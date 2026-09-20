import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.asset import Asset, AssetStatus
from app.models.incident import Incident, IncidentCategory, IncidentPriority, IncidentStatus
from app.models.maintenance import Maintenance, MaintenanceStatus
from app.models.user import User, UserRole
from app.services.knowledge_base import KnowledgeBaseService
from app.services.ai_assistant import AIAssistantService


def test_knowledge_base_similarity_scoring_and_eligibility(db: Session, admin_user: User):
    """
    Tests 1, 2, 3, 4, 5, 6, 7, 8, 9, 10:
    - Eligible vs Ineligible knowledge sources (only RESOLVED/CLOSED with non-empty resolution_notes)
    - Exclude self target incident
    - Category match scoring (+40)
    - Keyword Jaccard text overlap scoring (+0 to +40)
    - Asset type match scoring (+10)
    - Resolution bonus (+10)
    - Max score <= 100
    - Descending order ranking
    - Similarity reasons explanation in Vietnamese
    - Limit parameter & Min score filtering
    """
    # 1. Create a test Asset
    asset1 = Asset(
        asset_code=f"KB-AST-01-{datetime.now().timestamp()}",
        name="Dell XPS Laptop 15",
        category="Laptop",
        brand="Dell",
        model="XPS 15",
        serial_number=f"SN-KB-01-{datetime.now().timestamp()}",
        status=AssetStatus.IN_STOCK
    )
    asset2 = Asset(
        asset_code=f"KB-AST-02-{datetime.now().timestamp()}",
        name="HP LaserJet Printer",
        category="Printer",
        brand="HP",
        model="M404dn",
        serial_number=f"SN-KB-02-{datetime.now().timestamp()}",
        status=AssetStatus.IN_STOCK
    )
    db.add_all([asset1, asset2])
    db.commit()

    # 2. Target incident A (RESOLVED, HARDWARE)
    target_inc = Incident(
        ticket_code=f"INC-TGT-{datetime.now().timestamp()}",
        title="Màn hình laptop bị chớp giật xanh nhấp nháy",
        description="Màn hình hiển thị sọc xanh và chớp nháy liên tục khi cắm sạc laptop dell xps",
        category=IncidentCategory.HARDWARE,
        priority=IncidentPriority.HIGH,
        status=IncidentStatus.RESOLVED,
        reporter_id=admin_user.id,
        asset_id=asset1.id,
        resolution_notes="Đã thay cáp màn hình laptop và vệ sinh chân cắm."
    )
    db.add(target_inc)
    db.commit()

    # Candidate 1: High similarity (RESOLVED, HARDWARE, same asset category, resolved notes)
    cand1 = Incident(
        ticket_code=f"INC-CND1-{datetime.now().timestamp()}",
        title="Laptop bị chớp màn hình sọc xanh",
        description="Màn hình laptop xps bị chớp nháy sọc ngang khi dùng sạc",
        category=IncidentCategory.HARDWARE,
        priority=IncidentPriority.MEDIUM,
        status=IncidentStatus.RESOLVED,
        reporter_id=admin_user.id,
        asset_id=asset1.id,
        resolution_notes="Đã ép lại cổ cáp màn hình và thay sạc adapter mới."
    )

    # Candidate 2: Low similarity / Different category (RESOLVED, SOFTWARE, different asset)
    cand2 = Incident(
        ticket_code=f"INC-CND2-{datetime.now().timestamp()}",
        title="Lỗi phông chữ phần mềm Office",
        description="Không gõ được tiếng Việt trong word excel",
        category=IncidentCategory.SOFTWARE,
        priority=IncidentPriority.LOW,
        status=IncidentStatus.CLOSED,
        reporter_id=admin_user.id,
        asset_id=asset2.id,
        resolution_notes="Cài đặt lại Unikey 64-bit và chọn bảng mã Unicode."
    )

    # Candidate 3: Ineligible (OPEN status, non-empty notes)
    cand3 = Incident(
        ticket_code=f"INC-CND3-{datetime.now().timestamp()}",
        title="Màn hình bị chớp",
        description="Màn hình chớp nháy",
        category=IncidentCategory.HARDWARE,
        priority=IncidentPriority.HIGH,
        status=IncidentStatus.OPEN,
        reporter_id=admin_user.id,
        asset_id=asset1.id,
        resolution_notes="Đang kiểm tra"
    )

    # Candidate 4: Ineligible (RESOLVED status, EMPTY notes)
    cand4 = Incident(
        ticket_code=f"INC-CND4-{datetime.now().timestamp()}",
        title="Màn hình bị sọc",
        description="Màn hình laptop sọc",
        category=IncidentCategory.HARDWARE,
        priority=IncidentPriority.HIGH,
        status=IncidentStatus.RESOLVED,
        reporter_id=admin_user.id,
        asset_id=asset1.id,
        resolution_notes="   "  # Whitespace only
    )

    db.add_all([cand1, cand2, cand3, cand4])
    db.commit()

    # Attach maintenance to cand1 for resolution bonus test
    maint1 = Maintenance(
        maintenance_code=f"MNT-KB-{datetime.now().timestamp()}",
        incident_id=cand1.id,
        asset_id=asset1.id,
        title="Sửa cáp màn hình",
        description="Chi tiết sửa chữa cáp màn hình",
        status=MaintenanceStatus.COMPLETED,
        start_date=datetime.now(timezone.utc),
        completed_date=datetime.now(timezone.utc),
        repair_cost=150000.0
    )
    db.add(maint1)
    db.commit()

    # Test Query
    res = KnowledgeBaseService.get_similar_incidents(db, target_inc.id, limit=5, min_score=10)

    # 1 & 2. Eligibility & Exclude Self
    found_ids = [item.incident_id for item in res.items]
    assert target_inc.id not in found_ids, "Target incident must exclude self"
    assert cand3.id not in found_ids, "Ineligible candidate with status OPEN must be excluded"
    assert cand4.id not in found_ids, "Ineligible candidate with empty resolution notes must be excluded"
    assert cand1.id in found_ids, "Eligible candidate 1 must be found"

    # 3. Descending order ranking
    scores = [item.similarity_score for item in res.items]
    assert scores == sorted(scores, reverse=True), "Items must be sorted in descending score order"

    # 4. Score <= 100
    for score in scores:
        assert 0 <= score <= 100, "Similarity score must be between 0 and 100"

    # 5. Check Candidate 1 breakdown (Category match + text overlap + asset match + resolution bonus)
    top_item = res.items[0]
    assert top_item.incident_id == cand1.id
    assert top_item.similarity_score >= 50
    assert any("Cùng danh mục sự cố" in r for r in top_item.similarity_reasons)
    assert any("Cùng loại tài sản" in r for r in top_item.similarity_reasons)
    assert any("Có phương án giải quyết" in r or "bảo trì" in r for r in top_item.similarity_reasons)
    assert top_item.linked_maintenance is not None
    assert top_item.linked_maintenance.repair_cost == 150000.0

    # 6. Limit parameter
    limit_res = KnowledgeBaseService.get_similar_incidents(db, target_inc.id, limit=1, min_score=0)
    assert len(limit_res.items) == 1

    # 7. Min score filtering
    high_min_res = KnowledgeBaseService.get_similar_incidents(db, target_inc.id, limit=5, min_score=99)
    assert len(high_min_res.items) == 0 or all(item.similarity_score >= 99 for item in high_min_res.items)


