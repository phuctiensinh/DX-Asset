import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.enums import AssetStatus, IncidentCategory, IncidentPriority

def test_chat_unauthenticated(client: TestClient):
    """Verify POST /api/v1/assistant/chat requires authentication."""
    response = client.post("/api/v1/assistant/chat", json={"message": "Có bao nhiêu tài sản?"})
    assert response.status_code == 401

def test_chat_empty_message(client: TestClient, admin_token: str):
    """Verify empty message payload returns HTTP 400 Bad Request."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.post("/api/v1/assistant/chat", headers=headers, json={"message": "   "})
    assert response.status_code == 400
    assert "Nội dung câu hỏi không được để trống" in response.json()["detail"]

def test_chat_mutation_rejected(client: TestClient, admin_token: str):
    """Verify AI Assistant strictly rejects data mutation/deletion requests (Read-Only policy)."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    mutation_queries = [
        "Xóa laptop AST-LAP-001 khỏi cơ sở dữ liệu",
        "Tạo tài sản mới có tên MacBook Pro",
        "Update trạng thái tài sản AST-001 thành RETIRED",
        "Sửa thông tin phiếu sự cố",
        "Cấp phát laptop AST-001 cho Nguyễn Văn A",
        "Hãy cấp phát tài sản này cho nhân viên A"
    ]
    
    for query in mutation_queries:
        response = client.post("/api/v1/assistant/chat", headers=headers, json={"message": query})
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "MUTATION_REJECTED", f"Query '{query}' failed to trigger MUTATION_REJECTED"
        assert "Read-Only" in data["answer"] or "chỉ đọc" in data["answer"]

def test_chat_assigned_assets_read_inquiries(client: TestClient, admin_token: str):
    """
    Regression test: Verify asking about assigned assets (e.g. 'Có bao nhiêu tài sản đang được cấp phát?')
    is correctly recognized as a READ INQUIRY and does NOT trigger MUTATION_REJECTED.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    read_queries = [
        "Có bao nhiêu tài sản đang được cấp phát?",
        "Cho tôi xem các tài sản đang được cấp phát",
        "Có bao nhiêu laptop đang được cấp phát?",
        "Danh sách tài sản đang được cấp phát"
    ]

    for query in read_queries:
        response = client.post("/api/v1/assistant/chat", headers=headers, json={"message": query})
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] != "MUTATION_REJECTED", f"Query '{query}' was incorrectly rejected as mutation"
        assert data["intent"] in ["ASSIGNED_ASSETS_QUERY", "ASSET_SUMMARY_COUNT", "SEARCH_ASSETS"]
        assert "cấp phát" in data["answer"].lower() or "tài sản" in data["answer"].lower()

def test_chat_asset_count_query(client: TestClient, admin_token: str):
    """Verify natural language query asking for total asset count."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.post("/api/v1/assistant/chat", headers=headers, json={"message": "Có bao nhiêu tài sản đang có trong hệ thống?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] in ["ASSET_SUMMARY_COUNT", "UNASSIGNED_ASSETS", "SEARCH_ASSETS"]
    assert "tài sản" in data["answer"].lower()

def test_chat_specific_asset_code(client: TestClient, admin_token: str, db: Session):
    """Verify querying specific asset code returns accurate DB details and source tags."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    unique_suffix = str(uuid.uuid4())[:8].upper()
    asset_code = f"AST-AI-{unique_suffix}"
    asset_name = f"AI Test Laptop {unique_suffix}"

    # Create asset
    create_res = client.post(
        "/api/v1/assets",
        headers=headers,
        json={
            "asset_code": asset_code,
            "name": asset_name,
            "category": "Laptop",
            "brand": "Lenovo",
            "model": "ThinkPad",
            "status": AssetStatus.IN_STOCK.value,
        }
    )
    assert create_res.status_code == 201

    # Query assistant about this asset
    chat_res = client.post("/api/v1/assistant/chat", headers=headers, json={"message": f"Laptop {asset_code} đang ở đâu và trạng thái gì?"})
    assert chat_res.status_code == 200
    data = chat_res.json()

    assert data["intent"] == "ASSET_DETAIL"
    assert asset_code in data["answer"]
    assert asset_name in data["answer"]
    assert len(data["sources"]) > 0
    assert data["sources"][0]["code"] == asset_code

def test_chat_incident_ticket_query(client: TestClient, admin_token: str, db: Session):
    """Verify querying incident ticket code returns ticket details."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    unique_suffix = str(uuid.uuid4())[:8].upper()
    asset_code = f"AST-INC-{unique_suffix}"
    ticket_code = f"INC-AI-{unique_suffix}"

    # 1. Create asset
    asset_res = client.post(
        "/api/v1/assets",
        headers=headers,
        json={
            "asset_code": asset_code,
            "name": f"Incident Asset {unique_suffix}",
            "category": "Monitor",
            "status": AssetStatus.IN_STOCK.value,
        }
    )
    assert asset_res.status_code == 201
    asset_id = asset_res.json()["id"]

    # 2. Create incident
    inc_res = client.post(
        "/api/v1/incidents",
        headers=headers,
        json={
            "ticket_code": ticket_code,
            "asset_id": asset_id,
            "title": f"Monitor Display Issue {unique_suffix}",
            "description": "Screen shows vertical green line.",
            "category": IncidentCategory.HARDWARE.value,
            "priority": IncidentPriority.HIGH.value,
        }
    )
    assert inc_res.status_code == 201

    # 3. Query assistant about ticket
    chat_res = client.post("/api/v1/assistant/chat", headers=headers, json={"message": f"Phiếu {ticket_code} đang ở trạng thái nào?"})
    assert chat_res.status_code == 200
    data = chat_res.json()

    assert data["intent"] == "INCIDENT_DETAIL"
    assert ticket_code in data["answer"]
    assert "Monitor Display Issue" in data["answer"]

def test_chat_unassigned_assets_query(client: TestClient, admin_token: str):
    """Verify query asking for unassigned / in-stock assets."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.post("/api/v1/assistant/chat", headers=headers, json={"message": "Tài sản nào chưa được cấp phát?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "UNASSIGNED_ASSETS"
    assert "chưa cấp phát" in data["answer"].lower() or "có sẵn" in data["answer"].lower()

def test_chat_recent_history_query(client: TestClient, admin_token: str):
    """Verify query asking for asset audit history."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.post("/api/v1/assistant/chat", headers=headers, json={"message": "Cho tôi xem lịch sử tài sản gần đây?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "RECENT_HISTORY"
    assert "nhật ký" in data["answer"].lower() or "lịch sử" in data["answer"].lower()

def test_chat_non_existent_asset(client: TestClient, admin_token: str):
    """Verify querying non-existent asset code does not hallucinate fake details."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.post("/api/v1/assistant/chat", headers=headers, json={"message": "Laptop AST-NON-EXISTENT-999999 đang ở đâu?"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] != "ASSET_DETAIL"
