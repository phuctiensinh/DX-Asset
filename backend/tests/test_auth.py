from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import create_access_token
from app.models.user import User
from app.models.enums import UserRole


def test_login_success(client: TestClient):
    payload = {
        "email": "employee1@dxasset.local",
        "password": "password123"
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["email"] == "employee1@dxasset.local"
    assert "password_hash" not in data["user"]

def test_login_invalid_password(client: TestClient):
    payload = {
        "email": "employee1@dxasset.local",
        "password": "wrongpassword"
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"

def test_login_non_existent_email(client: TestClient):
    payload = {
        "email": "nonexistent@dxasset.local",
        "password": "password123"
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"

def test_get_me_success(client: TestClient, employee_user: User, employee_token: str):
    headers = {"Authorization": f"Bearer {employee_token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == employee_user.email
    assert "password_hash" not in data

def test_get_me_missing_token(client: TestClient):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401

def test_get_me_invalid_token(client: TestClient):
    headers = {"Authorization": "Bearer invalid.jwt.token"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"

def test_get_me_expired_token(client: TestClient, employee_user: User):
    expired_token = create_access_token(
        subject=employee_user.id,
        expires_delta=timedelta(seconds=-10)
    )
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"

def test_get_me_inactive_user_rejected(client: TestClient, db: Session):
    inactive_user = User(
        email="disabled_user_test_temp@dxasset.local",
        password_hash="HASH",
        full_name="Disabled User Temp",
        role=UserRole.EMPLOYEE,
        is_active=False,
    )
    db.add(inactive_user)
    db.commit()
    db.refresh(inactive_user)

    try:
        token = create_access_token(
            subject=inactive_user.id,
            extra_claims={"email": inactive_user.email, "role": str(inactive_user.role)}
        )
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "User account is inactive"
    finally:
        db.delete(inactive_user)
        db.commit()
