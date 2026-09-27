import json
import urllib.request
import urllib.parse
import pytest
import jwt
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.user import User
from app.models.enums import UserRole

def get_real_keycloak_token(username: str = "testuser", password: str = "password123") -> str:
    """Helper to fetch a real Keycloak RS256 Access Token from local running Keycloak instance."""
    url = "http://localhost:8080/realms/dx-asset/protocol/openid-connect/token"
    data = urllib.parse.urlencode({
        "client_id": "dx-asset-frontend",
        "grant_type": "password",
        "username": username,
        "password": password,
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        res = urllib.request.urlopen(req, timeout=2.0)
        body = json.loads(res.read())
        return body["access_token"]
    except Exception:
        pytest.skip("Real Keycloak container is offline on localhost:8080")


def test_real_keycloak_token_integration_and_jit_provisioning(client: TestClient, db: Session):
    """
    Test Case 3: Xác thực Token thực tế từ Keycloak container, gọi /auth/me thành công 200,
    tự động JIT Provisioning bản ghi local User với role = EMPLOYEE và keycloak_user_id được lưu.
    """
    token = get_real_keycloak_token()
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "testuser@student.tdmu.edu.vn"
    assert data["role"] == "EMPLOYEE"
    assert data["keycloak_user_id"] is not None

    # Kiểm tra trong Database local
    local_user = db.query(User).filter(User.email == "testuser@student.tdmu.edu.vn").first()
    assert local_user is not None
    assert local_user.keycloak_user_id == data["keycloak_user_id"]
    assert local_user.role == UserRole.EMPLOYEE

def test_keycloak_first_time_linking_existing_user(client: TestClient, db: Session):
    """
    Test Case 1: Lần đầu đăng nhập của System Owner đã tồn tại trong local DB (2424801030008@student.tdmu.edu.vn).
    Hệ thống sẽ tự động gán keycloak_user_id = token.sub, đồng thời GIỮ NGUYÊN role ADMIN của System Owner.
    """
    admin_user = db.query(User).filter(User.email == "2424801030008@student.tdmu.edu.vn").first()
    assert admin_user is not None
    orig_sub = admin_user.keycloak_user_id
    try:
        admin_user.keycloak_user_id = None
        db.commit()
        db.refresh(admin_user)

        initial_role = admin_user.role
        assert initial_role == UserRole.ADMIN

        sub_uuid = "owner-keycloak-sub-uuid-12345"
        token_payload = {
            "sub": sub_uuid,
            "email": "2424801030008@student.tdmu.edu.vn",
            "iss": settings.KEYCLOAK_ISSUER_URL,
            "azp": settings.KEYCLOAK_CLIENT_ID,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        mock_token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm="HS256")
        headers = {"Authorization": f"Bearer {mock_token}"}

        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "2424801030008@student.tdmu.edu.vn"
        assert data["role"] == "ADMIN"
        assert data["keycloak_user_id"] == sub_uuid

        db.refresh(admin_user)
        assert admin_user.keycloak_user_id == sub_uuid
        assert admin_user.role == UserRole.ADMIN
    finally:
        admin_user.keycloak_user_id = orig_sub
        db.commit()

def test_keycloak_existing_linked_user_lookup_by_sub(client: TestClient, db: Session):
    """
    Test Case 2: Khi System Owner đã được linked keycloak_user_id, các request tiếp theo
    sẽ tra cứu trực tiếp bằng sub (indexed lookup), không bị trùng lặp user, role giữ nguyên ADMIN.
    """
    admin_user = db.query(User).filter(User.email == "2424801030008@student.tdmu.edu.vn").first()
    orig_sub = admin_user.keycloak_user_id
    sub_uuid = "owner-keycloak-sub-uuid-12345"
    try:
        admin_user.keycloak_user_id = sub_uuid
        db.commit()

        token_payload = {
            "sub": sub_uuid,
            "email": "different_email_claim_ignored@example.com",
            "iss": settings.KEYCLOAK_ISSUER_URL,
            "azp": settings.KEYCLOAK_CLIENT_ID,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        mock_token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm="HS256")
        headers = {"Authorization": f"Bearer {mock_token}"}

        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == admin_user.id
        assert data["role"] == "ADMIN"
    finally:
        admin_user.keycloak_user_id = orig_sub
        db.commit()


def test_keycloak_identity_conflict_rejected(client: TestClient, db: Session):
    """
    Test Case 5 & 6: Nếu token sub A muốn link tới user email X đã được link với sub B khác,
    hệ thống phát hiện xung đột identity và từ chối request với HTTP 401.
    """
    conflict_user = db.query(User).filter(User.email == "conflict_test_user@dxasset.local").first()
    if not conflict_user:
        conflict_user = User(
            email="conflict_test_user@dxasset.local",
            password_hash="HASH",
            full_name="Conflict Test User",
            role=UserRole.EMPLOYEE,
            keycloak_user_id="original-correct-sub-123",
            is_active=True,
        )
        db.add(conflict_user)
        db.commit()
    else:
        conflict_user.keycloak_user_id = "original-correct-sub-123"
        db.commit()

    try:
        conflict_payload = {
            "sub": "malicious-sub-999",
            "email": "conflict_test_user@dxasset.local",
            "iss": settings.KEYCLOAK_ISSUER_URL,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        conflict_token = jwt.encode(conflict_payload, settings.SECRET_KEY, algorithm="HS256")
        headers = {"Authorization": f"Bearer {conflict_token}"}

        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"
    finally:
        db.delete(conflict_user)
        db.commit()

def test_keycloak_role_source_of_truth_prevents_privilege_escalation(client: TestClient, db: Session):
    """
    Test Case 4: Chứng minh Database `users.role` là Source of Truth duy nhất cho Authorization.
    Tài khoản testuser đăng nhập qua Keycloak nhận role EMPLOYEE, không thể gọi các endpoint yêu cầu ADMIN / IT_ASSET_MANAGER.
    """
    token = get_real_keycloak_token()
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/users/technicians/skills", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Operation not permitted for this user role"

def test_system_owner_admin_invariant(client: TestClient, db: Session):
    """
    Test Case 7: Kiểm tra System Owner 2424801030008@student.tdmu.edu.vn luôn có role ADMIN.
    """
    owner_user = db.query(User).filter(User.email == "2424801030008@student.tdmu.edu.vn").first()
    if not owner_user:
        owner_user = User(
            email="2424801030008@student.tdmu.edu.vn",
            password_hash="EXTERNAL",
            full_name="Nguyễn Phạm Đại Phúc (System Owner)",
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(owner_user)
        db.commit()

    orig_sub = owner_user.keycloak_user_id
    try:
        sub_to_use = orig_sub or "system-owner-keycloak-sub-888"
        token_payload = {
            "sub": sub_to_use,
            "email": "2424801030008@student.tdmu.edu.vn",
            "iss": settings.KEYCLOAK_ISSUER_URL,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        owner_token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm="HS256")
        headers = {"Authorization": f"Bearer {owner_token}"}

        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["role"] == "ADMIN"
    finally:
        owner_user.keycloak_user_id = orig_sub
        db.commit()

def test_keycloak_tampered_jwt_signature_rejected(client: TestClient):
    """JWT bị sửa đổi chữ ký hoặc payload (Fake JWT) sẽ bị từ chối với lỗi 401 Unauthorized."""
    token = get_real_keycloak_token()
    parts = token.split(".")
    tampered_token = f"{parts[0]}.{parts[1]}.tampered_invalid_signature"

    headers = {"Authorization": f"Bearer {tampered_token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401

def test_keycloak_wrong_issuer_rejected(client: TestClient):
    """Giả lập token từ Issuer không hợp lệ sẽ bị từ chối 401."""
    bad_payload = {
        "sub": "fake-user-uuid",
        "email": "hacker@evil.com",
        "iss": "http://evil-hacker.com/realms/fake",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    bad_token = jwt.encode(bad_payload, "secret", algorithm="HS256")

    headers = {"Authorization": f"Bearer {bad_token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401

def test_keycloak_expired_token_rejected(client: TestClient):
    """Token hết hạn (expired token) bị từ chối 401."""
    expired_payload = {
        "sub": "testuser",
        "email": "testuser@student.tdmu.edu.vn",
        "iss": settings.KEYCLOAK_ISSUER_URL,
        "exp": datetime.now(timezone.utc) - timedelta(seconds=60),
    }
    expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm="HS256")

    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
