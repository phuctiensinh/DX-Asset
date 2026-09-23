import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.user import User
from app.models.incident import Incident
from app.models.maintenance import Maintenance
from app.models.enums import (
    AssetStatus,
    IncidentCategory,
    IncidentPriority,
    IncidentStatus,
    MaintenanceStatus,
    UserRole,
)
from app.services.asset_intelligence import AssetIntelligenceService
from app.services.ai_assistant import AIAssistantService


def test_asset_intelligence_no_incidents_or_maintenance(db: Session):
    """Test 1: Asset mới/rỗng không có incident hay maintenance -> metrics 0, risk score 0 (LOW), MTTR None."""
    asset = Asset(
        asset_code=f"INT-EMPTY-{uuid.uuid4().hex[:6].upper()}",
        name="Empty Clean Asset",
        category="Laptop",
        status=AssetStatus.IN_STOCK,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    metrics = AssetIntelligenceService.calculate_asset_metrics(db, asset)
    assert metrics.incident_count == 0
    assert metrics.maintenance_count == 0
    assert metrics.total_repair_cost == 0.0
    assert metrics.mttr_hours is None
    assert metrics.downtime_hours == 0.0
    assert metrics.has_repeated_failure is False

    health_risk = AssetIntelligenceService.calculate_risk_score(asset.status, metrics)
    assert health_risk.risk_score == 0.0
    assert health_risk.health_score == 100.0
    assert health_risk.risk_level == "LOW"
    assert len(health_risk.warning_reasons) == 0


def test_asset_intelligence_single_resolved_incident(db: Session, admin_user: User):
    """Test 2: Asset có 1 incident đã resolved -> MTTR được tính chính xác."""
    asset = Asset(
        asset_code=f"INT-RES-{uuid.uuid4().hex[:6].upper()}",
        name="Single Resolved Incident Asset",
        category="Monitor",
        status=AssetStatus.IN_STOCK,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    created = datetime.now(timezone.utc) - timedelta(hours=10)
    resolved = datetime.now(timezone.utc)

    inc = Incident(
        ticket_code=f"INC-RES-{uuid.uuid4().hex[:6].upper()}",
        asset_id=asset.id,
        reporter_id=admin_user.id,
        title="Lỗi IntelUnitTest Màn hình hiển thị",
        description="Kiểm tra IntelTest123",
        category=IncidentCategory.POWER,
        priority=IncidentPriority.MEDIUM,
        status=IncidentStatus.RESOLVED,
        created_at=created,
        resolved_at=resolved,
        repair_cost=100000.00,
    )
    db.add(inc)
    db.commit()

    metrics = AssetIntelligenceService.calculate_asset_metrics(db, asset)
    assert metrics.incident_count == 1
    assert metrics.total_repair_cost == 100000.00
    assert metrics.mttr_hours is not None
    assert 9.5 <= metrics.mttr_hours <= 10.5


def test_asset_intelligence_repeated_failure(db: Session, admin_user: User):
    """Test 3: Asset có 2 incidents cùng category HARDWARE trong 60 ngày -> Repeated Failure = True."""
    asset = Asset(
        asset_code=f"INT-REP-{uuid.uuid4().hex[:6].upper()}",
        name="Repeated Failure Asset",
        category="Laptop",
        status=AssetStatus.IN_STOCK,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    now = datetime.now(timezone.utc)
    inc1 = Incident(
        ticket_code=f"INC-R1-{uuid.uuid4().hex[:6].upper()}",
        asset_id=asset.id,
        reporter_id=admin_user.id,
        title="Hỏng ổ cứng Lượt 1",
        description="Bad sector",
        category=IncidentCategory.HARDWARE,
        priority=IncidentPriority.HIGH,
        status=IncidentStatus.RESOLVED,
        created_at=now - timedelta(days=20),
        resolved_at=now - timedelta(days=19),
    )
    inc2 = Incident(
        ticket_code=f"INC-R2-{uuid.uuid4().hex[:6].upper()}",
        asset_id=asset.id,
        reporter_id=admin_user.id,
        title="Hỏng RAM Lượt 2",
        description="Lỗi RAM",
        category=IncidentCategory.HARDWARE,
        priority=IncidentPriority.HIGH,
        status=IncidentStatus.RESOLVED,
        created_at=now - timedelta(days=5),
        resolved_at=now - timedelta(days=4),
    )
    db.add_all([inc1, inc2])
    db.commit()

    metrics = AssetIntelligenceService.calculate_asset_metrics(db, asset)
    assert metrics.incident_count == 2
    assert metrics.has_repeated_failure is True
    assert "HARDWARE" in metrics.repeated_categories

    health_risk = AssetIntelligenceService.calculate_risk_score(asset.status, metrics)
    assert health_risk.component_scores.repeat_score == 100.0


def test_asset_intelligence_status_damaged_and_in_maintenance(db: Session):
    """Test 4 & 5: Kiểm tra điểm số thành phần cho trạng thái DAMAGED và IN_MAINTENANCE."""
    asset_damaged = Asset(
        asset_code=f"INT-DAM-{uuid.uuid4().hex[:6].upper()}",
        name="Damaged Laptop",
        category="Laptop",
        status=AssetStatus.DAMAGED,
    )
    asset_maint = Asset(
        asset_code=f"INT-MNT-{uuid.uuid4().hex[:6].upper()}",
        name="Maintenance Laptop",
        category="Laptop",
        status=AssetStatus.IN_MAINTENANCE,
    )
    db.add_all([asset_damaged, asset_maint])
    db.commit()

    m_dam = AssetIntelligenceService.calculate_asset_metrics(db, asset_damaged)
    hr_dam = AssetIntelligenceService.calculate_risk_score(asset_damaged.status, m_dam)
    assert hr_dam.component_scores.status_score == 100.0

    m_mnt = AssetIntelligenceService.calculate_asset_metrics(db, asset_maint)
    hr_mnt = AssetIntelligenceService.calculate_risk_score(asset_maint.status, m_mnt)
    assert hr_mnt.component_scores.status_score == 60.0


def test_asset_intelligence_double_counting_cost_prevention(db: Session, admin_user: User):
    """Test 7: Quy tắc chống trùng lặp chi phí (Double counting repair cost).
    Incident cost = 100,000, Maintenance cost = 150,000 (linked to Incident).
    Total cost phải là 150,000 (KHÔNG phải 250,000).
    """
    asset = Asset(
        asset_code=f"INT-COST-{uuid.uuid4().hex[:6].upper()}",
        name="Cost Test Asset",
        category="Printer",
        status=AssetStatus.IN_STOCK,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    inc = Incident(
        ticket_code=f"INC-C-{uuid.uuid4().hex[:6].upper()}",
        asset_id=asset.id,
        reporter_id=admin_user.id,
        title="Hỏng sấy máy in",
        description="Kẹt giấy",
        category=IncidentCategory.HARDWARE,
        priority=IncidentPriority.HIGH,
        status=IncidentStatus.RESOLVED,
        repair_cost=100000.00,
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)

    mnt = Maintenance(
        maintenance_code=f"MNT-C-{uuid.uuid4().hex[:6].upper()}",
        asset_id=asset.id,
        incident_id=inc.id,
        status=MaintenanceStatus.COMPLETED,
        title="Thay bao sấy máy in",
        repair_cost=150000.00,
        completed_date=datetime.now(timezone.utc),
    )
    db.add(mnt)
    db.commit()

    metrics = AssetIntelligenceService.calculate_asset_metrics(db, asset)
    assert metrics.total_repair_cost == 150000.00


def test_asset_intelligence_downtime_active_and_completed(db: Session, admin_user: User):
    """Test 9 & 10: Downtime cho completed maintenance và active maintenance."""
    asset = Asset(
        asset_code=f"INT-DOWN-{uuid.uuid4().hex[:6].upper()}",
        name="Downtime Asset",
        category="Server",
        status=AssetStatus.IN_MAINTENANCE,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    now = datetime.now(timezone.utc)
    # Active maintenance started 5 hours ago
    mnt_active = Maintenance(
        maintenance_code=f"MNT-ACT-{uuid.uuid4().hex[:6].upper()}",
        asset_id=asset.id,
        status=MaintenanceStatus.IN_PROGRESS,
        title="Bảo trì máy chủ",
        start_date=now - timedelta(hours=5),
    )

    # Completed maintenance lasted 10 hours
    mnt_completed = Maintenance(
        maintenance_code=f"MNT-CMP-{uuid.uuid4().hex[:6].upper()}",
        asset_id=asset.id,
        status=MaintenanceStatus.COMPLETED,
        title="Nâng cấp nguồn",
        start_date=now - timedelta(days=2, hours=10),
        completed_date=now - timedelta(days=2),
    )

    db.add_all([mnt_active, mnt_completed])
    db.commit()

    metrics = AssetIntelligenceService.calculate_asset_metrics(db, asset)
    assert 14.5 <= metrics.downtime_hours <= 15.5


def test_asset_intelligence_risk_level_boundaries(db: Session):
    """Test 11, 12, 13, 14: Phân cấp Risk Level và Lý do Cảnh báo."""
    asset = Asset(
        asset_code=f"INT-HIGH-{uuid.uuid4().hex[:6].upper()}",
        name="High Risk Critical Asset",
        category="Laptop",
        status=AssetStatus.DAMAGED,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    # Add 4 incidents to push incident score to 100
    now = datetime.now(timezone.utc)
    for i in range(4):
        inc = Incident(
            ticket_code=f"INC-H{i}-{uuid.uuid4().hex[:6].upper()}",
            asset_id=asset.id,
            reporter_id=1,
            title=f"Lỗi phần cứng {i}",
            description="Hardware failure",
            category=IncidentCategory.HARDWARE,
            priority=IncidentPriority.CRITICAL,
            status=IncidentStatus.OPEN,
            created_at=now - timedelta(days=i * 2),
            repair_cost=1000000.00,
        )
        db.add(inc)
    db.commit()

    detail = AssetIntelligenceService.get_asset_intelligence_detail(db, asset.id)
    assert detail is not None
    assert detail.health_risk.risk_level in ("HIGH", "CRITICAL")
    assert len(detail.health_risk.warning_reasons) > 0


def test_intelligence_summary_and_top_endpoints(client: TestClient, admin_token: str):
    """Test 15 & 16: Endpoints /intelligence/summary, /top-failures, /top-costly."""
    res_summary = client.get(
        "/api/v1/intelligence/summary",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_summary.status_code == 200
    s_data = res_summary.json()
    assert "total_assets_analyzed" in s_data
    assert "risk_distribution" in s_data

    res_tf = client.get(
        "/api/v1/intelligence/top-failures",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_tf.status_code == 200
    assert isinstance(res_tf.json(), list)

    res_tc = client.get(
        "/api/v1/intelligence/top-costly",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_tc.status_code == 200
    assert isinstance(res_tc.json(), list)


def test_intelligence_rbac_restrictions(client: TestClient, employee_token: str, admin_token: str, db: Session, employee_user: User):
    """Test 17 & 18: Kiểm soát quyền RBAC với Employee và Admin."""
    # Employee accessing summary -> 403 Forbidden
    res_emp_summary = client.get(
        "/api/v1/intelligence/summary",
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert res_emp_summary.status_code == 403

    # Employee accessing risk-matrix -> 403 Forbidden
    res_emp_matrix = client.get(
        "/api/v1/intelligence/risk-matrix",
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert res_emp_matrix.status_code == 403

    # Asset assigned to employee
    asset_emp = Asset(
        asset_code=f"INT-EMP-{uuid.uuid4().hex[:6].upper()}",
        name="Employee Assigned Asset",
        category="Laptop",
        status=AssetStatus.ASSIGNED,
        current_user_id=employee_user.id,
    )
    # Unassigned asset
    asset_other = Asset(
        asset_code=f"INT-OTH-{uuid.uuid4().hex[:6].upper()}",
        name="Other Asset",
        category="Desktop PC",
        status=AssetStatus.IN_STOCK,
        current_user_id=None,
    )
    db.add_all([asset_emp, asset_other])
    db.commit()

    # Employee accesses their own assigned asset detail -> 200 OK
    res_own = client.get(
        f"/api/v1/intelligence/assets/{asset_emp.id}",
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert res_own.status_code == 200

    # Employee accesses another asset detail -> 403 Forbidden
    res_other = client.get(
        f"/api/v1/intelligence/assets/{asset_other.id}",
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert res_other.status_code == 403


def test_ai_assistant_intelligence_intents(db: Session, admin_user: User):
    """Test 19: AI Assistant nhận diện các intent Asset Intelligence read-only."""
    # Test top failure query
    res_tf = AIAssistantService.process_chat(db, admin_user, "Thiết bị nào hay hỏng nhất?")
    assert res_tf.intent == "TOP_FAILURE_ASSETS_QUERY"
    assert res_tf.is_fallback is True

    # Test top costly query
    res_tc = AIAssistantService.process_chat(db, admin_user, "Tài sản nào tốn nhiều tiền sửa nhất?")
    assert res_tc.intent == "HIGH_COST_ASSETS_QUERY"

    # Test risk query
    res_risk = AIAssistantService.process_chat(db, admin_user, "Tài sản nào có rủi ro cao?")
    assert res_risk.intent == "ASSET_RISK_QUERY"