def test_api_get_similar_incidents_endpoint(client: TestClient, admin_token: str, employee_token: str, db: Session, admin_user: User):
    """
    Tests 11, 12:
    - GET /api/v1/incidents/{incident_id}/similar read-only endpoint
    - 404 for non-existent incident
    - RBAC authorization check (Employee & Admin can read)
    """
    asset = db.query(Asset).first()
    assert asset is not None, "An asset must exist in DB for test"

    # Create target resolved incident
    inc = Incident(
        ticket_code=f"INC-API-{datetime.now().timestamp()}",
        title="Lỗi mất kết nối mạng Wifi công ty",
        description="Máy tính không bắt được wifi văn phòng tầng 3",
        category=IncidentCategory.NETWORK,
        priority=IncidentPriority.MEDIUM,
        status=IncidentStatus.RESOLVED,
        reporter_id=admin_user.id,
        asset_id=asset.id,
        resolution_notes="Khởi động lại router wifi tầng 3 và gia hạn cấp IP."
    )
    db.add(inc)
    db.commit()

    # 1. Non-existent incident -> 404
    resp = client.get(
        "/api/v1/incidents/999999/similar",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 404
    assert "Không tìm thấy" in resp.json()["detail"]

    # 2. Valid request with Admin token
    resp = client.get(
        f"/api/v1/incidents/{inc.id}/similar?limit=3&min_score=10",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "target_incident_id" in data
    assert data["target_incident_id"] == inc.id
    assert "total_found" in data
    assert "items" in data

    # 3. Valid request with Employee token (RBAC allows read-only access)
    resp_emp = client.get(
        f"/api/v1/incidents/{inc.id}/similar",
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert resp_emp.status_code == 200


def test_ai_assistant_similar_incident_queries(db: Session, admin_user: User):
    """
    Tests 13, 14:
    - AI Assistant query intents for SIMILAR_INCIDENT_QUERY and KNOWLEDGE_BASE_QUERY
    - Read-only guard (AI output only suggests/informs, does not mutate DB)
    """
    asset = db.query(Asset).first()
    assert asset is not None

    ticket_code = f"INC-KB888-{datetime.now().timestamp()}"

    # Create resolved incident for query
    inc = Incident(
        ticket_code=ticket_code,
        title="Hỏng ổ cứng SSD NVMe không nhận trong BIOS",
        description="Laptop bị sập nguồn đột ngột sau đó báo No Boot Device",
        category=IncidentCategory.HARDWARE,
        priority=IncidentPriority.HIGH,
        status=IncidentStatus.RESOLVED,
        reporter_id=admin_user.id,
        asset_id=asset.id,
        resolution_notes="Thay ổ cứng SSD NVMe 512GB và cài lại Windows 11."
    )
    db.add(inc)
    db.commit()

    # 1. Query with ticket code
    res1 = AIAssistantService.process_chat(
        db=db,
        current_user=admin_user,
        user_message=f"Có sự cố nào tương tự {ticket_code} không?"
    )
    assert res1.intent in ("SIMILAR_INCIDENT_QUERY", "KNOWLEDGE_BASE_QUERY", "INCIDENT_DETAIL")
    assert "sự cố" in res1.answer.lower() or "knowledge base" in res1.answer.lower() or "tương tự" in res1.answer.lower()

    # 2. General Knowledge base query
    res2 = AIAssistantService.process_chat(
        db=db,
        current_user=admin_user,
        user_message="Đã từng gặp lỗi ổ cứng SSD không nhận chưa?"
    )
    assert res2.intent in ("SIMILAR_INCIDENT_QUERY", "KNOWLEDGE_BASE_QUERY", "SEARCH_ASSETS")
    assert res2.answer is not None

    # 3. Verify no mutation occurred (Incident status remains RESOLVED)
    db.refresh(inc)
    assert inc.status == IncidentStatus.RESOLVED
    assert inc.resolution_notes == "Thay ổ cứng SSD NVMe 512GB và cài lại Windows 11."
