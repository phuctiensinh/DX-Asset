from datetime import datetime, timedelta, timezone
import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Asset, AssetAssignment, Incident, Maintenance, User, UserRole
from app.models.enums import (
    AssetStatus,
    IncidentCategory,
    IncidentPriority,
    IncidentStatus,
    ProcessCaseType,
    ProcessEventSource,
    ProcessEventTimestampQuality,
    ProcessEventType,
)
from app.models.process_case import ProcessCase
from app.models.process_event import ProcessEvent
from app.services.ai_assistant import AIAssistantService
from app.services.process_mining import ProcessMiningService
from app.services.process_mining_assistant import (
    ProcessMiningAssistantIntent,
    ProcessMiningAssistantService,
)


def _add_case(
    db: Session,
    admin: User,
    *,
    case_index: int,
    closed: bool,
    source: ProcessEventSource,
) -> ProcessCase:
    suffix = uuid.uuid4().hex[:12].upper()
    asset = Asset(
        asset_code=f"PMA-{suffix}",
        name="Process Mining Assistant Test Asset",
        category="Laptop",
        status=AssetStatus.IN_STOCK,
    )
    db.add(asset)
    db.flush()
    created_at = datetime(2049, 1, 1, tzinfo=timezone.utc) + timedelta(days=case_index)
    incident = Incident(
        ticket_code=f"PMA-{suffix}",
        asset_id=asset.id,
        reporter_id=admin.id,
        title="Process Mining Assistant test case",
        description="Temporary test fixture, rolled back after test.",
        category=IncidentCategory.HARDWARE,
        priority=IncidentPriority.MEDIUM,
        status=IncidentStatus.CLOSED if closed else IncidentStatus.OPEN,
        created_at=created_at,
    )
    db.add(incident)
    db.flush()
    case = ProcessCase(case_type=ProcessCaseType.INCIDENT, incident_id=incident.id)
    db.add(case)
    db.flush()

    events = [
        (ProcessEventType.INCIDENT_CREATED, None, IncidentStatus.OPEN.value),
        (ProcessEventType.TECHNICIAN_ASSIGNED, None, None),
    ]
    if closed:
        events.append((ProcessEventType.INCIDENT_STATUS_CHANGED, IncidentStatus.RESOLVED.value, IncidentStatus.CLOSED.value))
    for sequence, (event_type, from_status, to_status) in enumerate(events, start=1):
        db.add(ProcessEvent(
            case_id=case.id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            occurred_at=created_at + timedelta(seconds=20 * sequence),
            case_sequence=sequence,
            source=source,
            timestamp_quality=ProcessEventTimestampQuality.ACTION_TIME,
            source_event_key=f"pma-test:{suffix}:{sequence}",
        ))
    db.flush()
    return case


@pytest.fixture
def process_case_sandbox(db: Session):
    transaction = db.begin_nested()
    try:
        yield
    finally:
        transaction.rollback()


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Quy trình hiện tại thế nào?", ProcessMiningAssistantIntent.SUMMARY),
        ("Tình hình process mining", ProcessMiningAssistantIntent.SUMMARY),
        ("What is the process mining overview?", ProcessMiningAssistantIntent.SUMMARY),
        ("Có những biến thể quy trình nào?", ProcessMiningAssistantIntent.VARIANTS),
        ("Process variants", ProcessMiningAssistantIntent.VARIANTS),
        ("Bottleneck ở đâu?", ProcessMiningAssistantIntent.BOTTLENECKS),
        ("Which process step is slowest?", ProcessMiningAssistantIntent.BOTTLENECKS),
        ("CASE-023 mất bao lâu?", ProcessMiningAssistantIntent.CASE_DURATION),
        ("How long is CASE-023 processing time?", ProcessMiningAssistantIntent.CASE_DURATION),
        ("CASE-023 đã trải qua những bước nào?", ProcessMiningAssistantIntent.CASE_DETAIL),
        ("Chi tiết case đó", ProcessMiningAssistantIntent.CASE_DETAIL),
        ("How long does this case take?", ProcessMiningAssistantIntent.CASE_DURATION),
        ("Cho tôi chi tiết case", ProcessMiningAssistantIntent.CASE_DETAIL),
    ],
)
def test_detects_vietnamese_and_english_process_mining_intents(message, expected):
    assert ProcessMiningAssistantService.detect_intent(message) == expected


def test_non_process_mining_asset_incident_and_mutation_intents_are_not_reclassified():
    for message in (
        "AST-LAP-001 đang ở đâu?",
        "INC-001 đang ở trạng thái nào?",
        "Tạo incident mới cho laptop này",
    ):
        assert ProcessMiningAssistantService.detect_intent(message) is None


