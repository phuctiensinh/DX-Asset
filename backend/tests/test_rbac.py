from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import require_roles, get_current_user
from app.models.user import User
from app.models.enums import UserRole

# Create a temporary test router to verify RBAC behavior
test_router = APIRouter(prefix="/api/v1/test-rbac", tags=["Test RBAC"])

@test_router.get("/admin-only")
def admin_only_endpoint(current_user: User = Depends(require_roles(UserRole.ADMIN))):
    return {"message": "Admin access granted", "user_id": current_user.id}

@test_router.get("/admin-or-it")
def admin_or_it_endpoint(current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.IT_ASSET_MANAGER))):
    return {"message": "Admin or IT access granted", "role": str(current_user.role)}

app.include_router(test_router)

def test_rbac_admin_only_with_admin_token(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/api/v1/test-rbac/admin-only", headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Admin access granted"

def test_rbac_admin_only_with_employee_token(client: TestClient, employee_token: str):
    headers = {"Authorization": f"Bearer {employee_token}"}
    response = client.get("/api/v1/test-rbac/admin-only", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Operation not permitted for this user role"

def test_rbac_admin_or_it_with_employee_token(client: TestClient, employee_token: str):
    headers = {"Authorization": f"Bearer {employee_token}"}
    response = client.get("/api/v1/test-rbac/admin-or-it", headers=headers)
    assert response.status_code == 403
