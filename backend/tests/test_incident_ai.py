import json
from unittest.mock import MagicMock, patch

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Incident, User
from app.models.enums import IncidentCategory, IncidentPriority
from app.services.incident_ai import IncidentAIService


def _ollama_reply(content: str) -> MagicMock:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": {"role": "assistant", "content": content}}
    return mock_response


def mock_ollama(reply: MagicMock = None, error: Exception = None):
    """Mock only the HTTP client used by ollama_client (patching httpx.Client.post would also hit TestClient)."""
    client_cls = MagicMock()
    post = client_cls.return_value.__enter__.return_value.post
    if error is not None:
        post.side_effect = error
    else:
        post.return_value = reply
    return patch("app.services.ollama_client.httpx.Client", client_cls)


OLLAMA_DOWN = httpx.ConnectError("Connection refused")


# --- Triage suggestion (category + priority) ---

def test_triage_uses_ollama_answer():
    reply = _ollama_reply(json.dumps({"category": "network", "priority": "HIGH", "reasoning": "Mất kết nối mạng toàn máy."}))
    with mock_ollama(reply=reply):
        res = IncidentAIService.suggest_triage("Không vào được mạng", "Máy tính không truy cập được internet")
    assert res.source == "AI"
    assert res.category == IncidentCategory.NETWORK
    assert res.priority == IncidentPriority.HIGH


def test_triage_falls_back_when_ollama_down():
    with mock_ollama(error=OLLAMA_DOWN):
        res = IncidentAIService.suggest_triage("Laptop không lên nguồn", "Bấm nút nguồn laptop không có phản ứng")
    assert res.source == "RULE_BASED"
    assert res.category == IncidentCategory.HARDWARE
    assert res.priority == IncidentPriority.HIGH


def test_triage_falls_back_on_invalid_ai_values():
    reply = _ollama_reply(json.dumps({"category": "PRINTER", "priority": "URGENT", "reasoning": "x"}))
    with mock_ollama(reply=reply):
        res = IncidentAIService.suggest_triage("Ổ cắm bốc khói", "Ổ cắm cạnh máy in bốc khói và có mùi khét")
    assert res.source == "RULE_BASED"
    assert res.priority == IncidentPriority.CRITICAL


def test_triage_falls_back_on_non_json_output():
    with mock_ollama(reply=_ollama_reply("Đây là lỗi phần mềm")):
        res = IncidentAIService.suggest_triage("Excel bị treo", "Mở file excel thì phần mềm bị treo")
    assert res.source == "RULE_BASED"
    assert res.category == IncidentCategory.SOFTWARE


def test_triage_endpoint_available_to_employee(client: TestClient, employee_token: str):
    headers = {"Authorization": f"Bearer {employee_token}"}
    with mock_ollama(error=OLLAMA_DOWN):
        res = client.post(
            "/api/v1/incidents/ai/triage-suggestion",
            json={"title": "Wifi chập chờn", "description": "Thỉnh thoảng mất kết nối wifi"},
            headers=headers,
        )
    assert res.status_code == 200
    data = res.json()
    assert data["category"] == "NETWORK"
    assert data["source"] == "RULE_BASED"


def test_triage_endpoint_validates_input(client: TestClient, employee_token: str):
    headers = {"Authorization": f"Bearer {employee_token}"}
    res = client.post("/api/v1/incidents/ai/triage-suggestion", json={"title": "", "description": "abc"}, headers=headers)
    assert res.status_code == 422


def test_triage_endpoint_requires_login(client: TestClient):
    res = client.post("/api/v1/incidents/ai/triage-suggestion", json={"title": "a", "description": "b"})
    assert res.status_code == 401


# --- Summary ---

def test_summary_ai_and_fallback(client: TestClient, admin_token: str, db: Session):
    incident = db.query(Incident).first()
    headers = {"Authorization": f"Bearer {admin_token}"}

    with mock_ollama(reply=_ollama_reply("Laptop hỏng màn hình, đang chờ xử lý.")):
        res = client.post(f"/api/v1/incidents/{incident.id}/ai/summary", headers=headers)
    assert res.status_code == 200
    assert res.json()["source"] == "AI"
    assert res.json()["summary"] == "Laptop hỏng màn hình, đang chờ xử lý."

    with mock_ollama(error=OLLAMA_DOWN):
        res = client.post(f"/api/v1/incidents/{incident.id}/ai/summary", headers=headers)
    assert res.status_code == 200
    assert res.json()["source"] == "RULE_BASED"
    assert incident.asset.asset_code in res.json()["summary"]


def test_summary_employee_only_own_incident(client: TestClient, employee_token: str, employee_user: User, db: Session):
    headers = {"Authorization": f"Bearer {employee_token}"}
    other = db.query(Incident).filter(Incident.reporter_id != employee_user.id).first()
    if other:
        res = client.post(f"/api/v1/incidents/{other.id}/ai/summary", headers=headers)
        assert res.status_code == 403


def test_summary_not_found(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.post("/api/v1/incidents/99999999/ai/summary", headers=headers)
    assert res.status_code == 404


# --- Troubleshooting steps ---

def test_troubleshooting_ai_and_fallback(client: TestClient, admin_token: str, db: Session):
    incident = db.query(Incident).first()
    headers = {"Authorization": f"Bearer {admin_token}"}

    reply = _ollama_reply(json.dumps({"steps": ["Kiểm tra cáp nguồn", "Thử adapter khác", "  "]}))
    with mock_ollama(reply=reply):
        res = client.post(f"/api/v1/incidents/{incident.id}/ai/troubleshooting", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["source"] == "AI"
    assert data["steps"] == ["Kiểm tra cáp nguồn", "Thử adapter khác"]

    with mock_ollama(error=httpx.ReadTimeout("slow")):
        res = client.post(f"/api/v1/incidents/{incident.id}/ai/troubleshooting", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["source"] == "RULE_BASED"
    assert len(data["steps"]) >= 3


def test_troubleshooting_forbidden_for_employee(client: TestClient, employee_token: str, db: Session):
    incident = db.query(Incident).first()
    headers = {"Authorization": f"Bearer {employee_token}"}
    res = client.post(f"/api/v1/incidents/{incident.id}/ai/troubleshooting", headers=headers)
    assert res.status_code == 403


# --- Classify endpoint (queue routing) ---

def test_classify_uses_ai_then_falls_back(client: TestClient, admin_token: str, db: Session):
    incident = db.query(Incident).first()
    original_category = incident.category
    headers = {"Authorization": f"Bearer {admin_token}"}

    reply = _ollama_reply(json.dumps({"category": "POWER", "priority": "HIGH", "reasoning": "Lỗi nguồn."}))
    with mock_ollama(reply=reply):
        res = client.post(f"/api/v1/incidents/{incident.id}/classify", headers=headers)
    assert res.status_code == 200
    assert res.json()["suggested_queue"] == "INFRASTRUCTURE_SUPPORT"
    assert res.json()["ai_reasoning"].startswith("AI (Ollama)")

    with mock_ollama(error=OLLAMA_DOWN):
        res = client.post(f"/api/v1/incidents/{incident.id}/classify", headers=headers)
    assert res.status_code == 200
    assert not res.json()["ai_reasoning"].startswith("AI (Ollama)")

    # Classification only suggests a queue; the incident category itself must not change
    db.refresh(incident)
    assert incident.category == original_category
