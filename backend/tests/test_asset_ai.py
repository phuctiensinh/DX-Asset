import json
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.models import Asset, Incident, Maintenance, User
from app.models.enums import AssetStatus, IncidentCategory, IncidentPriority, IncidentStatus, MaintenanceStatus, UserRole
from app.services import asset_ai
from app.services.asset_ai import COMPONENT_WEIGHTS, AssetAIService, build_context
from app.services.asset_intelligence import AssetIntelligenceService
from tests.test_incident_ai import OLLAMA_DOWN, _ollama_reply, mock_ollama

TODAY = date(2026, 10, 27)


def _token(user: User) -> dict:
    token = create_access_token(subject=user.id, extra_claims={"email": user.email, "role": str(user.role)})
    return {"Authorization": f"Bearer {token}"}


def _risky_asset(db: Session, reporter: User, current_user_id=None) -> Asset:
    """Damaged laptop with 3 recent hardware incidents and 3.000.000 VNĐ of repairs."""
    asset = Asset(
        asset_code=f"AI-RISK-{uuid.uuid4().hex[:6].upper()}",
        name="Laptop rủi ro",
        category="Laptop",
        status=AssetStatus.DAMAGED,
        current_user_id=current_user_id,
        warranty_expiry=TODAY + timedelta(days=100),
    )
    db.add(asset)
    db.commit()
    now = datetime.now(timezone.utc)
    for i in range(3):
        db.add(Incident(
            ticket_code=f"INC-AI-{uuid.uuid4().hex[:8].upper()}",
            asset_id=asset.id,
            reporter_id=reporter.id,
            title=f"Laptop không lên nguồn lần {i + 1}",
            description="Bấm nút nguồn không phản ứng",
            category=IncidentCategory.HARDWARE,
            priority=IncidentPriority.HIGH,
            status=IncidentStatus.OPEN,
            created_at=now - timedelta(days=i * 5),
        ))
    db.add(Maintenance(
        maintenance_code=f"MNT-AI-{uuid.uuid4().hex[:8].upper()}",
        asset_id=asset.id,
        title="Thay mainboard",
        status=MaintenanceStatus.COMPLETED,
        start_date=now - timedelta(days=10),
        completed_date=now - timedelta(days=9),
        repair_cost=Decimal("3000000"),
    ))
    db.commit()
    db.refresh(asset)
    return asset


def _db_snapshot(db: Session, asset: Asset) -> tuple:
    db.expire_all()
    a = db.query(Asset).filter(Asset.id == asset.id).one()
    return (
        a.status,
        a.updated_at,
        db.query(Incident).filter(Incident.asset_id == asset.id).count(),
        db.query(Maintenance).filter(Maintenance.asset_id == asset.id).count(),
    )


# --- Service: context, AI path, fallback ---

def test_component_weights_match_risk_score(db: Session, admin_user: User):
    """The weights used for 'largest contributor' must stay in sync with calculate_risk_score."""
    asset = _risky_asset(db, admin_user)
    detail = AssetIntelligenceService.get_asset_intelligence_detail(db, asset.id)
    scores = detail.health_risk.component_scores
    total = sum(getattr(scores, field) * weight for field, (_, weight) in COMPONENT_WEIGHTS.items())
    assert round(total, 1) == detail.health_risk.risk_score


def test_context_contains_intelligence_data_only(db: Session, admin_user: User):
    asset = _risky_asset(db, admin_user)
    detail = AssetIntelligenceService.get_asset_intelligence_detail(db, asset.id)
    incidents = asset_ai._recent_incidents(db, asset.id)
    context = build_context(detail, asset.warranty_expiry, incidents, TODAY)

    assert asset.asset_code in context
    assert f"Điểm rủi ro: {detail.health_risk.risk_score}/100" in context
    for reason in detail.health_risk.warning_reasons:
        assert reason in context
    assert "3.000.000 VNĐ" in context
    assert "Số sự cố: 3" in context
    assert "Còn bảo hành đến" in context
    assert "Laptop không lên nguồn lần 1" in context
    # No personal data or secrets in the prompt
    assert admin_user.email not in context
    assert settings.SECRET_KEY not in context
    assert "password" not in context.lower()


def test_explain_uses_ollama_answer(db: Session, admin_user: User):
    asset = _risky_asset(db, admin_user)
    detail = AssetIntelligenceService.get_asset_intelligence_detail(db, asset.id)
    reply = _ollama_reply(json.dumps({
        "explanation": f"Tài sản đang bị hỏng và có 3 sự cố. Điểm rủi ro {detail.health_risk.risk_score}/100.",
        "recommendations": ["Kiểm tra nguyên nhân gốc.", "Liên hệ bảo hành.", "Mục thừa sẽ bị cắt."],
    }))
    with mock_ollama(reply=reply):
        res = AssetAIService.explain_risk(db, asset, detail, today=TODAY)
    assert res.source == "AI"
    assert "3 sự cố" in res.explanation
    assert len(res.recommendations) == 2
    assert res.risk_score == detail.health_risk.risk_score
    assert res.risk_level == detail.health_risk.risk_level


def test_explain_rejects_invented_numbers(db: Session, admin_user: User):
    asset = _risky_asset(db, admin_user)
    detail = AssetIntelligenceService.get_asset_intelligence_detail(db, asset.id)
    reply = _ollama_reply(json.dumps({
        "explanation": "Pin đã chai 97531% nên tài sản rủi ro cao.",
        "recommendations": ["Thay pin."],
    }))
    with mock_ollama(reply=reply):
        res = AssetAIService.explain_risk(db, asset, detail, today=TODAY)
    assert res.source == "RULE_BASED"
    assert "97531" not in res.explanation  # long number: random asset codes may contain short digit runs


