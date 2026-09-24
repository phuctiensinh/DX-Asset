from collections import Counter
from datetime import datetime, timedelta, timezone
import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.assignment import AssetAssignment
from app.models.enums import (
    AssetStatus,
    IncidentCategory,
    IncidentPriority,
    IncidentStatus,
    MaintenanceStatus,
    ProcessCaseType,
    ProcessEventSource,
    ProcessEventTimestampQuality,
    ProcessEventType,
    UserRole,
)
from app.models.incident import Incident
from app.models.history import AssetHistory
from app.models.maintenance import Maintenance
from app.models.process_case import ProcessCase
from app.models.process_event import ProcessEvent
from app.models.technician_skill import TechnicianSkill
from app.models.user import User
from app.services.process_event_backfill import backfill_process_events
from app.services.process_event_writer import create_process_event, get_or_create_incident_case


def _make_asset(db: Session, suffix: str) -> Asset:
    asset = Asset(
        asset_code=f"P15C-{suffix}-{uuid.uuid4().hex[:8].upper()}",
        name=f"Phase 15C {suffix} asset",
        category="Laptop",
        status=AssetStatus.IN_STOCK,
    )
    db.add(asset)
    db.flush()
    return asset


def test_backfill_cases_events_provenance_and_idempotency(db: Session, admin_user: User):
    base = datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)
    asset = _make_asset(db, "LINKED")
    incident = Incident(
        ticket_code=f"P15C-INC-{uuid.uuid4().hex[:8].upper()}",
        asset_id=asset.id,
        reporter_id=admin_user.id,
        assigned_it_id=admin_user.id,
        title="Legacy resolved incident",
        description="Snapshot has no structured status or assignment history",
        category=IncidentCategory.HARDWARE,
        priority=IncidentPriority.MEDIUM,
        status=IncidentStatus.RESOLVED,
        created_at=base,
        resolved_at=base + timedelta(days=2),
    )
    db.add(incident)
    db.flush()
    linked = Maintenance(
        maintenance_code=f"P15C-LINK-{uuid.uuid4().hex[:8].upper()}",
        asset_id=asset.id,
        incident_id=incident.id,
        technician_id=admin_user.id,
        title="Legacy linked maintenance",
        status=MaintenanceStatus.COMPLETED,
        created_at=base + timedelta(minutes=1),
        start_date=base + timedelta(minutes=5),
        # Equal source timestamps still use the deterministic start-before-end tie-break.
        completed_date=base + timedelta(minutes=5),
    )
    independent = Maintenance(
        maintenance_code=f"P15C-IND-{uuid.uuid4().hex[:8].upper()}",
        asset_id=asset.id,
        title="Legacy completed without reliable start",
        status=MaintenanceStatus.COMPLETED,
        created_at=base + timedelta(minutes=2),
        # The complete endpoint writes created_at here as a fallback; this is
        # not proof that a start action occurred.
        start_date=base + timedelta(minutes=2),
        completed_date=base + timedelta(minutes=30),
    )
    db.add_all([linked, independent])
    db.commit()

    business_tables = (
        Asset,
        AssetAssignment,
        Incident,
        Maintenance,
        User,
        TechnicianSkill,
        AssetHistory,
    )
    business_before = {
        model.__tablename__: db.query(model).count() for model in business_tables
    }
    target_snapshot = (
        incident.status,
        incident.assigned_it_id,
        linked.status,
        linked.start_date,
        linked.completed_date,
        independent.status,
        independent.start_date,
        independent.completed_date,
    )

    first = backfill_process_events(db)
    db.commit()

    incident_case = db.query(ProcessCase).filter(ProcessCase.incident_id == incident.id).one()
    assert incident_case.case_type == ProcessCaseType.INCIDENT
    assert db.query(ProcessCase).filter(ProcessCase.maintenance_id == linked.id).count() == 0
    independent_case = db.query(ProcessCase).filter(ProcessCase.maintenance_id == independent.id).one()
    assert independent_case.case_type == ProcessCaseType.MAINTENANCE

    incident_event = db.query(ProcessEvent).filter(
        ProcessEvent.case_id == incident_case.id,
        ProcessEvent.event_type == ProcessEventType.INCIDENT_CREATED,
    ).one()
    assert incident_event.from_status is None
    assert incident_event.to_status == IncidentStatus.RESOLVED.value
    assert incident_event.performed_by_id is None
    assert incident_event.target_user_id is None
    assert incident_event.occurred_at.replace(tzinfo=timezone.utc) == base
    assert incident_event.source == ProcessEventSource.BACKFILL
    assert incident_event.timestamp_quality == ProcessEventTimestampQuality.LEGACY_FIELD
    assert incident_event.source_event_key == f"legacy:incident:{incident.id}:created"
    assert incident_event.event_metadata == {
        "backfill_reason": "legacy_incident_created_at",
        "source_record": "incidents",
        "source_id": incident.id,
        "status_source": "current_incident_snapshot",
    }

    linked_events = db.query(ProcessEvent).filter(
        ProcessEvent.case_id == incident_case.id
    ).order_by(ProcessEvent.case_sequence).all()
    assert [(event.event_type, event.from_status, event.to_status) for event in linked_events] == [
        (ProcessEventType.INCIDENT_CREATED.value, None, IncidentStatus.RESOLVED.value),
        (ProcessEventType.MAINTENANCE_CREATED.value, None, None),
        (ProcessEventType.MAINTENANCE_STATUS_CHANGED.value, MaintenanceStatus.SCHEDULED.value, MaintenanceStatus.IN_PROGRESS.value),
        (ProcessEventType.MAINTENANCE_STATUS_CHANGED.value, MaintenanceStatus.IN_PROGRESS.value, MaintenanceStatus.COMPLETED.value),
    ]
    assert [event.case_sequence for event in linked_events] == [1, 2, 3, 4]
    assert [event.occurred_at for event in linked_events] == sorted(event.occurred_at for event in linked_events)
    assert all(event.source == ProcessEventSource.BACKFILL for event in linked_events)
    assert linked_events[2].timestamp_quality == ProcessEventTimestampQuality.ACTION_TIME
    assert linked_events[3].timestamp_quality == ProcessEventTimestampQuality.ACTION_TIME
    assert linked_events[2].source_event_key == f"legacy:maintenance:{linked.id}:started"
    assert linked_events[3].source_event_key == f"legacy:maintenance:{linked.id}:completed"

    independent_events = db.query(ProcessEvent).filter(
        ProcessEvent.case_id == independent_case.id
    ).all()
    assert len(independent_events) == 1
    assert independent_events[0].event_type == ProcessEventType.MAINTENANCE_CREATED
    assert independent_events[0].source_event_key == f"legacy:maintenance:{independent.id}:created"
    assert independent_events[0].to_status is None

    # Snapshot status and assigned technician do not establish transition history.
    assert db.query(ProcessEvent).filter(
        ProcessEvent.case_id == incident_case.id,
        ProcessEvent.event_type.in_([
            ProcessEventType.INCIDENT_STATUS_CHANGED,
            ProcessEventType.TECHNICIAN_ASSIGNED,
        ]),
    ).count() == 0
    assert first["incident_status_transitions_skipped"] >= 1
    assert first["technician_assignments_skipped"] >= 1
    assert first["maintenance_completions_skipped"] >= 1

    assert {
        model.__tablename__: db.query(model).count() for model in business_tables
    } == business_before
    assert target_snapshot == (
        incident.status,
        incident.assigned_it_id,
        linked.status,
        linked.start_date,
        linked.completed_date,
        independent.status,
        independent.start_date,
        independent.completed_date,
    )

    case_count = db.query(ProcessCase).count()
    event_count = db.query(ProcessEvent).count()
    second = backfill_process_events(db)
    db.commit()
    assert db.query(ProcessCase).count() == case_count
    assert db.query(ProcessEvent).count() == event_count
    assert Counter(second["events_created"]) == Counter()


