import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.enums import AssetStatus, IncidentCategory, IncidentPriority

def test_get_dashboard_summary_unauthenticated(client: TestClient):
    """Verify GET /api/v1/dashboard/summary requires authentication."""
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 401

def test_get_dashboard_summary_success(client: TestClient, admin_token: str):
    """Verify authenticated user can fetch dashboard summary with valid structure."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/api/v1/dashboard/summary", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert "assets" in data
    assert "assignments" in data
    assert "incidents" in data
    assert "departments" in data
    assert "recent_activities" in data

    # Validate asset summary fields
    assets = data["assets"]
    assert "total" in assets
    assert "by_status" in assets
    assert "in_stock" in assets
    assert "assigned" in assets
    assert "in_maintenance" in assets
    assert "damaged" in assets
    assert "retired" in assets
    assert "lost" in assets
    assert "inactive" in assets
    assert assets["total"] >= 0

    # Validate assignment summary fields
    assignments = data["assignments"]
    assert "total" in assignments
    assert "active" in assignments
    assert "returned" in assignments

    # Validate incident summary fields
    incidents = data["incidents"]
    assert "total" in incidents
    assert "open" in incidents
    assert "pending" in incidents

    # Validate departments list
    departments = data["departments"]
    assert isinstance(departments, list)

    # Validate recent activities list
    activities = data["recent_activities"]
    assert isinstance(activities, list)

def test_dashboard_aggregation_dynamic_update(client: TestClient, admin_token: str, employee_user, db: Session):
    """
    Verify creating an asset and reporting an incident updates dashboard stats dynamically.
    Uses UUIDs to ensure 100% test idempotency across consecutive test executions.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Fetch initial dashboard stats
    initial_res = client.get("/api/v1/dashboard/summary", headers=headers)
    assert initial_res.status_code == 200
    initial_data = initial_res.json()
    initial_total_assets = initial_data["assets"]["total"]
    initial_in_stock = initial_data["assets"]["in_stock"]
    initial_total_incidents = initial_data["incidents"]["total"]

    # 2. Create a new asset with unique UUID code
    unique_suffix = str(uuid.uuid4())[:8].upper()
    asset_code = f"AST-DASH-{unique_suffix}"
    create_asset_res = client.post(
        "/api/v1/assets",
        headers=headers,
        json={
            "asset_code": asset_code,
            "name": f"Dashboard Test Laptop {unique_suffix}",
            "category": "Laptop",
            "brand": "Dell",
            "model": "XPS 15",
            "status": AssetStatus.IN_STOCK.value,
        }
    )
    assert create_asset_res.status_code == 201
    asset_id = create_asset_res.json()["id"]

    # 3. Report an incident on the newly created asset
    ticket_code = f"INC-DASH-{unique_suffix}"
    create_incident_res = client.post(
        "/api/v1/incidents",
        headers=headers,
        json={
            "ticket_code": ticket_code,
            "asset_id": asset_id,
            "title": f"Screen Flicker {unique_suffix}",
            "description": "Display screen flickers when plugged into power.",
            "category": IncidentCategory.HARDWARE.value,
            "priority": IncidentPriority.HIGH.value,
        }
    )
    assert create_incident_res.status_code == 201

    # 4. Fetch updated dashboard stats and verify incremented counts
    updated_res = client.get("/api/v1/dashboard/summary", headers=headers)
    assert updated_res.status_code == 200
    updated_data = updated_res.json()

    assert updated_data["assets"]["total"] == initial_total_assets + 1
    assert updated_data["assets"]["in_stock"] == initial_in_stock + 1
    assert updated_data["incidents"]["total"] == initial_total_incidents + 1

    # 5. Verify recent activities contains the newly generated history event
    recent_activities = updated_data["recent_activities"]
    assert len(recent_activities) > 0
    # At least one activity should reference our new asset_id or asset_code
    recent_codes = [act["asset_code"] for act in recent_activities]
    assert asset_code in recent_codes
