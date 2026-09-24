import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.models import Asset, AssetAssignment, Incident, Maintenance, User, UserRole
from app.models.process_case import ProcessCase
from app.models.process_event import ProcessEvent

BASE = "/api/v1/process-mining"
ENDPOINTS = [
    f"{BASE}/summary",
    f"{BASE}/variants",
    f"{BASE}/bottlenecks",
    f"{BASE}/cases",
]


def _headers(user: User) -> dict[str, str]:
    token = create_access_token(subject=user.id, extra_claims={"email": user.email, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("path", ENDPOINTS)
def test_process_mining_requires_authentication(client: TestClient, path: str):
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"Authorization": "Bearer invalid-token"}).status_code == 401


def test_process_mining_role_matrix(client: TestClient, db, admin_user, it_manager_user, employee_user):
    manager = db.query(User).filter(User.role == UserRole.MANAGER).first()
    assert manager is not None, "The API RBAC test requires the seeded MANAGER user"
    allowed = (admin_user, it_manager_user, manager)
    for path in ENDPOINTS:
        for user in allowed:
            assert client.get(path, headers=_headers(user)).status_code == 200
        assert client.get(path, headers=_headers(employee_user)).status_code == 403
    case = db.query(ProcessCase).first()
    if case is not None:
        detail_path = f"{BASE}/cases/{case.id}"
        for user in allowed:
            assert client.get(detail_path, headers=_headers(user)).status_code == 200
        assert client.get(detail_path, headers=_headers(employee_user)).status_code == 403


def test_process_mining_summary_filter_validation_and_structure(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    responses = [
        client.get(f"{BASE}/summary", headers=headers),
        client.get(f"{BASE}/summary?case_type=INCIDENT", headers=headers),
        client.get(f"{BASE}/summary?source=BACKFILL", headers=headers),
        client.get(f"{BASE}/summary?date_from=2024-01-01T00:00:00Z", headers=headers),
        client.get(f"{BASE}/summary?date_to=2025-01-01T00:00:00%2B00:00", headers=headers),
        client.get(f"{BASE}/summary?case_type=INCIDENT&source=LIVE&date_from=2024-01-01T00:00:00Z&date_to=2025-01-01T00:00:00Z", headers=headers),
    ]
    assert all(response.status_code == 200 for response in responses)
    body = responses[0].json()
    assert {"cohort", "total_cases", "completed_cases", "total_events", "data_quality"} <= body.keys()
    assert isinstance(body["observed_flow"], list)
    assert client.get(f"{BASE}/summary?case_type=UNKNOWN", headers=headers).status_code == 422
    assert client.get(f"{BASE}/summary?source=UNKNOWN", headers=headers).status_code == 422
    assert client.get(f"{BASE}/summary?date_from=2024-01-01T00:00:00", headers=headers).status_code == 422
    assert client.get(f"{BASE}/summary?date_from=2025-01-01T00:00:00Z&date_to=2024-01-01T00:00:00Z", headers=headers).status_code == 422


def test_variants_bottlenecks_and_filters(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    variants = client.get(f"{BASE}/variants?source=BACKFILL&date_from=2024-01-01T00:00:00Z", headers=headers)
    assert variants.status_code == 200
    assert isinstance(variants.json()["variants"], list)
    assert variants.json()["variants"] == sorted(
        variants.json()["variants"], key=lambda row: (-row["case_count"], row["event_sequence"])
    )
    assert client.get(f"{BASE}/bottlenecks", headers=headers).status_code == 200
    assert client.get(f"{BASE}/bottlenecks?min_sample=1&case_type=INCIDENT", headers=headers).status_code == 200
    assert client.get(f"{BASE}/bottlenecks?min_sample=0", headers=headers).status_code == 422


def test_case_list_pagination_detail_and_not_found(client, admin_token, db):
    headers = {"Authorization": f"Bearer {admin_token}"}
    first = client.get(f"{BASE}/cases?page=1&page_size=2", headers=headers)
    assert first.status_code == 200
    body = first.json()
    assert body["page"] == 1 and body["page_size"] == 2
    assert len(body["items"]) <= 2
    assert {"items", "total", "page", "page_size"} <= body.keys()
    assert "_sa_instance_state" not in str(body)
    assert body["items"] == sorted(
        body["items"], key=lambda item: (item["created_at"], item["case_id"]), reverse=True
    )
    filtered = client.get(
        f"{BASE}/cases?case_type=INCIDENT&source=BACKFILL&date_from=2024-01-01T00:00:00Z&page_size=1",
        headers=headers,
    )
    assert filtered.status_code == 200
    assert all(item["case_type"] == "INCIDENT" for item in filtered.json()["items"])
    assert client.get(f"{BASE}/cases?page=999&page_size=2", headers=headers).status_code == 200
    assert client.get(f"{BASE}/cases?page=0", headers=headers).status_code == 422
    assert client.get(f"{BASE}/cases?page_size=101", headers=headers).status_code == 422
    if body["items"]:
        item = body["items"][0]
        assert {"case_id", "case_type", "event_count", "source_coverage", "completed"} <= item.keys()
        detail = client.get(f"{BASE}/cases/{item['case_id']}", headers=headers)
        assert detail.status_code == 200
        events = detail.json()["events"]
        assert [event["sequence"] for event in events] == sorted(event["sequence"] for event in events)
        assert all("source" in event and "timestamp_quality" in event for event in events)
    assert client.get(f"{BASE}/cases/2147483647", headers=headers).status_code == 404


def test_process_mining_get_endpoints_are_read_only(client, admin_token, db):
    models = (ProcessCase, ProcessEvent, Incident, Maintenance, Asset, AssetAssignment)
    before = [db.query(model).count() for model in models]
    headers = {"Authorization": f"Bearer {admin_token}"}
    for path in ENDPOINTS:
        assert client.get(path, headers=headers).status_code == 200
    case = db.query(ProcessCase).first()
    if case:
        assert client.get(f"{BASE}/cases/{case.id}", headers=headers).status_code == 200
    assert before == [db.query(model).count() for model in models]


def test_openapi_registers_process_mining_contract(client):
    paths = client.get("/openapi.json").json()["paths"]
    expected = [*ENDPOINTS, f"{BASE}/cases/{{case_id}}"]
    for path in expected:
        assert path in paths
        assert "get" in paths[path]
        assert "security" in paths[path]["get"]
    assert "ProcessMiningCasesResponse" in str(paths[f"{BASE}/cases"]["get"]["responses"])
