import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.user import User
from app.models.incident import Incident
from app.models.maintenance import Maintenance
from app.models.assignment import AssetAssignment
from app.models.history import AssetHistory
from app.models.enums import (
    AssetStatus,
    AssignmentStatus,
    IncidentCategory,
    IncidentPriority,
    IncidentStatus,
    MaintenanceStatus,
    AssetActionType,
    UserRole,
)

def test_list_maintenances_unauthorized(client: TestClient):
    """Test 1: GET /maintenances không có token -> 401."""
    res = client.get("/api/v1/maintenances")
    assert res.status_code == 401

def test_list_maintenances_authorized(client: TestClient, employee_token: str):
    """Test 2: Lấy danh sách bảo trì với token hợp lệ -> 200."""
    res = client.get(
        "/api/v1/maintenances",
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data

def test_employee_cannot_create_maintenance(client: TestClient, employee_token: str, db: Session):
    """Test 3: Employee tạo phiếu bảo trì -> 403 Forbidden."""
    asset = db.query(Asset).filter(Asset.status == AssetStatus.IN_STOCK).first()
    assert asset is not None

    res = client.post(
        "/api/v1/maintenances",
        json={
            "asset_id": asset.id,
            "title": "Employee thử tạo bảo trì",
        },
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert res.status_code == 403

def test_admin_creates_maintenance_success(client: TestClient, admin_token: str, db: Session, admin_user: User):
    """Test 4: Admin/IT_ASSET_MANAGER tạo phiếu bảo trì thành công -> 201."""
    asset = Asset(
        asset_code=f"MNT-AST-{uuid.uuid4().hex[:6].upper()}",
        name="Maintenance Test Laptop",
        category="Laptop",
        status=AssetStatus.IN_STOCK,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    mnt_code = f"MNT-T-{uuid.uuid4().hex[:6].upper()}"
    res = client.post(
        "/api/v1/maintenances",
        json={
            "asset_id": asset.id,
            "maintenance_code": mnt_code,
            "title": "Bảo trì nâng cấp RAM",
            "description": "Nâng cấp RAM từ 8GB lên 16GB",
            "repair_cost": 500000.00,
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["maintenance_code"] == mnt_code
    assert data["status"] == "SCHEDULED"
    assert data["repair_cost"] == 500000.00

def test_maintenance_start_updates_asset_status(client: TestClient, admin_token: str, db: Session, admin_user: User):
    """Test 5: Start maintenance -> Maintenance: IN_PROGRESS, Asset: IN_MAINTENANCE, History created."""
    asset = Asset(
        asset_code=f"MNT-ST-{uuid.uuid4().hex[:6].upper()}",
        name="Start Test Laptop",
        category="Laptop",
        status=AssetStatus.IN_STOCK,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    mnt = Maintenance(
        maintenance_code=f"MNT-ST-{uuid.uuid4().hex[:6].upper()}",
        asset_id=asset.id,
        technician_id=admin_user.id,
        status=MaintenanceStatus.SCHEDULED,
        title="Thay bàn phím",
    )
    db.add(mnt)
    db.commit()
    db.refresh(mnt)

    res = client.patch(
        f"/api/v1/maintenances/{mnt.id}/start",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "IN_PROGRESS"

    db.refresh(asset)
    assert asset.status == AssetStatus.IN_MAINTENANCE

    # Check history
    history = db.query(AssetHistory).filter(
        AssetHistory.asset_id == asset.id,
        AssetActionType.MAINTENANCE_STARTED == AssetHistory.action_type
    ).first()
    assert history is not None

def test_maintenance_on_retired_asset_fails(client: TestClient, admin_token: str, db: Session):
    """Test 6: Đưa tài sản RETIRED vào bảo trì -> 400 Bad Request."""
    asset = Asset(
        asset_code=f"MNT-RET-{uuid.uuid4().hex[:6].upper()}",
        name="Retired Device",
        category="Monitor",
        status=AssetStatus.RETIRED,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    res = client.post(
        "/api/v1/maintenances",
        json={
            "asset_id": asset.id,
            "title": "Bảo trì thiết bị thanh lý",
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 400
    assert "không thể đưa vào bảo trì" in res.json()["detail"]

def test_complete_maintenance_reverts_to_assigned_if_has_holder(client: TestClient, admin_token: str, db: Session, employee_user: User, admin_user: User):
    """Test 7: Complete maintenance khi asset đang có người giữ -> Asset khôi phục về ASSIGNED & current_user_id preserved."""
    asset = Asset(
        asset_code=f"MNT-ASG-{uuid.uuid4().hex[:6].upper()}",
        name="Assigned Laptop Under Maintenance",
        category="Laptop",
        status=AssetStatus.IN_MAINTENANCE,
        current_user_id=employee_user.id,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    mnt = Maintenance(
        maintenance_code=f"MNT-ASG-{uuid.uuid4().hex[:6].upper()}",
        asset_id=asset.id,
        technician_id=admin_user.id,
        status=MaintenanceStatus.IN_PROGRESS,
        title="Sửa bản lề màn hình",
    )
    db.add(mnt)
    db.commit()
    db.refresh(mnt)

    res = client.patch(
        f"/api/v1/maintenances/{mnt.id}/complete",
        json={
            "resolution_notes": "Đã siết chặt bản lề",
            "repair_cost": 200000.00
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "COMPLETED"

    db.refresh(asset)
    assert asset.status == AssetStatus.ASSIGNED
    assert asset.current_user_id == employee_user.id

def test_complete_maintenance_reverts_to_in_stock_if_unassigned(client: TestClient, admin_token: str, db: Session):
    """Test 8: Complete maintenance khi asset không có người giữ -> Asset khôi phục về IN_STOCK."""
    asset = Asset(
        asset_code=f"MNT-STK-{uuid.uuid4().hex[:6].upper()}",
        name="Unassigned Asset Under Maintenance",
        category="Printer",
        status=AssetStatus.IN_MAINTENANCE,
        current_user_id=None,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    mnt = Maintenance(
        maintenance_code=f"MNT-STK-{uuid.uuid4().hex[:6].upper()}",
        asset_id=asset.id,
        status=MaintenanceStatus.IN_PROGRESS,
        title="Vệ sinh đầu phun máy in",
    )
    db.add(mnt)
    db.commit()
    db.refresh(mnt)

    res = client.patch(
        f"/api/v1/maintenances/{mnt.id}/complete",
        json={"resolution_notes": "Đã vệ sinh xong"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "COMPLETED"

    db.refresh(asset)
    assert asset.status == AssetStatus.IN_STOCK

def test_incident_resolution_blocked_if_active_maintenance_exists(client: TestClient, admin_token: str, db: Session, admin_user: User):
    """Test 9: Chuyển Incident sang RESOLVED bị chặn (400) nếu Maintenance liên kết vẫn đang IN_PROGRESS."""
    asset = Asset(
        asset_code=f"INC-MNT-{uuid.uuid4().hex[:6].upper()}",
        name="Incident Linked Asset",
        category="Laptop",
        status=AssetStatus.IN_MAINTENANCE,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    inc = Incident(
        ticket_code=f"INC-L-{uuid.uuid4().hex[:6].upper()}",
        asset_id=asset.id,
        reporter_id=admin_user.id,
        title="Lỗi cáp màn hình",
        description="Màn hình chớp nháy",
        category=IncidentCategory.HARDWARE,
        priority=IncidentPriority.HIGH,
        status=IncidentStatus.IN_PROGRESS,
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)

    mnt = Maintenance(
        maintenance_code=f"MNT-INC-{uuid.uuid4().hex[:6].upper()}",
        asset_id=asset.id,
        incident_id=inc.id,
        status=MaintenanceStatus.IN_PROGRESS,
        title="Thay cáp màn hình",
    )
    db.add(mnt)
    db.commit()
    db.refresh(mnt)

    # Attempt to resolve incident directly while maintenance is active
    res = client.patch(
        f"/api/v1/incidents/{inc.id}",
        json={"status": "RESOLVED"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 400
    assert "đợt bảo trì liên kết" in res.json()["detail"]
