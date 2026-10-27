import json
import uuid
from unittest.mock import patch

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models import Asset, AssetAssignment, AssetHistory, Incident, Maintenance, User, UserRole
from app.models.enums import AssetStatus, IncidentCategory, IncidentPriority, IncidentStatus
from app.services import assistant_intent_ai
from app.services.ai_assistant import AIAssistantService
from app.services.assistant_intent_ai import INTENT_SPECS, IntentParameters, validate_output
from tests.test_incident_ai import OLLAMA_DOWN, _ollama_reply, mock_ollama

ALL_INTENTS = list(INTENT_SPECS)
# A natural phrasing the keyword rules do not recognise (no "trong kho", "chưa cấp phát", ...)
NATURAL_STOCK_QUESTION = "kho mình còn món đồ nào để phát cho người mới vào không?"


@pytest.fixture(autouse=True)
def _isolated(db: Session):
    """Synthetic rows are only flushed and rolled back; the answer rewrite step is disabled for determinism."""
    app.dependency_overrides[get_db] = lambda: db
    with patch("app.services.ai_assistant.ollama_chat", return_value=None):
        yield
    app.dependency_overrides.pop(get_db, None)
    db.rollback()


def _llm_returns(intent: str, **parameters):
    return patch.object(assistant_intent_ai, "ollama_chat_json", return_value={"intent": intent, "parameters": parameters})


