import pytest
from unittest.mock import patch, MagicMock
import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.services.ai_assistant import AIAssistantService
from app.schemas.assistant import AssistantChatResponse

def test_ollama_chat_success(db: Session, admin_user: User):
    """Test successful Ollama API call returns natural language answer and is_fallback=False."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "role": "assistant",
            "content": "Tổng quan hệ thống DX-Asset hiện tại có tổng cộng **7 tài sản** đang được quản lý."
        }
    }

    with patch("httpx.Client.post", return_value=mock_response):
        res = AIAssistantService.process_chat(db, admin_user, "thống kê tổng quan tài sản")
        assert isinstance(res, AssistantChatResponse)
        assert "7 tài sản" in res.answer
        assert res.is_fallback is False
        assert res.intent == "ASSET_SUMMARY_COUNT"

def test_ollama_chat_timeout_fallback(db: Session, admin_user: User):
    """Test Ollama timeout gracefully falls back to Rule-Based engine with is_fallback=True."""
    with patch("httpx.Client.post", side_effect=httpx.ReadTimeout("Ollama read timeout")):
        res = AIAssistantService.process_chat(db, admin_user, "thống kê tổng quan tài sản")
        assert isinstance(res, AssistantChatResponse)
        assert res.is_fallback is True
        assert "Thống kê tổng quan tài sản DX-Asset" in res.answer

def test_ollama_chat_unavailable_fallback(db: Session, admin_user: User):
    """Test Ollama connection refused gracefully falls back to Rule-Based engine."""
    with patch("httpx.Client.post", side_effect=httpx.ConnectError("Connection refused")):
        res = AIAssistantService.process_chat(db, admin_user, "thống kê tổng quan tài sản")
        assert isinstance(res, AssistantChatResponse)
        assert res.is_fallback is True
        assert res.intent == "ASSET_SUMMARY_COUNT"

def test_ollama_chat_http_error_fallback(db: Session, admin_user: User):
    """Test Ollama HTTP 500 error gracefully falls back to Rule-Based engine."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("httpx.Client.post", return_value=mock_response):
        res = AIAssistantService.process_chat(db, admin_user, "thống kê tổng quan tài sản")
        assert isinstance(res, AssistantChatResponse)
        assert res.is_fallback is True

def test_ollama_rbac_employee_restriction(client: TestClient, employee_token: str):
    """Test Employee cannot access global analytics, returning HTTP 403 before calling Ollama."""
    headers = {"Authorization": f"Bearer {employee_token}"}
    res = client.post("/api/v1/assistant/chat", json={"message": "thống kê tổng số chi phí tài sản"}, headers=headers)
    assert res.status_code == 403
    assert "Employees cannot access global analytics" in res.json()["detail"]

def test_ollama_mutation_guard(db: Session, admin_user: User):
    """Test explicit mutation query is rejected by Read-Only guard and never sent to Ollama."""
    with patch("httpx.Client.post") as mock_post:
        res = AIAssistantService.process_chat(db, admin_user, "xóa tài sản LAP-001 ngay")
        assert isinstance(res, AssistantChatResponse)
        assert res.intent == "MUTATION_REJECTED"
        assert res.is_fallback is True
        # Ensure HTTP call to Ollama was NOT made for mutation intent
        mock_post.assert_not_called()

def test_ollama_deterministic_process_mining_intents(db: Session, admin_user: User):
    """Test deterministic Process Mining intents bypass LLM and return exact deterministic results."""
    with patch("httpx.Client.post") as mock_post:
        res = AIAssistantService.process_chat(db, admin_user, "quy trình hiện tại thế nào?")
        assert isinstance(res, AssistantChatResponse)
        assert res.intent == "PROCESS_MINING_SUMMARY"
        mock_post.assert_not_called()