def test_explain_falls_back_on_bad_json(db: Session, admin_user: User):
    asset = _risky_asset(db, admin_user)
    detail = AssetIntelligenceService.get_asset_intelligence_detail(db, asset.id)
    with mock_ollama(reply=_ollama_reply("Không phải JSON")):
        res = AssetAIService.explain_risk(db, asset, detail, today=TODAY)
    assert res.source == "RULE_BASED"


def test_fallback_is_deterministic_and_grounded(db: Session, admin_user: User):
    asset = _risky_asset(db, admin_user)
    detail = AssetIntelligenceService.get_asset_intelligence_detail(db, asset.id)
    with mock_ollama(error=OLLAMA_DOWN):
        first = AssetAIService.explain_risk(db, asset, detail, today=TODAY)
        second = AssetAIService.explain_risk(db, asset, detail, today=TODAY)
    assert first == second
    assert first.source == "RULE_BASED"
    assert f"{detail.health_risk.risk_score}/100" in first.explanation
    assert "Rủi ro chủ yếu do" in first.explanation
    assert 1 <= len(first.recommendations) <= 2
    context = build_context(detail, asset.warranty_expiry, asset_ai._recent_incidents(db, asset.id), TODAY)
    assert asset_ai._numbers_grounded(" ".join([first.explanation, *first.recommendations]), context)


def test_fallback_low_risk_asset(db: Session):
    asset = Asset(asset_code=f"AI-LOW-{uuid.uuid4().hex[:6].upper()}", name="Màn hình mới", category="Monitor", status=AssetStatus.IN_STOCK)
    db.add(asset)
    db.commit()
    detail = AssetIntelligenceService.get_asset_intelligence_detail(db, asset.id)
    with mock_ollama(error=OLLAMA_DOWN):
        res = AssetAIService.explain_risk(db, asset, detail, today=TODAY)
    assert res.source == "RULE_BASED"
    assert "chưa ghi nhận dấu hiệu cảnh báo" in res.explanation
    assert "Không có dữ liệu bảo hành" in res.explanation
    assert res.recommendations == ["Tiếp tục theo dõi định kỳ, chưa cần hành động đặc biệt."]


# --- Endpoint: auth, RBAC, fallback, read-only ---

def test_endpoint_requires_authentication(client: TestClient, db: Session, admin_user: User):
    asset = _risky_asset(db, admin_user)
    res = client.post(f"/api/v1/intelligence/assets/{asset.id}/ai/explain")
    assert res.status_code == 401


def test_endpoint_not_found(client: TestClient, admin_token: str):
    res = client.post("/api/v1/intelligence/assets/999999999/ai/explain", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 404


def test_endpoint_rbac(client: TestClient, db: Session, admin_user: User, it_manager_user: User, employee_user: User):
    other_asset = _risky_asset(db, admin_user)
    own_asset = _risky_asset(db, admin_user, current_user_id=employee_user.id)
    manager = db.query(User).filter(User.role == UserRole.MANAGER, User.is_active == True).first()

    with mock_ollama(error=OLLAMA_DOWN):
        # Same rule as GET /intelligence/assets/{id}: analytics roles see every asset
        for user in [admin_user, it_manager_user] + ([manager] if manager else []):
            res = client.post(f"/api/v1/intelligence/assets/{other_asset.id}/ai/explain", headers=_token(user))
            assert res.status_code == 200, user.role
        # EMPLOYEE only for the asset currently assigned to them
        res = client.post(f"/api/v1/intelligence/assets/{other_asset.id}/ai/explain", headers=_token(employee_user))
        assert res.status_code == 403
        res = client.post(f"/api/v1/intelligence/assets/{own_asset.id}/ai/explain", headers=_token(employee_user))
        assert res.status_code == 200


def test_endpoint_ollama_success_schema_and_read_only(client: TestClient, db: Session, admin_user: User, admin_token: str):
    asset = _risky_asset(db, admin_user)
    before = _db_snapshot(db, asset)
    reply = _ollama_reply(json.dumps({
        "explanation": "Tài sản đang bị hỏng và đã có 3 sự cố.",
        "recommendations": ["Kiểm tra nguyên nhân gốc của lỗi phần cứng."],
    }))
    with mock_ollama(reply=reply):
        res = client.post(f"/api/v1/intelligence/assets/{asset.id}/ai/explain", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert set(data) == {"asset_id", "asset_code", "asset_name", "risk_score", "risk_level", "explanation", "recommendations", "source"}
    assert data["source"] == "AI"
    assert data["asset_id"] == asset.id
    assert _db_snapshot(db, asset) == before


def test_endpoint_falls_back_when_ollama_unavailable_or_slow(client: TestClient, db: Session, admin_user: User, admin_token: str):
    asset = _risky_asset(db, admin_user)
    headers = {"Authorization": f"Bearer {admin_token}"}
    for error in (OLLAMA_DOWN, httpx.ReadTimeout("timed out")):
        with mock_ollama(error=error):
            res = client.post(f"/api/v1/intelligence/assets/{asset.id}/ai/explain", headers=headers)
        assert res.status_code == 200
        assert res.json()["source"] == "RULE_BASED"
        assert res.json()["explanation"]


def test_endpoint_works_when_ollama_disabled(client: TestClient, db: Session, admin_user: User, admin_token: str, monkeypatch):
    asset = _risky_asset(db, admin_user)
    monkeypatch.setattr(settings, "OLLAMA_ENABLED", False)
    res = client.post(f"/api/v1/intelligence/assets/{asset.id}/ai/explain", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert res.json()["source"] == "RULE_BASED"