def test_backfill_rolls_back_process_rows_when_event_write_fails(
    db: Session, monkeypatch: pytest.MonkeyPatch
):
    from app.services import process_event_backfill as backfill_service

    admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
    assert admin is not None
    asset = _make_asset(db, "ROLLBACK")
    incident = Incident(
        ticket_code=f"P15C-RB-{uuid.uuid4().hex[:8].upper()}",
        asset_id=asset.id,
        reporter_id=admin.id,
        title="Backfill rollback case",
        description="Force an event write failure",
        category=IncidentCategory.HARDWARE,
        priority=IncidentPriority.LOW,
        status=IncidentStatus.OPEN,
        created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
    )
    db.add(incident)
    db.commit()
    cases_before = db.query(ProcessCase).count()
    events_before = db.query(ProcessEvent).count()

    def fail_writer(*_args, **_kwargs):
        raise IntegrityError("forced backfill failure", {}, RuntimeError("test"))

    monkeypatch.setattr(backfill_service, "create_process_event", fail_writer)
    with pytest.raises(IntegrityError, match="forced backfill failure"):
        backfill_process_events(db)

    db.expire_all()
    assert db.query(ProcessCase).count() == cases_before
    assert db.query(ProcessEvent).count() == events_before
    assert db.query(ProcessCase).filter(ProcessCase.incident_id == incident.id).count() == 0


def test_backfill_does_not_duplicate_existing_live_creation_event(db: Session, admin_user: User):
    asset = _make_asset(db, "LIVE")
    incident = Incident(
        ticket_code=f"P15C-LIVE-{uuid.uuid4().hex[:8].upper()}",
        asset_id=asset.id,
        reporter_id=admin_user.id,
        title="Post-Phase 15B incident",
        description="Already has its live creation event",
        category=IncidentCategory.HARDWARE,
        priority=IncidentPriority.LOW,
        status=IncidentStatus.RESOLVED,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    db.add(incident)
    db.flush()
    case = get_or_create_incident_case(db, incident)
    live_event = create_process_event(
        db,
        case=case,
        event_type=ProcessEventType.INCIDENT_CREATED,
        to_status=IncidentStatus.OPEN,
        occurred_at=incident.created_at,
        performed_by_id=admin_user.id,
        source=ProcessEventSource.LIVE,
        timestamp_quality=ProcessEventTimestampQuality.ACTION_TIME,
        source_event_key=f"incident:{incident.id}:created",
    )
    db.commit()

    backfill_process_events(db)
    db.commit()

    events = db.query(ProcessEvent).filter(ProcessEvent.case_id == case.id).all()
    assert len(events) == 1
    assert events[0].id == live_event.id
    assert events[0].source == ProcessEventSource.LIVE
    assert db.query(ProcessEvent).filter(
        ProcessEvent.source_event_key == f"legacy:incident:{incident.id}:created"
    ).count() == 0
