import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.models import Asset, AssetAssignment, AssetHistory, Incident, Maintenance, User
from app.models.enums import (
    AssetActionType,
    AssetStatus,
    AssignmentStatus,
    IncidentCategory,
    IncidentPriority,
    IncidentStatus,
    MaintenanceStatus,
    UserRole,
)
from app.services.asset_lifecycle_ai import (
    RECENT_ASSIGNMENTS,
    RECENT_HISTORY,
    RECENT_INCIDENTS,
    RECENT_MAINTENANCES,
    AssetLifecycleAIService,
    LifecycleData,
    build_context,
)
from tests.test_incident_ai import OLLAMA_DOWN, _ollama_reply, mock_ollama

TODAY = date(2026, 10, 27)


def _headers(user: User) -> dict:
    token = create_access_token(subject=user.id, extra_claims={"email": user.email, "role": str(user.role)})
    return {"Authorization": f"Bearer {token}"}


def _other_user(db: Session) -> User:
    user = User(
        email=f"prev-holder-{uuid.uuid4().hex[:6]}@dxasset.local",
        password_hash=get_password_hash(uuid.uuid4().hex),
        full_name="Lê Văn Người Cũ",
        role=UserRole.EMPLOYEE,
        # Inactive so the shared `employee_user` fixture (first active employee) never picks it up
        is_active=False,
    )
    db.add(user)
    db.commit()
    return user


def _asset_with_lifecycle(db: Session, admin: User, holder: User, previous: User) -> Asset:
    """Laptop bought 2023, first held by `previous`, now held by `holder`, with incidents and 1 paid repair."""
    now = datetime.now(timezone.utc)
    asset = Asset(
        asset_code=f"LC-{uuid.uuid4().hex[:6].upper()}",
        name="Laptop vòng đời",
        category="Laptop",
        status=AssetStatus.ASSIGNED,
        purchase_date=date(2023, 3, 15),
        warranty_expiry=date(2026, 12, 31),
        current_user_id=holder.id,
    )
    db.add(asset)
    db.commit()
    db.add_all([
        AssetAssignment(asset_id=asset.id, assigned_to_user_id=previous.id, assigned_by_user_id=admin.id,
                        assigned_date=now - timedelta(days=300), return_date=now - timedelta(days=200),
                        status=AssignmentStatus.RETURNED),
        AssetAssignment(asset_id=asset.id, assigned_to_user_id=holder.id, assigned_by_user_id=admin.id,
                        assigned_date=now - timedelta(days=100), status=AssignmentStatus.ACTIVE),
        AssetHistory(asset_id=asset.id, action_type=AssetActionType.ASSIGNED, performed_by_id=admin.id,
                     details=f"Cấp phát cho {previous.full_name}"),
    ])
    for i in range(2):
        db.add(Incident(
            ticket_code=f"INC-LC-{uuid.uuid4().hex[:8].upper()}", asset_id=asset.id, reporter_id=holder.id,
            title=f"Pin chai nhanh lần {i + 1}", description="Pin tụt nhanh", category=IncidentCategory.HARDWARE,
            priority=IncidentPriority.MEDIUM, status=IncidentStatus.RESOLVED if i == 0 else IncidentStatus.OPEN,
            created_at=now - timedelta(days=50 - i * 10),
        ))
    db.add(Maintenance(
        maintenance_code=f"MNT-LC-{uuid.uuid4().hex[:8].upper()}", asset_id=asset.id, title="Thay pin",
        status=MaintenanceStatus.COMPLETED, start_date=now - timedelta(days=40), completed_date=now - timedelta(days=39),
        repair_cost=Decimal("1500000"),
    ))
    db.commit()
    db.refresh(asset)
    return asset


def _snapshot(db: Session, asset: Asset) -> tuple:
    db.expire_all()
    a = db.query(Asset).filter(Asset.id == asset.id).one()
    return (
        a.status, a.current_user_id, a.updated_at,
        db.query(AssetAssignment).filter(AssetAssignment.asset_id == asset.id).count(),
        db.query(Incident).filter(Incident.asset_id == asset.id).count(),
        db.query(Maintenance).filter(Maintenance.asset_id == asset.id).count(),
        db.query(AssetHistory).filter(AssetHistory.asset_id == asset.id).count(),
    )


# --- Context ---

