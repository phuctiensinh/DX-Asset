import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, UserRole, Incident, IncidentCategory, IncidentPriority, IncidentStatus, Asset, AssetStatus
from app.services.smart_routing import SmartRoutingService, QUEUE_MAPPING

def test_smart_routing_service_classification():
    # 1. Hardware text
    res_hw = SmartRoutingService.classify_incident_text("Laptop bị hỏng màn hình", "Màn hình laptop không lên nguồn")
    assert res_hw.category == IncidentCategory.HARDWARE
    assert res_hw.queue == "HARDWARE_SUPPORT"
    assert res_hw.confidence >= 0.75

    # 2. Software text
    res_sw = SmartRoutingService.classify_incident_text("Lỗi phần mềm Excel", "Không mở được ứng dụng office excel")
    assert res_sw.category == IncidentCategory.SOFTWARE
    assert res_sw.queue == "SOFTWARE_SUPPORT"

    # 3. Network text
    res_nw = SmartRoutingService.classify_incident_text("Mất mạng Wi-Fi", "Không thể truy cập internet cisco switch")
    assert res_nw.category == IncidentCategory.NETWORK
    assert res_nw.queue == "NETWORK_SUPPORT"

    # 4. Fallback/Unknown text
    res_oth = SmartRoutingService.classify_incident_text("Vấn đề lạ", "Yêu cầu kiểm tra tài sản này")
    assert res_oth.category == IncidentCategory.OTHER
    assert res_oth.queue == "GENERAL_SUPPORT"

def test_queue_mapping_coverage():
    for cat in IncidentCategory:
        q = SmartRoutingService.get_queue_for_category(cat)
        assert isinstance(q, str)
        assert len(q) > 0

def test_smart_routing_api_rbac_employee_denied(client: TestClient, employee_token: str):
    headers = {"Authorization": f"Bearer {employee_token}"}

    # Classify endpoint forbidden for EMPLOYEE
    resp_classify = client.post("/api/v1/incidents/1/classify", headers=headers)
    assert resp_classify.status_code == 403

    # Recommendations endpoint forbidden for EMPLOYEE
    resp_recs = client.get("/api/v1/incidents/1/recommendations", headers=headers)
    assert resp_recs.status_code == 403

    # Assign endpoint forbidden for EMPLOYEE
    resp_assign = client.post("/api/v1/incidents/1/assign", json={"technician_id": 1}, headers=headers)
    assert resp_assign.status_code == 403

    # Skills endpoint forbidden for EMPLOYEE
    resp_skills = client.get("/api/v1/users/technicians/skills", headers=headers)
    assert resp_skills.status_code == 403

def test_smart_routing_api_admin_success(client: TestClient, admin_token: str, db: Session):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Fetch technicians skills & profiles
    resp_skills = client.get("/api/v1/users/technicians/skills", headers=headers)
    assert resp_skills.status_code == 200
    techs = resp_skills.json()
    assert isinstance(techs, list)
    assert len(techs) > 0

    # 2. Get recommendations for an incident
    incident = db.query(Incident).first()
    if incident:
        resp_recs = client.get(f"/api/v1/incidents/{incident.id}/recommendations", headers=headers)
        assert resp_recs.status_code == 200
        rec_data = resp_recs.json()
        assert rec_data["incident_id"] == incident.id
        assert "recommendations" in rec_data
        assert len(rec_data["recommendations"]) > 0

        # Verify 100-pt score math & non-empty reasons
        top_rec = rec_data["recommendations"][0]
        assert top_rec["total_score"] <= 100.0
        assert len(top_rec["reasons"]) == 3

        # 3. Classify incident
        resp_class = client.post(f"/api/v1/incidents/{incident.id}/classify", headers=headers)
        assert resp_class.status_code == 200
        class_data = resp_class.json()
        assert "suggested_queue" in class_data

        # 4. Assign technician
        tech_user_id = top_rec["user_id"]
        resp_assign = client.post(
            f"/api/v1/incidents/{incident.id}/assign",
            json={"technician_id": tech_user_id, "notes": "Phân công xử lý bởi Smart Routing Test"},
            headers=headers
        )
        assert resp_assign.status_code == 200
        assigned_data = resp_assign.json()
        assert assigned_data["assigned_it_id"] == tech_user_id

def test_set_technician_skill(client: TestClient, admin_token: str, db: Session):
    headers = {"Authorization": f"Bearer {admin_token}"}
    it_user = db.query(User).filter(User.role == UserRole.IT_ASSET_MANAGER).first()
    assert it_user is not None

    resp = client.post(
        f"/api/v1/users/{it_user.id}/skills",
        json={"category": "HARDWARE", "skill_level": 5},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == it_user.id
    assert data["category"] == "HARDWARE"
    assert data["skill_level"] == 5
