import pytest
from fastapi.testclient import TestClient

def get_token(client: TestClient, email: str, password: str = "password123") -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

def test_list_assets_unauthorized(client: TestClient):
    response = client.get("/api/v1/assets")
    assert response.status_code == 401

def test_list_assets_authorized(client: TestClient):
    token = get_token(client, "employee1@dxasset.local")
    response = client.get(
        "/api/v1/assets",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 7
    assert len(data["items"]) > 0

def test_list_assets_search_and_filter(client: TestClient):
    token = get_token(client, "employee1@dxasset.local")
    
    # Search term
    res_search = client.get(
        "/api/v1/assets?search=Lenovo",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_search.status_code == 200
    search_data = res_search.json()
    assert search_data["total"] >= 1
    assert "Lenovo" in search_data["items"][0]["name"]

    # Filter status
    res_filter = client.get(
        "/api/v1/assets?status=ASSIGNED",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_filter.status_code == 200
    filter_data = res_filter.json()
    for item in filter_data["items"]:
        assert item["status"] == "ASSIGNED"

def test_get_asset_detail(client: TestClient):
    token = get_token(client, "employee1@dxasset.local")
    
    # Get list first to grab an ID
    res_list = client.get("/api/v1/assets", headers={"Authorization": f"Bearer {token}"})
    asset_id = res_list.json()["items"][0]["id"]

    res_detail = client.get(f"/api/v1/assets/{asset_id}", headers={"Authorization": f"Bearer {token}"})
    assert res_detail.status_code == 200
    assert res_detail.json()["id"] == asset_id

def test_get_asset_not_found(client: TestClient):
    token = get_token(client, "employee1@dxasset.local")
    res = client.get("/api/v1/assets/999999", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404

def test_create_asset_permission_denied(client: TestClient):
    token = get_token(client, "employee1@dxasset.local")
    payload = {
        "asset_code": "TEST-EXP-001",
        "name": "Test Laptop",
        "category": "Laptop"
    }
    res = client.post("/api/v1/assets", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403

def test_create_asset_success(client: TestClient):
    import uuid
    unique_suffix = uuid.uuid4().hex[:6].upper()
    code = f"TEST-{unique_suffix}"
    serial = f"SN-{unique_suffix}"

    token = get_token(client, "admin@dxasset.local")
    payload = {
        "asset_code": code,
        "name": "MacBook Pro M3 Max 16 inch",
        "category": "Laptop",
        "brand": "Apple",
        "model": "MacBook Pro 16",
        "serial_number": serial,
        "status": "IN_STOCK",
        "location": "Phòng Server Tầng 3",
        "description": "Máy test tự động"
    }
    res = client.post("/api/v1/assets", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 201
    data = res.json()
    assert data["asset_code"] == code
    assert data["name"] == "MacBook Pro M3 Max 16 inch"

def test_create_asset_duplicate_code(client: TestClient):
    token = get_token(client, "admin@dxasset.local")
    payload = {
        "asset_code": "LAP-001",  # Existing seed asset
        "name": "Duplicate Code Laptop",
        "category": "Laptop"
    }
    res = client.post("/api/v1/assets", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400
    assert "đã tồn tại" in res.json()["detail"]

def test_update_asset_permission_denied(client: TestClient):
    token = get_token(client, "employee1@dxasset.local")
    payload = {"name": "Hacker Updated Name"}
    res = client.patch("/api/v1/assets/1", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403

def test_update_asset_success(client: TestClient):
    token = get_token(client, "it_manager@dxasset.local")
    
    # Get an asset id
    res_list = client.get("/api/v1/assets", headers={"Authorization": f"Bearer {token}"})
    asset = res_list.json()["items"][0]
    asset_id = asset["id"]

    payload = {"location": "Khu vực kiểm thử tự động updated"}
    res = client.patch(f"/api/v1/assets/{asset_id}", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["location"] == "Khu vực kiểm thử tự động updated"