def test_context_contains_lifecycle_totals_and_details(db: Session, admin_user: User, employee_user: User):
    previous = _other_user(db)
    asset = _asset_with_lifecycle(db, admin_user, employee_user, previous)
    context = build_context(LifecycleData(db, asset, admin_user, TODAY))

    assert asset.asset_code in context
    assert "Ngày mua: 15/03/2023" in context
    assert "Tổng số lượt cấp phát: 2 (cho 2 người dùng khác nhau)" in context
    assert "Tổng số sự cố: 2 (đang mở: 1)" in context
    assert "Tổng số lần bảo trì: 1" in context
    assert "Tổng chi phí sửa chữa: 1.500.000 VNĐ" in context
    assert f"Người đang sử dụng: {employee_user.full_name}" in context
    assert "Còn bảo hành đến 31/12/2026" in context
    assert "Pin chai nhanh lần 1" in context
    assert previous.full_name in context  # admin may see previous holders
    # No contact details or secrets
    assert previous.email not in context and employee_user.email not in context
    assert settings.SECRET_KEY not in context


def test_context_hides_other_people_from_employee(db: Session, admin_user: User, employee_user: User):
    previous = _other_user(db)
    asset = _asset_with_lifecycle(db, admin_user, employee_user, previous)
    context = build_context(LifecycleData(db, asset, employee_user, TODAY))
    assert previous.full_name not in context
    assert "một người dùng khác" in context
    assert f"Người đang sử dụng: {employee_user.full_name}" in context


def test_context_states_true_totals_when_truncated(db: Session, admin_user: User):
    asset = Asset(asset_code=f"LC-BIG-{uuid.uuid4().hex[:6].upper()}", name="Máy in nhiều lịch sử",
                  category="Printer", status=AssetStatus.IN_STOCK)
    db.add(asset)
    db.commit()
    db.add_all([AssetHistory(asset_id=asset.id, action_type=AssetActionType.STATUS_CHANGED,
                             performed_by_id=admin_user.id, details=f"Ghi chú {i}") for i in range(100)])
    db.add_all([Incident(ticket_code=f"INC-BIG-{uuid.uuid4().hex[:8].upper()}", asset_id=asset.id,
                         reporter_id=admin_user.id, title=f"Kẹt giấy {i}", description="x",
                         category=IncidentCategory.HARDWARE, priority=IncidentPriority.LOW,
                         status=IncidentStatus.CLOSED) for i in range(40)])
    db.commit()

    context = build_context(LifecycleData(db, asset, admin_user, TODAY))
    assert "Tổng số dòng nhật ký: 100" in context
    assert "Nhật ký gần nhất (chỉ là một phần" in context
    assert "Tổng số sự cố: 40" in context
    assert "Các sự cố gần nhất (chỉ là một phần" in context
    assert len([l for l in context.splitlines() if l.startswith("- ") and "Kẹt giấy" in l]) == RECENT_INCIDENTS
    detail_rows = [line for line in context.splitlines() if line.startswith("- ")]
    assert len(detail_rows) <= RECENT_ASSIGNMENTS + RECENT_INCIDENTS + RECENT_MAINTENANCES + RECENT_HISTORY <= 30


def test_context_without_optional_data(db: Session, admin_user: User):
    asset = Asset(asset_code=f"LC-NEW-{uuid.uuid4().hex[:6].upper()}", name="Chuột mới", category="Mouse",
                  status=AssetStatus.IN_STOCK)
    db.add(asset)
    db.commit()
    context = build_context(LifecycleData(db, asset, admin_user, TODAY))
    assert "Ngày mua" not in context
    assert "Bảo hành" not in context
    assert "Người đang sử dụng: không có (chưa cấp phát)" in context


# --- Service: AI path and fallback ---

def test_summary_uses_ollama_answer(db: Session, admin_user: User, employee_user: User):
    asset = _asset_with_lifecycle(db, admin_user, employee_user, _other_user(db))
    text = "Tài sản được mua ngày 15/03/2023, đã cấp phát 2 lượt và có 2 sự cố về pin."
    with mock_ollama(reply=_ollama_reply(text)):
        res = AssetLifecycleAIService.summarize(db, asset, admin_user, today=TODAY)
    assert res.source == "AI"
    assert res.summary == text


def test_summary_is_capped_at_six_sentences(db: Session, admin_user: User, employee_user: User):
    asset = _asset_with_lifecycle(db, admin_user, employee_user, _other_user(db))
    text = " ".join("Tài sản đang được sử dụng." for _ in range(10))
    with mock_ollama(reply=_ollama_reply(text)):
        res = AssetLifecycleAIService.summarize(db, asset, admin_user, today=TODAY)
    assert res.source == "AI"
    assert res.summary.count(".") == 6
    assert (res.total_assignments, res.total_incidents, res.total_maintenances) == (2, 2, 1)


