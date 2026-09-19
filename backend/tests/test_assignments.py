import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.user import User
from app.models.assignment import AssetAssignment
from app.models.history import AssetHistory
from app.models.enums import AssetStatus, AssignmentStatus, AssetActionType, UserRole
from app.core.security import create_access_token

@pytest.fixture
def manager_token(db: Session) -> str:
    user = db.query(User).filter(User.role == UserRole.MANAGER).first()
    assert user is not None, "Manager user should exist in DB seed"
    return create_access_token(
        subject=user.id,
        extra_claims={"email": user.email, "role": str(user.role)}
    )

def test_list_assignments_unauthorized(client: TestClient):
    """Test 1: Truy cập GET /assignments mà không có token -> 401."""
    res = client.get("/api/v1/assignments")
    assert res.status_code == 401

def test_list_assignments_authorized(client: TestClient, employee_token: str):
    """Test 2: Lấy danh sách assignments với token hợp lệ -> 200."""
    res = client.get(
        "/api/v1/assignments",
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)

def test_create_assignment_employee_forbidden(client: TestClient, employee_token: str, db: Session):
    """Test 3: Employee gửi request POST /assignments -> 403 Forbidden."""
    asset = db.query(Asset).filter(Asset.status == AssetStatus.IN_STOCK).first()
    user = db.query(User).filter(User.role == UserRole.EMPLOYEE).first()
    assert asset is not None and user is not None

    res = client.post(
        "/api/v1/assignments",
        json={"asset_id": asset.id, "user_id": user.id, "notes": "Test employee assign"},
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert res.status_code == 403

def test_create_assignment_manager_forbidden(client: TestClient, manager_token: str, db: Session):
    """Test 4: Manager gửi request POST /assignments -> 403 Forbidden."""
    asset = db.query(Asset).filter(Asset.status == AssetStatus.IN_STOCK).first()
    user = db.query(User).filter(User.role == UserRole.EMPLOYEE).first()
    assert asset is not None and user is not None

    res = client.post(
        "/api/v1/assignments",
        json={"asset_id": asset.id, "user_id": user.id, "notes": "Test manager assign"},
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert res.status_code == 403

def test_create_assignment_asset_not_found(client: TestClient, admin_token: str, db: Session):
    """Test 5: Cấp phát tài sản không tồn tại -> 404."""
    user = db.query(User).filter(User.role == UserRole.EMPLOYEE).first()
    res = client.post(
        "/api/v1/assignments",
        json={"asset_id": 999999, "user_id": user.id},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 404
    assert "Không tìm thấy tài sản" in res.json()["detail"]

def test_create_assignment_user_not_found(client: TestClient, admin_token: str, db: Session):
    """Test 6: Cấp phát cho user không tồn tại -> 404."""
    asset = db.query(Asset).filter(Asset.status == AssetStatus.IN_STOCK).first()
    assert asset is not None
    res = client.post(
        "/api/v1/assignments",
        json={"asset_id": asset.id, "user_id": 999999},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 404
    assert "Không tìm thấy người dùng" in res.json()["detail"]

def test_create_assignment_retired_asset(client: TestClient, admin_token: str, db: Session):
    """Test 7: Cấp phát tài sản RETIRED -> 400."""
    unique_code = f"RETIRED-{uuid.uuid4().hex[:6].upper()}"
    retired_asset = Asset(
        asset_code=unique_code,
        name="Retired Test Asset",
        category="Laptop",
        status=AssetStatus.RETIRED
    )
    db.add(retired_asset)
    db.commit()
    db.refresh(retired_asset)

    user = db.query(User).filter(User.role == UserRole.EMPLOYEE).first()

    res = client.post(
        "/api/v1/assignments",
        json={"asset_id": retired_asset.id, "user_id": user.id},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 400
    assert "không thể cấp phát" in res.json()["detail"]

def test_create_assignment_success_and_history(client: TestClient, admin_token: str, db: Session, admin_user: User):
    """Test 8, 12, 13, 14: Cấp phát thành công, đổi status, đổi current_user_id, tạo history."""
    unique_code = f"T-ASSIGN-{uuid.uuid4().hex[:6].upper()}"
    asset = Asset(
        asset_code=unique_code,
        name="Test Assign Asset",
        category="Laptop",
        status=AssetStatus.IN_STOCK
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    target_user = db.query(User).filter(User.role == UserRole.EMPLOYEE).first()
    assert target_user is not None

    res = client.post(
        "/api/v1/assignments",
        json={"asset_id": asset.id, "user_id": target_user.id, "notes": "Cấp phát thử nghiệm"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 201
    asm_data = res.json()
    assert asm_data["asset_id"] == asset.id
    assert asm_data["assigned_to_user_id"] == target_user.id
    assert asm_data["status"] == "ACTIVE"

    # Verify Asset state updated
    db.refresh(asset)
    assert asset.status == AssetStatus.ASSIGNED
    assert asset.current_user_id == target_user.id

    # Verify AssetHistory created
    history = db.query(AssetHistory).filter(
        AssetHistory.asset_id == asset.id,
        AssetActionType.ASSIGNED == AssetHistory.action_type
    ).first()
    assert history is not None
    assert history.performed_by_id == admin_user.id
    assert target_user.email in history.details

def test_duplicate_active_assignment(client: TestClient, admin_token: str, db: Session):
    """Test 9: Cấp phát lại tài sản đã có active assignment -> 400."""
    asset = db.query(Asset).filter(Asset.status == AssetStatus.ASSIGNED).first()
    assert asset is not None
    user = db.query(User).filter(User.role == UserRole.EMPLOYEE).first()

    res = client.post(
        "/api/v1/assignments",
        json={"asset_id": asset.id, "user_id": user.id},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 400
    assert "đã có lượt cấp phát đang hoạt động" in res.json()["detail"]

def test_return_assignment_success_and_history(client: TestClient, admin_token: str, db: Session, admin_user: User):
    """Test 10, 11, 15, 16: Thu hồi thành công, đổi asset status về IN_STOCK, current_user_id = None, ghi history."""
    unique_code = f"T-RETURN-{uuid.uuid4().hex[:6].upper()}"
    asset = Asset(
        asset_code=unique_code,
        name="Test Return Asset",
        category="Monitor",
        status=AssetStatus.IN_STOCK
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    target_user = db.query(User).filter(User.role == UserRole.EMPLOYEE).first()

    # Assign
    post_res = client.post(
        "/api/v1/assignments",
        json={"asset_id": asset.id, "user_id": target_user.id},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert post_res.status_code == 201
    assignment_id = post_res.json()["id"]

    # Return
    ret_res = client.patch(
        f"/api/v1/assignments/{assignment_id}/return",
        json={"notes": "Thu hồi sau khi hết dự án"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert ret_res.status_code == 200
    ret_data = ret_res.json()
    assert ret_data["status"] == "RETURNED"
    assert ret_data["return_date"] is not None

    # Verify asset state
    db.refresh(asset)
    assert asset.status == AssetStatus.IN_STOCK
    assert asset.current_user_id is None

    # Verify history created
    history = db.query(AssetHistory).filter(
        AssetHistory.asset_id == asset.id,
        AssetHistory.action_type == AssetActionType.RETURNED
    ).first()
    assert history is not None
    assert history.performed_by_id == admin_user.id

    # Verify assignment record still exists in DB (not hard deleted)
    db_asm = db.query(AssetAssignment).filter(AssetAssignment.id == assignment_id).first()
    assert db_asm is not None
    assert db_asm.status == AssignmentStatus.RETURNED

def test_return_already_returned_assignment(client: TestClient, admin_token: str, db: Session):
    """Test 11: Thu hồi lại assignment đã RETURNED -> 400."""
    returned_asm = db.query(AssetAssignment).filter(AssetAssignment.status == AssignmentStatus.RETURNED).first()
    assert returned_asm is not None

    res = client.patch(
        f"/api/v1/assignments/{returned_asm.id}/return",
        json={"notes": "Thử thu hồi lần 2"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 400
    assert "không thể thu hồi" in res.json()["detail"]

def test_transfer_assignment(client: TestClient, admin_token: str, db: Session):
    """Test 17: Chuyển giao tài sản từ user A sang user B."""
    user_a = db.query(User).filter(User.email == "employee1@dxasset.local").first()
    user_b = db.query(User).filter(User.email == "employee2@dxasset.local").first()
    assert user_a is not None and user_b is not None

    unique_code = f"T-TRANS-{uuid.uuid4().hex[:6].upper()}"
    asset = Asset(
        asset_code=unique_code,
        name="Test Transfer Asset",
        category="Laptop",
        status=AssetStatus.IN_STOCK
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    assign_res = client.post(
        "/api/v1/assignments",
        json={"asset_id": asset.id, "user_id": user_a.id},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    old_asm_id = assign_res.json()["id"]

    # Transfer to user B
    transfer_res = client.patch(
        f"/api/v1/assignments/{old_asm_id}/transfer",
        json={"target_user_id": user_b.id, "notes": "Chuyển giao bàn làm việc"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert transfer_res.status_code == 200
    new_asm_data = transfer_res.json()
    assert new_asm_data["id"] != old_asm_id
    assert new_asm_data["assigned_to_user_id"] == user_b.id
    assert new_asm_data["status"] == "ACTIVE"

    # Verify old assignment is RETURNED
    old_asm = db.query(AssetAssignment).filter(AssetAssignment.id == old_asm_id).first()
    assert old_asm.status == AssignmentStatus.RETURNED

    # Verify Asset current_user_id updated to user B
    db.refresh(asset)
    assert asset.current_user_id == user_b.id
    assert asset.status == AssetStatus.ASSIGNED
