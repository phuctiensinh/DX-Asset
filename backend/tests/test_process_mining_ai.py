import json
import random
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.core.security import create_access_token
from app.models import Asset, AssetAssignment, Incident, Maintenance, User, UserRole
from app.models.enums import IncidentStatus, ProcessEventType
from app.models.process_case import ProcessCase
from app.models.process_event import ProcessEvent
from app.services.process_mining import ProcessMiningService
from app.services.process_mining_ai import ProcessMiningAIService, ProcessMiningReportData, build_context
from tests.test_incident_ai import OLLAMA_DOWN, _ollama_reply, mock_ollama
from tests.test_process_mining import _add_incident_case, _created_incident_event, _filters

URL = "/api/v1/process-mining/ai/report"
EMPTY_YEAR = 2099


@pytest.fixture(autouse=True)
def _rollback_synthetic_data(db: Session):
    """Endpoints share the test session so synthetic cases are only flushed, then rolled back (never reach the dev DB)."""
    app.dependency_overrides[get_db] = lambda: db
    yield
    app.dependency_overrides.pop(get_db, None)
    db.rollback()


def _new_year() -> int:
    """Fresh synthetic year per test so cohorts never overlap with seed data or other tests."""
    return random.randint(2200, 9000)


def _headers(user: User) -> dict:
    token = create_access_token(subject=user.id, extra_claims={"email": user.email, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


def _status(seconds: int, frm: IncidentStatus, to: IncidentStatus) -> dict:
    return {"type": ProcessEventType.INCIDENT_STATUS_CHANGED, "seconds": seconds, "from": frm, "to": to}


def _seed_cohort(db: Session, admin: User, year: int) -> list:
    """3 incident cases in `year`: one normal, one reworked, one with a non-standard transition."""
    cases = [
        _add_incident_case(db, admin, year, [
            _created_incident_event(0),
            _status(3600, IncidentStatus.OPEN, IncidentStatus.IN_REVIEW),
            _status(7200, IncidentStatus.IN_REVIEW, IncidentStatus.RESOLVED),
        ]),
        _add_incident_case(db, admin, year, [
            _created_incident_event(100),
            _status(3700, IncidentStatus.OPEN, IncidentStatus.IN_REVIEW),
            _status(7300, IncidentStatus.IN_REVIEW, IncidentStatus.RESOLVED),
            _status(9000, IncidentStatus.RESOLVED, IncidentStatus.IN_PROGRESS),
        ]),
        _add_incident_case(db, admin, year, [
            _created_incident_event(200),
            _status(3800, IncidentStatus.OPEN, IncidentStatus.IN_REVIEW),
            _status(4000, IncidentStatus.CLOSED, IncidentStatus.OPEN),
        ]),
    ]
    return cases


def _year_query(year: int) -> str:
    return f"?date_from={year}-01-01T00:00:00Z&date_to={year + 1}-01-01T00:00:00Z&min_sample=2"


# --- Context built from ProcessMiningService results only ---

def test_context_is_built_from_process_mining_service(db: Session, admin_user: User):
    year = _new_year()
    cases = _seed_cohort(db, admin_user, year)
    filters = _filters(year)
    data = ProcessMiningReportData(db, filters, min_sample=2)
    context = build_context(data)

    summary = ProcessMiningService.get_summary(db, filters)
    rework = ProcessMiningService.get_rework(db, filters)
    conformance = ProcessMiningService.get_conformance(db, filters)
    assert data.summary == summary
    assert f"có {summary.total_cases} phiếu" in context
    assert f"Có {rework.total_rework_cases} trên {rework.eligible_cases} phiếu sự cố bị mở xử lý lại" in context
    assert f"Có {conformance.conforming_cases} trên {conformance.eligible_cases} phiếu sự cố đi đúng quy trình chuẩn" in context
    # 3 cases is a small sample: the backend itself flags it instead of letting the model conclude
    assert "chưa đủ để kết luận" in context
    assert "Tạo phiếu sự cố → " in context  # bottlenecks use Vietnamese labels, not internal codes
    assert "INCIDENT_STATUS_CHANGED" not in context
    # Only aggregated metrics: no ticket codes, people or asset identifiers reach the model
    for _, incident, _ in cases:
        assert incident.ticket_code not in context
        assert incident.asset.asset_code not in context
    assert admin_user.email not in context and admin_user.full_name not in context
    assert settings.SECRET_KEY not in context


def test_ollama_receives_exactly_the_structured_context(db: Session, admin_user: User):
    year = _new_year()
    _seed_cohort(db, admin_user, year)
    filters = _filters(year)
    expected = build_context(ProcessMiningReportData(db, filters, min_sample=2))
    reply = json.dumps({"report": "Quy trình có 3 phiếu.", "recommendations": []})
    with patch("app.services.process_mining_ai.ollama_chat_json", return_value=json.loads(reply)) as chat:
        ProcessMiningAIService.generate_report(db, filters, min_sample=2)
    system_prompt, user_content = chat.call_args.args
    assert user_content == expected
    assert "JSON" in system_prompt


# --- AI path and fallback ---

def test_report_uses_ollama_answer(db: Session, admin_user: User):
    year = _new_year()
    _seed_cohort(db, admin_user, year)
    reply = _ollama_reply(json.dumps({
        "report": "Trong năm có 3 phiếu sự cố. Có 1 phiếu bị làm lại.",
        "recommendations": ["Rà soát bước giải quyết.", "Kiểm tra phiếu sai quy trình.", "Theo dõi thêm.", "Mục thừa."],
    }))
    with mock_ollama(reply=reply):
        res = ProcessMiningAIService.generate_report(db, _filters(year), min_sample=2)
    assert res.source == "AI"
    assert res.total_cases == 3
    assert len(res.recommendations) == 3


def test_report_list_is_joined_into_text(db: Session, admin_user: User):
    year = _new_year()
    _seed_cohort(db, admin_user, year)
    reply = _ollama_reply(json.dumps({"report": ["Tổng quan: có 3 phiếu.", "Điểm nghẽn: chưa rõ."], "recommendations": []}))
    with mock_ollama(reply=reply):
        res = ProcessMiningAIService.generate_report(db, _filters(year), min_sample=2)
    assert res.source == "AI"
    assert res.report == "Tổng quan: có 3 phiếu. Điểm nghẽn: chưa rõ."


def test_report_is_capped_at_eight_sentences(db: Session, admin_user: User):
    year = _new_year()
    _seed_cohort(db, admin_user, year)
    reply = _ollama_reply(json.dumps({"report": " ".join("Quy trình cần theo dõi thêm." for _ in range(12)), "recommendations": []}))
    with mock_ollama(reply=reply):
        res = ProcessMiningAIService.generate_report(db, _filters(year), min_sample=2)
    assert res.source == "AI"
    assert res.report.count(".") == 8


def test_report_rejects_invented_numbers(db: Session, admin_user: User):
    year = _new_year()
    _seed_cohort(db, admin_user, year)
    reply = _ollama_reply(json.dumps({"report": "Có 57 phiếu bị làm lại trong 12 tuần.", "recommendations": []}))
    with mock_ollama(reply=reply):
        res = ProcessMiningAIService.generate_report(db, _filters(year), min_sample=2)
    assert res.source == "RULE_BASED"
    assert "57" not in res.report


def test_fallback_is_built_from_metrics(db: Session, admin_user: User):
    year = _new_year()
    _seed_cohort(db, admin_user, year)
    with mock_ollama(error=OLLAMA_DOWN):
        res = ProcessMiningAIService.generate_report(db, _filters(year), min_sample=2)
    assert res.source == "RULE_BASED"
    assert "có 3 phiếu" in res.report
    assert "Bước chậm nhất là" in res.report
    assert "Có 1 trên" in res.report  # rework ratio from ProcessMiningService
    assert "chưa đủ để kết luận" in res.report
    assert 1 <= len(res.recommendations) <= 3
    assert any("Rà soát bước" in r for r in res.recommendations)


def test_empty_cohort_skips_model(db: Session):
    with patch("app.services.process_mining_ai.ollama_chat_json") as chat:
        res = ProcessMiningAIService.generate_report(db, _filters(EMPTY_YEAR))
    chat.assert_not_called()
    assert res.source == "RULE_BASED"
    assert res.total_cases == 0
    assert "chưa đủ dữ liệu" in res.report


# --- Endpoint ---

def test_endpoint_rbac(client: TestClient, db: Session, admin_user: User, it_manager_user: User, employee_user: User):
    manager = db.query(User).filter(User.role == UserRole.MANAGER, User.is_active == True).first()
    assert manager is not None
    assert client.post(URL).status_code == 401
    assert client.post(URL, headers={"Authorization": "Bearer invalid-token"}).status_code == 401
    with mock_ollama(error=OLLAMA_DOWN):
        # Same roles as the existing Process Mining endpoints
        for user in (admin_user, it_manager_user, manager):
            assert client.post(URL + _year_query(EMPTY_YEAR), headers=_headers(user)).status_code == 200
        assert client.post(URL + _year_query(EMPTY_YEAR), headers=_headers(employee_user)).status_code == 403


def test_endpoint_success_schema_and_read_only(client: TestClient, db: Session, admin_user: User):
    year = _new_year()
    _seed_cohort(db, admin_user, year)
    models = (ProcessCase, ProcessEvent, Incident, Maintenance, Asset, AssetAssignment)
    before = [db.query(model).count() for model in models]
    reply = _ollama_reply(json.dumps({"report": "Có 3 phiếu sự cố trong phạm vi.", "recommendations": ["Theo dõi thêm."]}))
    with mock_ollama(reply=reply):
        res = client.post(URL + _year_query(year), headers=_headers(admin_user))
    assert res.status_code == 200
    data = res.json()
    assert set(data) == {"report", "recommendations", "total_cases", "source"}
    assert data["source"] == "AI" and data["total_cases"] == 3
    assert before == [db.query(model).count() for model in models]


def test_endpoint_falls_back_when_ollama_unavailable_slow_or_disabled(client: TestClient, db: Session, admin_user: User, monkeypatch):
    year = _new_year()
    _seed_cohort(db, admin_user, year)
    for error in (OLLAMA_DOWN, httpx.ReadTimeout("timed out")):
        with mock_ollama(error=error):
            res = client.post(URL + _year_query(year), headers=_headers(admin_user))
        assert res.status_code == 200 and res.json()["source"] == "RULE_BASED"
    monkeypatch.setattr(settings, "OLLAMA_ENABLED", False)
    res = client.post(URL + _year_query(year), headers=_headers(admin_user))
    assert res.status_code == 200 and res.json()["source"] == "RULE_BASED"


def test_endpoint_validates_filters(client: TestClient, admin_user: User):
    res = client.post(URL + "?date_from=2061-01-01T00:00:00", headers=_headers(admin_user))
    assert res.status_code == 422
