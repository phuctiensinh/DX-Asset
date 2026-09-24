import uuid

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.enums import AssetStatus, ProcessEventType
from app.models.process_case import ProcessCase
from app.models.process_event import ProcessEvent
from app.models.user import User


def _raise_integrity_error(*_args, **_kwargs):
    raise IntegrityError("forced process-event failure", {}, RuntimeError("test failure"))


def test_incident_and_case_rollback_when_process_event_write_fails(
    client: TestClient,
    admin_token: str,
    db: Session,
    admin_user: User,
    monkeypatch,
):
    import app.api.v1.incidents as incidents_api

    asset = Asset(
        asset_code=f"ATOMIC-INC-ASSET-{uuid.uuid4().hex[:6].upper()}",
        name="Atomic incident test asset",
        category="Laptop",
        status=AssetStatus.IN_STOCK,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    ticket_code = f"ATOMIC-INC-{uuid.uuid4().hex[:8].upper()}"
    cases_before = db.query(ProcessCase).count()
    events_before = db.query(ProcessEvent).count()
    monkeypatch.setattr(incidents_api, "create_process_event", _raise_integrity_error)

    response = client.post(
        "/api/v1/incidents",
        json={
            "asset_id": asset.id,
            "ticket_code": ticket_code,
            "title": "Atomic rollback test",
            "description": "The event writer is forced to fail",
            "category": "HARDWARE",
            "priority": "LOW",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409
    assert db.query(ProcessCase).count() == cases_before
    assert db.query(ProcessEvent).count() == events_before
    from app.models.incident import Incident
    assert db.query(Incident).filter(Incident.ticket_code == ticket_code).count() == 0


def test_maintenance_and_case_rollback_when_process_event_write_fails(
    client: TestClient,
    admin_token: str,
    db: Session,
    monkeypatch,
):
    import app.api.v1.maintenances as maintenances_api
    from app.models.maintenance import Maintenance

    asset = Asset(
        asset_code=f"ATOMIC-MNT-ASSET-{uuid.uuid4().hex[:6].upper()}",
        name="Atomic maintenance test asset",
        category="Monitor",
        status=AssetStatus.IN_STOCK,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    maintenance_code = f"ATOMIC-MNT-{uuid.uuid4().hex[:8].upper()}"
    cases_before = db.query(ProcessCase).count()
    events_before = db.query(ProcessEvent).count()
    monkeypatch.setattr(maintenances_api, "create_process_event", _raise_integrity_error)

    response = client.post(
        "/api/v1/maintenances",
        json={
            "asset_id": asset.id,
            "maintenance_code": maintenance_code,
            "title": "Atomic maintenance rollback test",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409
    assert db.query(Maintenance).filter(Maintenance.maintenance_code == maintenance_code).count() == 0
    assert db.query(ProcessCase).count() == cases_before
    assert db.query(ProcessEvent).count() == events_before