def test_summary_rejects_invented_numbers(db: Session, admin_user: User, employee_user: User):
    asset = _asset_with_lifecycle(db, admin_user, employee_user, _other_user(db))
    with mock_ollama(reply=_ollama_reply("Tài sản đã qua 7 người dùng và tốn 9.900.000 VNĐ.")):
        res = AssetLifecycleAIService.summarize(db, asset, admin_user, today=TODAY)
    assert res.source == "RULE_BASED"
    assert "9.900.000" not in res.summary


def test_fallback_is_grounded_and_skips_missing_data(db: Session, admin_user: User, employee_user: User):
    asset = _asset_with_lifecycle(db, admin_user, employee_user, _other_user(db))
    with mock_ollama(error=OLLAMA_DOWN):
        res = AssetLifecycleAIService.summarize(db, asset, admin_user, today=TODAY)
    assert res.source == "RULE_BASED"
    assert "15/03/2023" in res.summary
    assert "2 lượt cho 2 người dùng" in res.summary
    assert "1.500.000 VNĐ" in res.summary
    assert employee_user.full_name in res.summary
    assert "31/12/2026" in res.summary

    empty = Asset(asset_code=f"LC-EMP-{uuid.uuid4().hex[:6].upper()}", name="Bàn phím", category="Keyboard",
                  status=AssetStatus.IN_STOCK)
    db.add(empty)
    db.commit()
    with mock_ollama(error=OLLAMA_DOWN):
        res = AssetLifecycleAIService.summarize(db, empty, admin_user, today=TODAY)
    assert "mua" not in res.summary and "chi phí" not in res.summary and "bảo hành" not in res.summary
    assert "chưa từng được cấp phát" in res.summary


# --- Endpoint ---

def test_endpoint_rbac(client: TestClient, db: Session, admin_user: User, it_manager_user: User, employee_user: User):
    own = _asset_with_lifecycle(db, admin_user, employee_user, _other_user(db))
    other_holder = _other_user(db)
    other = _asset_with_lifecycle(db, admin_user, other_holder, _other_user(db))
    manager = db.query(User).filter(User.role == UserRole.MANAGER, User.is_active == True).first()

    with mock_ollama(error=OLLAMA_DOWN):
        for user in [admin_user, it_manager_user] + ([manager] if manager else []):
            assert client.post(f"/api/v1/assets/{other.id}/ai/summary", headers=_headers(user)).status_code == 200
        assert client.post(f"/api/v1/assets/{own.id}/ai/summary", headers=_headers(employee_user)).status_code == 200
        res = client.post(f"/api/v1/assets/{other.id}/ai/summary", headers=_headers(employee_user))
        assert res.status_code == 403
        assert other_holder.full_name not in res.text


def test_endpoint_auth_and_not_found(client: TestClient, db: Session, admin_user: User, employee_user: User, admin_token: str):
    asset = _asset_with_lifecycle(db, admin_user, employee_user, _other_user(db))
    assert client.post(f"/api/v1/assets/{asset.id}/ai/summary").status_code == 401
    res = client.post("/api/v1/assets/999999999/ai/summary", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 404


def test_endpoint_success_schema_and_read_only(client: TestClient, db: Session, admin_user: User, employee_user: User, admin_token: str):
    asset = _asset_with_lifecycle(db, admin_user, employee_user, _other_user(db))
    before = _snapshot(db, asset)
    with mock_ollama(reply=_ollama_reply("Tài sản đã cấp phát 2 lượt và có 2 sự cố.")):
        res = client.post(f"/api/v1/assets/{asset.id}/ai/summary", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert set(data) == {"asset_id", "asset_code", "asset_name", "summary", "total_assignments",
                         "total_incidents", "total_maintenances", "source"}
    assert data["source"] == "AI"
    assert _snapshot(db, asset) == before


def test_endpoint_falls_back_when_ollama_unavailable_slow_or_disabled(client: TestClient, db: Session, admin_user: User, employee_user: User, admin_token: str, monkeypatch):
    asset = _asset_with_lifecycle(db, admin_user, employee_user, _other_user(db))
    headers = {"Authorization": f"Bearer {admin_token}"}
    for error in (OLLAMA_DOWN, httpx.ReadTimeout("timed out")):
        with mock_ollama(error=error):
            res = client.post(f"/api/v1/assets/{asset.id}/ai/summary", headers=headers)
        assert res.status_code == 200 and res.json()["source"] == "RULE_BASED"
    monkeypatch.setattr(settings, "OLLAMA_ENABLED", False)
    res = client.post(f"/api/v1/assets/{asset.id}/ai/summary", headers=headers)
    assert res.status_code == 200 and res.json()["source"] == "RULE_BASED"