def test_process_mining_results_use_existing_service_and_exact_case_data(
    db: Session,
    admin_user: User,
    process_case_sandbox,
):
    before_case_count = db.query(ProcessCase).count()
    before_event_count = db.query(ProcessEvent).count()
    cases = [
        _add_case(
            db,
            admin_user,
            case_index=index,
            closed=index == 0,
            source=ProcessEventSource.LIVE if index == 0 else ProcessEventSource.BACKFILL,
        )
        for index in range(5)
    ]

    summary = AIAssistantService.process_chat(db, admin_user, "tình hình process mining")
    assert summary is not None and summary.intent == "PROCESS_MINING_SUMMARY"
    assert f"**{before_case_count + 5} case**" in summary.answer
    assert f"**{before_event_count + 11} event**" in summary.answer
    assert "LIVE" in summary.answer and "BACKFILL" in summary.answer
    assert summary.sources[0].type == "process_mining"

    variants = AIAssistantService.process_chat(db, admin_user, "process variants")
    assert variants is not None and variants.intent == "PROCESS_MINING_VARIANTS"
    assert "INCIDENT_CREATED → TECHNICIAN_ASSIGNED" in variants.answer

    expected_bottlenecks = ProcessMiningService.get_bottlenecks(db)
    bottlenecks = AIAssistantService.process_chat(db, admin_user, "đâu là bottleneck?")
    assert bottlenecks is not None and bottlenecks.intent == "PROCESS_MINING_BOTTLENECKS"
    expected_transition = next(
        item for item in expected_bottlenecks
        if item.from_event == ProcessEventType.INCIDENT_CREATED
        and item.to_event == ProcessEventType.TECHNICIAN_ASSIGNED
    )
    assert "INCIDENT_CREATED → TECHNICIAN_ASSIGNED" in bottlenecks.answer
    assert f"{expected_transition.count} observations" in bottlenecks.answer

    completed = AIAssistantService.process_chat(
        db, admin_user, f"CASE-{cases[0].id:03d} mất bao lâu?"
    )
    assert completed is not None and completed.intent == "PROCESS_MINING_CASE_DURATION"
    assert "40 giây" in completed.answer

    incomplete = AIAssistantService.process_chat(
        db, admin_user, f"CASE-{cases[1].id:03d} mất bao lâu?"
    )
    assert incomplete is not None and incomplete.intent == "PROCESS_MINING_CASE_DURATION"
    assert "chưa có processing time hoàn chỉnh" in incomplete.answer

    detail = AIAssistantService.process_chat(
        db, admin_user, f"CASE-{cases[0].id:03d} đã trải qua những bước nào?"
    )
    assert detail is not None and detail.intent == "PROCESS_MINING_CASE_DETAIL"
    assert "1. INCIDENT_CREATED (recorded status: OPEN)" in detail.answer
    assert "None →" not in detail.answer
    assert "2. TECHNICIAN_ASSIGNED" in detail.answer
    assert "3. INCIDENT_STATUS_CHANGED (RESOLVED → CLOSED)" in detail.answer
    assert detail.sources[0].code == f"CASE-{cases[0].id:03d}"

    missing_id = AIAssistantService.process_chat(db, admin_user, "Chi tiết case đó")
    assert missing_id is not None and "cung cấp Case ID" in missing_id.answer
    missing_case = AIAssistantService.process_chat(db, admin_user, "Chi tiết CASE-999999999")
    assert missing_case is not None and "Không tìm thấy CASE-999999999" in missing_case.answer


@pytest.mark.parametrize("message", [
    "quy trình hiện tại thế nào",
    "có những biến thể quy trình nào",
    "đâu là bottleneck của toàn hệ thống",
    "CASE-023 mất bao lâu",
    "chi tiết CASE-023",
])
def test_employee_is_forbidden_from_process_mining_assistant(
    client: TestClient,
    employee_token: str,
    message: str,
):
    response = client.post(
        "/api/v1/assistant/chat",
        headers={"Authorization": f"Bearer {employee_token}"},
        json={"message": message},
    )
    assert response.status_code == 403


def test_employee_is_rejected_before_process_mining_service_call(
    employee_user: User,
    monkeypatch,
):
    def unexpected_service_call(*args, **kwargs):
        pytest.fail("ProcessMiningService must not run for EMPLOYEE")

    monkeypatch.setattr(ProcessMiningService, "get_bottlenecks", unexpected_service_call)
    with pytest.raises(HTTPException) as error:
        AIAssistantService.process_chat(None, employee_user, "Đâu là bottleneck toàn hệ thống?")
    assert error.value.status_code == 403


def test_admin_it_manager_and_manager_can_use_process_mining_assistant(
    db: Session,
    client: TestClient,
    admin_token: str,
    it_manager_user: User,
):
    manager = db.query(User).filter(User.role == UserRole.MANAGER).first()
    assert manager is not None
    # The existing global assistant roles should all receive a deterministic answer.
    for token in (admin_token,):
        response = client.post(
            "/api/v1/assistant/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "tổng quan quy trình"},
        )
        assert response.status_code == 200
        assert response.json()["intent"] == "PROCESS_MINING_SUMMARY"

    from app.core.security import create_access_token

    for user in (it_manager_user, manager):
        token = create_access_token(
            subject=user.id,
            extra_claims={"email": user.email, "role": user.role.value},
        )
        response = client.post(
            "/api/v1/assistant/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "tổng quan quy trình"},
        )
        assert response.status_code == 200
        assert response.json()["intent"] == "PROCESS_MINING_SUMMARY"


def test_process_mining_assistant_is_read_only(
    db: Session,
    client: TestClient,
    admin_token: str,
):
    models = (ProcessCase, ProcessEvent, Incident, Maintenance, Asset, AssetAssignment)
    before = [db.query(model).count() for model in models]
    headers = {"Authorization": f"Bearer {admin_token}"}
    queries = (
        "quy trình hiện tại thế nào",
        "có những biến thể quy trình nào",
        "đâu là bottleneck hiện tại",
        "CASE-999999999 mất bao lâu",
        "chi tiết CASE-999999999",
    )
    for message in queries:
        response = client.post("/api/v1/assistant/chat", headers=headers, json={"message": message})
        assert response.status_code == 200
        assert response.json()["intent"].startswith("PROCESS_MINING_")
    assert before == [db.query(model).count() for model in models]
