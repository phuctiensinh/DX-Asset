import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.enums import UserRole
from app.core.security import create_access_token
from app.api.v1.users import SYSTEM_OWNER_EMAIL

def test_list_users_anonymous(client: TestClient):
    response = client.get("/api/v1/users")
    assert response.status_code == 401

def test_list_users_employee_forbidden(client: TestClient, employee_token: str):
    headers = {"Authorization": f"Bearer {employee_token}"}
    response = client.get("/api/v1/users", headers=headers)
    assert response.status_code == 403

def test_list_users_it_manager_forbidden(client: TestClient, it_manager_user: User):
    token = create_access_token(
        subject=it_manager_user.id,
        extra_claims={"email": it_manager_user.email, "role": str(it_manager_user.role)}
    )
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/users", headers=headers)
    assert response.status_code == 403

def test_list_users_manager_forbidden(client: TestClient, db: Session):
    manager_user = db.query(User).filter(User.role == UserRole.MANAGER).first()
    if not manager_user:
        target = db.query(User).filter(User.email != SYSTEM_OWNER_EMAIL, User.role != UserRole.ADMIN).first()
        assert target is not None
        target.role = UserRole.MANAGER
        db.commit()
        db.refresh(target)
        manager_user = target

    token = create_access_token(
        subject=manager_user.id,
        extra_claims={"email": manager_user.email, "role": str(manager_user.role)}
    )
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/users", headers=headers)
    assert response.status_code == 403

def test_list_users_admin_success(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/api/v1/users", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

def test_get_user_detail_admin(client: TestClient, admin_token: str, employee_user: User):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get(f"/api/v1/users/{employee_user.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == employee_user.id
    assert data["email"] == employee_user.email

def test_get_user_detail_not_found(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/api/v1/users/999999", headers=headers)
    assert response.status_code == 404

def test_patch_role_by_non_admin_forbidden(client: TestClient, employee_token: str, employee_user: User):
    headers = {"Authorization": f"Bearer {employee_token}"}
    response = client.patch(
        f"/api/v1/users/{employee_user.id}/role",
        json={"role": "MANAGER"},
        headers=headers,
    )
    assert response.status_code == 403

def test_patch_role_to_admin_forbidden(client: TestClient, admin_token: str, employee_user: User):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.patch(
        f"/api/v1/users/{employee_user.id}/role",
        json={"role": "ADMIN"},
        headers=headers,
    )
    assert response.status_code == 403
    assert "ADMIN" in response.json()["detail"]

def test_patch_role_system_owner_demotion_forbidden(client: TestClient, admin_token: str, db: Session):
    owner = db.query(User).filter(User.email == SYSTEM_OWNER_EMAIL).first()
    if not owner:
        # Create system owner record if not present in test DB
        owner = User(
            email=SYSTEM_OWNER_EMAIL,
            password_hash="hashed_pw",
            full_name="System Owner Admin",
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(owner)
        db.commit()
        db.refresh(owner)

    headers = {"Authorization": f"Bearer {admin_token}"}
    for target_role in ["EMPLOYEE", "MANAGER", "IT_ASSET_MANAGER"]:
        response = client.patch(
            f"/api/v1/users/{owner.id}/role",
            json={"role": target_role},
            headers=headers,
        )
        assert response.status_code == 403
        assert "System Owner" in response.json()["detail"]

def test_patch_role_valid_transitions(client: TestClient, admin_token: str, db: Session):
    headers = {"Authorization": f"Bearer {admin_token}"}
    temp_user = User(
        email="temp_transitions_test@dxasset.local",
        password_hash="HASH",
        full_name="Temp Transitions Test",
        role=UserRole.EMPLOYEE,
        is_active=True,
    )
    db.add(temp_user)
    db.commit()
    db.refresh(temp_user)

    try:
        # EMPLOYEE -> MANAGER
        res1 = client.patch(
            f"/api/v1/users/{temp_user.id}/role",
            json={"role": "MANAGER"},
            headers=headers,
        )
        assert res1.status_code == 200
        assert res1.json()["role"] == "MANAGER"

        # MANAGER -> IT_ASSET_MANAGER
        res2 = client.patch(
            f"/api/v1/users/{temp_user.id}/role",
            json={"role": "IT_ASSET_MANAGER"},
            headers=headers,
        )
        assert res2.status_code == 200
        assert res2.json()["role"] == "IT_ASSET_MANAGER"

        # IT_ASSET_MANAGER -> EMPLOYEE
        res3 = client.patch(
            f"/api/v1/users/{temp_user.id}/role",
            json={"role": "EMPLOYEE"},
            headers=headers,
        )
        assert res3.status_code == 200
        assert res3.json()["role"] == "EMPLOYEE"
    finally:
        db.delete(temp_user)
        db.commit()


def test_patch_role_invalid_role_enum(client: TestClient, admin_token: str, employee_user: User):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.patch(
        f"/api/v1/users/{employee_user.id}/role",
        json={"role": "SUPERUSER_FAKE"},
        headers=headers,
    )
    assert response.status_code == 422

def test_fake_role_claim_in_jwt(client: TestClient, employee_user: User):
    # JWT claims role=ADMIN, but local PostgreSQL role is EMPLOYEE
    fake_token = create_access_token(
        subject=employee_user.id,
        extra_claims={"email": employee_user.email, "role": "ADMIN"}
    )
    headers = {"Authorization": f"Bearer {fake_token}"}
    # Should STILL be rejected with 403 because DB role is EMPLOYEE
    response = client.get("/api/v1/users", headers=headers)
    assert response.status_code == 403

def test_patch_role_manager_to_employee(client: TestClient, admin_token: str, db: Session):
    headers = {"Authorization": f"Bearer {admin_token}"}
    temp_user = User(
        email="temp_manager_role_test@dxasset.local",
        password_hash="HASH",
        full_name="Temp Manager Role Test",
        role=UserRole.MANAGER,
        is_active=True,
    )
    db.add(temp_user)
    db.commit()
    db.refresh(temp_user)

    try:
        # 1. DB role before update
        assert temp_user.role == UserRole.MANAGER

        # 2. PATCH request
        response = client.patch(
            f"/api/v1/users/{temp_user.id}/role",
            json={"role": "EMPLOYEE"},
            headers=headers,
        )

        # 3. Status code & Response body verification
        assert response.status_code == 200
        assert response.json()["role"] == "EMPLOYEE"

        # 4. DB role after update
        db.refresh(temp_user)
        assert temp_user.role == UserRole.EMPLOYEE
    finally:
        db.delete(temp_user)
        db.commit()

def test_single_admin_database_invariant(db: Session):
    """
    Phase 16H Invariant: Verify that exactly 1 user in PostgreSQL has role == UserRole.ADMIN,
    and that user's email is strictly SYSTEM_OWNER_EMAIL.
    """
    admin_users = db.query(User).filter(User.role == UserRole.ADMIN).all()
    assert len(admin_users) == 1, f"Expected exactly 1 ADMIN user in database, found {len(admin_users)}"
    assert admin_users[0].email == SYSTEM_OWNER_EMAIL, f"Expected ADMIN email to be '{SYSTEM_OWNER_EMAIL}', found '{admin_users[0].email}'"
