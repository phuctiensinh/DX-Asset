import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.user import User
from app.models.incident import Incident
from app.models.history import AssetHistory
from app.models.enums import (
    AssetStatus, IncidentCategory, IncidentPriority, IncidentStatus,
    AssetActionType, UserRole, ProcessCaseType, ProcessEventType,
    ProcessEventSource, ProcessEventTimestampQuality,
)
from app.models.process_case import ProcessCase
from app.models.process_event import ProcessEvent

def test_list_incidents_unauthorized(client: TestClient):
    """Test 1: Truy cập GET /incidents không có token -> 401."""
    res = client.get("/api/v1/incidents")
    assert res.status_code == 401

def test_list_incidents_authorized(client: TestClient, employee_token: str):
    """Test 2: Lấy danh sách phiếu sự cố với token hợp lệ -> 200."""
    res = client.get(
        "/api/v1/incidents",
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)

def test_get_incident_detail(client: TestClient, employee_token: str, db: Session):
    """Test 3: Xem chi tiết phiếu sự cố tồn tại -> 200."""
    inc = db.query(Incident).first()
    assert inc is not None
    res = client.get(
        f"/api/v1/incidents/{inc.id}",
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert res.status_code == 200
    assert res.json()["id"] == inc.id

def test_get_incident_not_found(client: TestClient, employee_token: str):
    """Test 4: Xem phiếu không tồn tại -> 404."""
    res = client.get(
        "/api/v1/incidents/999999",
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert res.status_code == 404
    assert "Không tìm thấy phiếu" in res.json()["detail"]

def test_create_incident_success(client: TestClient, employee_token: str, db: Session, employee_user: User):
    """Test 5: Tạo phiếu báo hỏng thành công & kiểm tra AssetHistory."""
    unique_code = f"INC-T-{uuid.uuid4().hex[:6].upper()}"
    asset = Asset(
        asset_code=f"T-INC-{uuid.uuid4().hex[:6].upper()}",
        name="Test Incident Laptop",
        category="Laptop",
        status=AssetStatus.IN_STOCK
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    res = client.post(
        "/api/v1/incidents",
        json={
            "asset_id": asset.id,
            "ticket_code": unique_code,
            "title": "Màn hình bị chớp tắt liên tục",
            "description": "Khi cắm sạc thì màn hình bị chớp tắt nhấp nháy liên tục.",
            "category": "HARDWARE",
            "priority": "HIGH"
        },
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert res.status_code == 201
    inc_data = res.json()
    assert inc_data["ticket_code"] == unique_code
    assert inc_data["status"] == "OPEN"

    process_case = db.query(ProcessCase).filter(ProcessCase.incident_id == inc_data["id"]).one()
    event_row = db.query(ProcessEvent).filter(ProcessEvent.case_id == process_case.id).one()
    assert process_case.case_type == ProcessCaseType.INCIDENT
    assert event_row.event_type == ProcessEventType.INCIDENT_CREATED
    assert event_row.from_status is None
    assert event_row.to_status == IncidentStatus.OPEN.value
    assert event_row.performed_by_id == employee_user.id
    assert event_row.target_user_id is None
    assert event_row.source == ProcessEventSource.LIVE
    assert event_row.timestamp_quality == ProcessEventTimestampQuality.ACTION_TIME
    assert event_row.source_event_key == f"incident:{inc_data['id']}:created"

    # Verify AssetHistory created
    history = db.query(AssetHistory).filter(
        AssetHistory.asset_id == asset.id,
        AssetHistory.action_type == AssetActionType.INCIDENT_REPORTED
    ).first()
    assert history is not None
    assert history.performed_by_id == employee_user.id
    assert unique_code in history.details

def test_create_incident_asset_not_found(client: TestClient, employee_token: str):
    """Test 6: Tạo phiếu cho tài sản không tồn tại -> 404."""
    res = client.post(
        "/api/v1/incidents",
        json={
            "asset_id": 999999,
            "title": "Lỗi tài sản ảo",
            "description": "Mô tả lỗi"
        },
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert res.status_code == 404
    assert "Không tìm thấy tài sản" in res.json()["detail"]

def test_create_incident_retired_asset(client: TestClient, employee_token: str, db: Session):
    """Test 7: Tạo phiếu cho tài sản RETIRED -> 400."""
    unique_code = f"RET-INC-{uuid.uuid4().hex[:6].upper()}"
    asset = Asset(
        asset_code=unique_code,
        name="Retired Laptop",
        category="Laptop",
        status=AssetStatus.RETIRED
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    res = client.post(
        "/api/v1/incidents",
        json={
            "asset_id": asset.id,
            "title": "Báo hỏng máy thanh lý",
            "description": "Thử nghiệm"
        },
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert res.status_code == 400
    assert "không thể gửi báo hỏng" in res.json()["detail"]

def test_update_incident_employee_forbidden(client: TestClient, employee_token: str, db: Session):
    """Test 8: Employee sửa phiếu xử lý sự cố -> 403 Forbidden."""
    inc = db.query(Incident).first()
    assert inc is not None

    res = client.patch(
        f"/api/v1/incidents/{inc.id}",
        json={"status": "IN_PROGRESS"},
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert res.status_code == 403

def test_update_incident_success(client: TestClient, admin_token: str, db: Session, admin_user: User):
    """Test 9: Admin/IT sửa phiếu, đổi status OPEN -> IN_PROGRESS -> RESOLVED & ghi AssetHistory."""
    # Create test incident
    unique_code = f"INC-UP-{uuid.uuid4().hex[:6].upper()}"
    asset = Asset(
        asset_code=f"T-UP-{uuid.uuid4().hex[:6].upper()}",
        name="Test Update Asset",
        category="Laptop",
        status=AssetStatus.IN_STOCK
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    inc = Incident(
        ticket_code=unique_code,
        asset_id=asset.id,
        reporter_id=admin_user.id,
        title="Bàn phím hỏng nút Enter",
        description="Nút Enter bị kẹt",
        category=IncidentCategory.HARDWARE,
        priority=IncidentPriority.MEDIUM,
        status=IncidentStatus.OPEN,
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)

    # 1. Update OPEN -> IN_PROGRESS
    res1 = client.patch(
        f"/api/v1/incidents/{inc.id}",
        json={"status": "IN_PROGRESS", "assigned_it_id": admin_user.id},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res1.status_code == 200
    assert res1.json()["status"] == "IN_PROGRESS"
    assert res1.json()["assigned_it_id"] == admin_user.id
    case = db.query(ProcessCase).filter(ProcessCase.incident_id == inc.id).one()
    first_event = db.query(ProcessEvent).filter(ProcessEvent.case_id == case.id).one()
    assert first_event.event_type == ProcessEventType.INCIDENT_STATUS_CHANGED
    assert first_event.from_status == IncidentStatus.OPEN.value
    assert first_event.to_status == IncidentStatus.IN_PROGRESS.value
    assert first_event.performed_by_id == admin_user.id

    # 2. Update IN_PROGRESS -> RESOLVED
    res2 = client.patch(
        f"/api/v1/incidents/{inc.id}",
        json={
            "status": "RESOLVED",
            "resolution_notes": "Thay nút Enter mới",
            "repair_cost": 150000.00
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "RESOLVED"
    assert res2.json()["resolved_at"] is not None
    assert res2.json()["repair_cost"] == 150000.00
    status_events = db.query(ProcessEvent).filter(
        ProcessEvent.case_id == case.id,
        ProcessEvent.event_type == ProcessEventType.INCIDENT_STATUS_CHANGED,
    ).order_by(ProcessEvent.case_sequence).all()
    assert [(row.from_status, row.to_status) for row in status_events] == [
        (IncidentStatus.OPEN.value, IncidentStatus.IN_PROGRESS.value),
        (IncidentStatus.IN_PROGRESS.value, IncidentStatus.RESOLVED.value),
    ]

    # Same-state PATCH is not a new transition event.
    no_change = client.patch(
        f"/api/v1/incidents/{inc.id}",
        json={"status": "RESOLVED"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert no_change.status_code == 200
    assert db.query(ProcessEvent).filter(
        ProcessEvent.case_id == case.id,
        ProcessEvent.event_type == ProcessEventType.INCIDENT_STATUS_CHANGED,
    ).count() == 2

    # Verify AssetHistory MAINTENANCE_UPDATED
    history = db.query(AssetHistory).filter(
        AssetHistory.asset_id == asset.id,
        AssetHistory.action_type == AssetActionType.MAINTENANCE_UPDATED
    ).first()
    assert history is not None
    assert history.performed_by_id == admin_user.id

def test_update_incident_invalid_status_transition(client: TestClient, admin_token: str, db: Session, admin_user: User):
    """Test 10: Chuyển status không hợp lệ (VD: CANCELLED -> RESOLVED) -> 400."""
    unique_code = f"INC-INV-{uuid.uuid4().hex[:6].upper()}"
    asset = Asset(
        asset_code=f"T-INV-{uuid.uuid4().hex[:6].upper()}",
        name="Test Invalid Status Asset",
        category="Laptop",
        status=AssetStatus.IN_STOCK
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    inc = Incident(
        ticket_code=unique_code,
        asset_id=asset.id,
        reporter_id=admin_user.id,
        title="Phiếu đã hủy",
        description="Mô tả phiếu hủy",
        category=IncidentCategory.OTHER,
        priority=IncidentPriority.LOW,
        status=IncidentStatus.CANCELLED,
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)

    res = client.patch(
        f"/api/v1/incidents/{inc.id}",
        json={"status": "RESOLVED"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 400
    assert "Không thể chuyển trạng thái phiếu" in res.json()["detail"]


def test_assign_technician_records_assignment_and_status_only_when_changed(
    client: TestClient,
    admin_token: str,
    db: Session,
    admin_user: User,
    it_manager_user: User,
):
    asset = Asset(
        asset_code=f"T-ASG-{uuid.uuid4().hex[:8].upper()}",
        name="Technician assignment test asset",
        category="Laptop",
        status=AssetStatus.IN_STOCK,
    )
    db.add(asset)
    db.flush()
    incident = Incident(
        ticket_code=f"INC-ASG-{uuid.uuid4().hex[:8].upper()}",
        asset_id=asset.id,
        reporter_id=admin_user.id,
        title="Assignment event test",
        description="Test technician assignment process events",
        category=IncidentCategory.HARDWARE,
        priority=IncidentPriority.MEDIUM,
        status=IncidentStatus.OPEN,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    response = client.post(
        f"/api/v1/incidents/{incident.id}/assign",
        json={"technician_id": admin_user.id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    case = db.query(ProcessCase).filter(ProcessCase.incident_id == incident.id).one()
    events = db.query(ProcessEvent).filter(ProcessEvent.case_id == case.id).order_by(ProcessEvent.case_sequence).all()
    assert [row.event_type for row in events] == [
        ProcessEventType.TECHNICIAN_ASSIGNED,
        ProcessEventType.INCIDENT_STATUS_CHANGED,
    ]
    assert events[0].target_user_id == admin_user.id
    assert events[0].performed_by_id == admin_user.id
    assert (events[1].from_status, events[1].to_status) == (
        IncidentStatus.OPEN.value,
        IncidentStatus.IN_REVIEW.value,
    )

    # Repeating the same assignment does not create an assignment event.
    repeated = client.post(
        f"/api/v1/incidents/{incident.id}/assign",
        json={"technician_id": admin_user.id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert repeated.status_code == 200
    assert db.query(ProcessEvent).filter(ProcessEvent.case_id == case.id).count() == 2

    # Replacing the technician creates a new assignment occurrence, with a distinct key.
    replacement = client.post(
        f"/api/v1/incidents/{incident.id}/assign",
        json={"technician_id": it_manager_user.id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert replacement.status_code == 200
    events = db.query(ProcessEvent).filter(ProcessEvent.case_id == case.id).order_by(ProcessEvent.case_sequence).all()
    assert len(events) == 3
    assert events[2].event_type == ProcessEventType.TECHNICIAN_ASSIGNED
    assert events[2].target_user_id == it_manager_user.id
    assert len({row.source_event_key for row in events}) == 3
