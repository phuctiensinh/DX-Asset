from datetime import timedelta
from fastapi.testclient import TestClient
from app.core.security import create_access_token
from app.models.user import User

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

def test_get_me_success(client: TestClient, employee_token: str):
    headers = {"Authorization": f"Bearer {employee_token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "employee1@dxasset.local"
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