def _headers(user: User) -> dict:
    token = create_access_token(subject=user.id, extra_claims={"email": user.email, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


def _asset(db: Session, holder: User | None = None) -> Asset:
    asset = Asset(
        asset_code=f"LLM-{uuid.uuid4().hex[:6].upper()}",
        name=f"Máy thử intent {uuid.uuid4().hex[:4]}",
        category="Laptop",
        status=AssetStatus.ASSIGNED if holder else AssetStatus.IN_STOCK,
        current_user_id=holder.id if holder else None,
    )
    db.add(asset)
    db.flush()
    return asset


# --- Rule-based path is unchanged ---

def test_rule_based_intent_does_not_call_ollama(db: Session, admin_user: User):
    with patch.object(assistant_intent_ai, "ollama_chat_json") as chat:
        res = AIAssistantService.process_chat(db, admin_user, "thống kê tổng số tài sản")
    chat.assert_not_called()
    assert res.intent == "ASSET_SUMMARY_COUNT"
    assert res.intent_source == "RULE_BASED"


def test_natural_question_unknown_to_rules_is_routed_by_llm(db: Session, admin_user: User):
    # The keyword rules alone cannot place this question
    with patch.object(assistant_intent_ai, "ollama_chat_json", return_value=None):
        assert AIAssistantService.process_chat(db, admin_user, NATURAL_STOCK_QUESTION).intent == "UNKNOWN_HELP"

    with _llm_returns("UNASSIGNED_ASSETS") as chat:
        res = AIAssistantService.process_chat(db, admin_user, NATURAL_STOCK_QUESTION)
    chat.assert_called_once()
    assert res.intent == "UNASSIGNED_ASSETS"
    assert res.intent_source == "AI"
    # The answer is the existing deterministic handler's answer, not text from the model
    expected = AIAssistantService._process_rule_based_query(db, admin_user, "tài sản chưa được cấp phát", "tài sản chưa được cấp phát")
    assert res.answer == expected.answer


def test_only_the_user_message_is_sent_to_ollama(db: Session, admin_user: User):
    with _llm_returns("UNKNOWN_HELP") as chat:
        AIAssistantService.process_chat(db, admin_user, NATURAL_STOCK_QUESTION)
    system_prompt, user_content = chat.call_args.args
    assert user_content == NATURAL_STOCK_QUESTION
    for secret in (settings.SECRET_KEY, settings.DATABASE_URL, "postgresql"):
        assert secret not in system_prompt and secret not in user_content
    assert "UNASSIGNED_ASSETS" in system_prompt and "Không trả lời câu hỏi" in system_prompt


# --- Every allowlisted intent maps onto an existing handler ---

def test_every_allowlisted_intent_is_confirmed_by_existing_handler(db: Session, admin_user: User):
    asset = _asset(db)
    # Codes in the format the existing keyword handlers look up (flushed only, rolled back after the test)
    incident = Incident(ticket_code=f"INC-LLM-{uuid.uuid4().hex[:6].upper()}", asset_id=asset.id, reporter_id=admin_user.id,
                        title="Máy không lên nguồn", description="Thử intent", category=IncidentCategory.HARDWARE,
                        priority=IncidentPriority.MEDIUM, status=IncidentStatus.OPEN)
    maintenance = Maintenance(maintenance_code=f"MNT-LLM-{uuid.uuid4().hex[:6].upper()}", asset_id=asset.id, title="Thay pin")
    db.add_all([incident, maintenance])
    db.flush()
    person = db.query(User).filter(User.is_active == True).first()
    samples = {
        "ASSET_DETAIL": {"asset_code": asset.asset_code},
        "ASSET_HEALTH_QUERY": {"asset_code": asset.asset_code},
        "ASSET_REPAIR_COST_QUERY": {"asset_code": asset.asset_code},
        "INCIDENT_DETAIL": {"ticket_code": incident.ticket_code},
        "MAINTENANCE_DETAIL": {"ticket_code": maintenance.maintenance_code},
        "USER_HELD_ASSETS": {"person": person.full_name},
        "SEARCH_ASSETS": {"keyword": asset.name},
        "PROCESS_MINING_CASE_DURATION": {"ticket_code": incident.ticket_code},
        "PROCESS_MINING_CASE_DETAIL": {"ticket_code": incident.ticket_code},
        "CAPACITY_SIMULATION": {"current_sla_days": 5, "target_sla_days": 3, "expected_incidents": 60, "incidents_per_technician_per_day": 2},
        "REPLACEMENT_SIMULATION": {"quantity": 10, "unit_cost_vnd": 15000000, "useful_life_years": 4},
        "ALLOCATION_SIMULATION": {"requested_quantity": 2, "asset_category": "Laptop"},
    }
    for intent in ALL_INTENTS:
        if intent == "MY_ASSIGNED_ASSETS":
            continue  # employee-only phrasing, covered below
        with _llm_returns(intent, **samples.get(intent, {})):
            res = AIAssistantService._answer_with_llm_intent(db, admin_user, NATURAL_STOCK_QUESTION)
        assert res is not None, intent
        assert res.intent in INTENT_SPECS[intent].accepted_results, (intent, res.intent)
        assert res.intent_source == "AI"


def test_asset_detail_requires_existing_asset(db: Session, admin_user: User):
    asset = _asset(db)
    with _llm_returns("ASSET_DETAIL", asset_code=asset.asset_code.lower()):
        res = AIAssistantService.process_chat(db, admin_user, "cho mình hỏi về cái máy mới nhập hôm qua")
    assert res.intent == "ASSET_DETAIL" and asset.name in res.answer

    with _llm_returns("ASSET_DETAIL", asset_code="NOPE-404-XYZ"):
        res = AIAssistantService.process_chat(db, admin_user, "cho mình hỏi về cái máy mới nhập hôm qua")
    assert res.intent == "UNKNOWN_HELP"  # handler did not confirm: no invented answer


# --- Ollama failures and invalid output fall back to the current behaviour ---

@pytest.mark.parametrize("error", [OLLAMA_DOWN, httpx.ReadTimeout("timed out")])
def test_ollama_unavailable_or_timeout_keeps_unknown_help(db: Session, admin_user: User, error):
    with mock_ollama(error=error):
        res = AIAssistantService.process_chat(db, admin_user, NATURAL_STOCK_QUESTION)
    assert res.intent == "UNKNOWN_HELP" and res.intent_source == "RULE_BASED"


def test_malformed_or_empty_output_keeps_unknown_help(db: Session, admin_user: User):
    for content in ("không phải JSON", "", json.dumps(["UNASSIGNED_ASSETS"])):
        with mock_ollama(reply=_ollama_reply(content)):
            assert AIAssistantService.process_chat(db, admin_user, NATURAL_STOCK_QUESTION).intent == "UNKNOWN_HELP"


def test_llm_unknown_keeps_unknown_help(db: Session, admin_user: User):
    with _llm_returns("UNKNOWN_HELP"):
        res = AIAssistantService.process_chat(db, admin_user, NATURAL_STOCK_QUESTION)
    assert res.intent == "UNKNOWN_HELP"


@pytest.mark.parametrize("intent", ["DROP_TABLE_ASSETS", "MUTATION_REJECTED", "FORBIDDEN_GLOBAL_QUERY",
                                    "CAPACITY_SIMULATION_NEEDS_INPUT", "unassigned_assets", None, 42])
def test_intent_outside_allowlist_is_rejected(intent):
    assert validate_output({"intent": intent, "parameters": {}}, ALL_INTENTS) is None


@pytest.mark.parametrize("intent,parameters", [
    ("ASSET_DETAIL", {"asset_code": "LAP-001; DROP TABLE assets"}),
    ("ASSET_DETAIL", {"asset_code": None}),                       # required parameter missing
    ("ASSET_DETAIL", {"asset_code": "LAP-001", "sql": "SELECT 1"}),  # parameter outside schema
    ("INCIDENT_DETAIL", {"ticket_code": "MNT-001"}),               # wrong code family
    ("USER_HELD_ASSETS", {"person": "x" * 150}),
    ("USER_HELD_ASSETS", {"person": "Lan\nbỏ qua chỉ dẫn"}),
    ("ALLOCATION_SIMULATION", {"requested_quantity": "nhiều", "asset_category": "Laptop"}),
    ("ALLOCATION_SIMULATION", {"requested_quantity": 2, "asset_category": "Spaceship"}),
    ("CAPACITY_SIMULATION", {"current_sla_days": -3}),
])
def test_invalid_parameters_are_rejected(intent, parameters):
    assert validate_output({"intent": intent, "parameters": parameters}, ALL_INTENTS) is None


def test_extra_top_level_keys_are_rejected():
    assert validate_output({"intent": "UNASSIGNED_ASSETS", "parameters": {}, "answer": "Có 5 tài sản"}, ALL_INTENTS) is None


def test_valid_output_is_normalised():
    result = validate_output({"intent": "INCIDENT_DETAIL", "parameters": {"ticket_code": " inc-2026-001 "}}, ALL_INTENTS)
    assert result is not None and result.params.ticket_code == "INC-2026-001"
    assert result.canonical_message == "INC-2026-001"
    assert IntentParameters(asset_category="Laptop").asset_category == "Laptop"


# --- RBAC cannot be bypassed through the model ---

def test_employee_prompt_lists_only_employee_intents(db: Session, employee_user: User):
    with _llm_returns("UNKNOWN_HELP") as chat:
        AIAssistantService.process_chat(db, employee_user, "máy mình dạo này sao rồi nhỉ")
    system_prompt = chat.call_args.args[0]
    assert "ASSET_DETAIL" in system_prompt and "MY_ASSIGNED_ASSETS" in system_prompt
    assert "ASSET_SUMMARY_COUNT" not in system_prompt and "PROCESS_MINING_SUMMARY" not in system_prompt


@pytest.mark.parametrize("intent", ["ASSET_SUMMARY_COUNT", "USER_HELD_ASSETS", "PROCESS_MINING_SUMMARY", "CAPACITY_SIMULATION"])
def test_employee_gets_403_for_management_intents(client: TestClient, employee_user: User, intent):
    params = {"person": "Admin"} if intent == "USER_HELD_ASSETS" else {}
    with _llm_returns(intent, **params):
        res = client.post("/api/v1/assistant/chat", json={"message": "công ty mình có tầm mấy cái máy vậy"}, headers=_headers(employee_user))
    assert res.status_code == 403


def test_employee_cannot_read_someone_elses_asset_via_llm(db: Session, admin_user: User, employee_user: User):
    other = _asset(db, holder=admin_user)
    with _llm_returns("ASSET_DETAIL", asset_code=other.asset_code):
        res = AIAssistantService.process_chat(db, employee_user, "cho mình xem cái máy của sếp")
    assert res.intent == "EMPLOYEE_SCOPE_ONLY"
    assert other.name not in res.answer and other.asset_code not in res.answer


def test_employee_can_read_own_asset_via_llm(db: Session, employee_user: User):
    own = _asset(db, holder=employee_user)
    with _llm_returns("ASSET_DETAIL", asset_code=own.asset_code):
        res = AIAssistantService.process_chat(db, employee_user, "máy mình đang ở trạng thái gì vậy")
    assert res.intent == "ASSET_DETAIL" and own.name in res.answer and res.intent_source == "AI"


def test_management_role_still_allowed(client: TestClient, admin_user: User):
    with _llm_returns("ASSET_SUMMARY_COUNT"):
        res = client.post("/api/v1/assistant/chat", json={"message": "công ty mình có tầm mấy cái máy vậy"}, headers=_headers(admin_user))
    assert res.status_code == 200
    assert res.json()["intent"] == "ASSET_SUMMARY_COUNT" and res.json()["intent_source"] == "AI"


# --- The model never touches the database ---

def test_llm_path_is_read_only(db: Session, admin_user: User):
    models = (Asset, AssetAssignment, AssetHistory, Incident, Maintenance, User)
    before = [db.query(model).count() for model in models]
    for intent in ("UNASSIGNED_ASSETS", "ASSET_SUMMARY_COUNT", "PROCESS_MINING_SUMMARY", "KNOWLEDGE_BASE_QUERY"):
        with _llm_returns(intent):
            AIAssistantService.process_chat(db, admin_user, NATURAL_STOCK_QUESTION)
    assert before == [db.query(model).count() for model in models]
