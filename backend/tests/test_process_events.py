from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models import (
    Asset,
    AssetStatus,
    Department,
    Incident,
    IncidentCategory,
    IncidentPriority,
    IncidentStatus,
    Maintenance,
    MaintenanceStatus,
    ProcessCase,
    ProcessCaseType,
    ProcessEvent,
    ProcessEventSource,
    ProcessEventTimestampQuality,
    ProcessEventType,
    User,
    UserRole,
)
from app.services.process_event_writer import (
    create_process_event,
    get_or_create_incident_case,
    get_or_create_maintenance_case,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()

    department = Department(code="PROC", name="Process Test")
    session.add(department)
    session.flush()
    actor = User(
        email="process-test@example.invalid",
        password_hash="not-a-real-password-hash",
        full_name="Process Test User",
        role=UserRole.ADMIN,
    )
    session.add(actor)
    session.flush()
    asset = Asset(
        asset_code="PROC-ASSET",
        name="Process test asset",
        category="Test",
        status=AssetStatus.IN_STOCK,
    )
    session.add(asset)
    session.flush()
    incident = Incident(
        ticket_code="PROC-INCIDENT",
        asset_id=asset.id,
        reporter_id=actor.id,
        title="Test incident",
        description="Process event writer test",
        category=IncidentCategory.HARDWARE,
        priority=IncidentPriority.LOW,
        status=IncidentStatus.OPEN,
    )
    session.add(incident)
    session.flush()
    maintenance = Maintenance(
        maintenance_code="PROC-MAINTENANCE",
        asset_id=asset.id,
        incident_id=incident.id,
        technician_id=actor.id,
        title="Test maintenance",
        status=MaintenanceStatus.SCHEDULED,
    )
    standalone_maintenance = Maintenance(
        maintenance_code="PROC-STANDALONE",
        asset_id=asset.id,
        incident_id=None,
        technician_id=actor.id,
        title="Standalone test maintenance",
        status=MaintenanceStatus.SCHEDULED,
    )
    session.add_all([maintenance, standalone_maintenance])
    session.commit()

    session.info.update(
        actor_id=actor.id,
        incident_id=incident.id,
        maintenance_id=maintenance.id,
        standalone_maintenance_id=standalone_maintenance.id,
    )
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_get_or_create_incident_and_maintenance_cases_are_idempotent(db: Session):
    incident = db.get(Incident, db.info["incident_id"])
    maintenance = db.get(Maintenance, db.info["standalone_maintenance_id"])

    incident_case = get_or_create_incident_case(db, incident)
    maintenance_case = get_or_create_maintenance_case(db, maintenance)
    db.flush()

    assert get_or_create_incident_case(db, incident).id == incident_case.id
    assert get_or_create_maintenance_case(db, maintenance.id).id == maintenance_case.id
    assert incident_case.case_type == ProcessCaseType.INCIDENT
    assert incident_case.incident_id == incident.id and incident_case.maintenance_id is None
    assert maintenance_case.case_type == ProcessCaseType.MAINTENANCE
    assert maintenance_case.maintenance_id == maintenance.id and maintenance_case.incident_id is None


@pytest.mark.parametrize(
    "incident_id,maintenance_id",
    [(None, None), (1, 1)],
)
def test_process_case_requires_exactly_one_entity(db: Session, incident_id, maintenance_id):
    case = ProcessCase(
        case_type=ProcessCaseType.INCIDENT,
        incident_id=incident_id,
        maintenance_id=maintenance_id,
    )
    db.add(case)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_process_case_entity_uniqueness(db: Session):
    incident_id = db.info["incident_id"]
    db.add(ProcessCase(case_type=ProcessCaseType.INCIDENT, incident_id=incident_id))
    db.flush()
    db.add(ProcessCase(case_type=ProcessCaseType.INCIDENT, incident_id=incident_id))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_process_event_fk_constraints_and_nullable_actors(db: Session):
    case = get_or_create_incident_case(db, db.info["incident_id"])
    db.flush()
    event_row = create_process_event(
        db,
        case=case,
        event_type=ProcessEventType.INCIDENT_CREATED,
        to_status=IncidentStatus.OPEN,
        performed_by_id=None,
        target_user_id=None,
    )
    assert event_row.performed_by_id is None
    assert event_row.target_user_id is None

    bad_case_event = ProcessEvent(
        case_id=99999,
        event_type=ProcessEventType.INCIDENT_CREATED.value,
        to_status=IncidentStatus.OPEN.value,
        occurred_at=datetime.now(timezone.utc),
        case_sequence=1,
        source=ProcessEventSource.LIVE.value,
        timestamp_quality=ProcessEventTimestampQuality.ACTION_TIME.value,
    )
    db.add(bad_case_event)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_process_event_maintenance_fk_is_enforced(db: Session):
    case = get_or_create_incident_case(db, db.info["incident_id"])
    db.flush()
    bad_maintenance_event = ProcessEvent(
        case_id=case.id,
        maintenance_id=99999,
        event_type=ProcessEventType.MAINTENANCE_STATUS_CHANGED.value,
        from_status=MaintenanceStatus.SCHEDULED.value,
        to_status=MaintenanceStatus.IN_PROGRESS.value,
        occurred_at=datetime.now(timezone.utc),
        case_sequence=1,
        source=ProcessEventSource.LIVE.value,
        timestamp_quality=ProcessEventTimestampQuality.ACTION_TIME.value,
    )
    db.add(bad_maintenance_event)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_event_writer_validates_event_case_and_status_fields(db: Session):
    incident_case = get_or_create_incident_case(db, db.info["incident_id"])
    maintenance_case = get_or_create_maintenance_case(db, db.info["standalone_maintenance_id"])
    db.flush()

    with pytest.raises(ValueError, match="Incident case"):
        create_process_event(db, case=maintenance_case, event_type=ProcessEventType.INCIDENT_CREATED)
    with pytest.raises(ValueError, match="require from_status"):
        create_process_event(db, case=incident_case, event_type=ProcessEventType.INCIDENT_STATUS_CHANGED)
    with pytest.raises(ValueError, match="Invalid Incident status"):
        create_process_event(
            db,
            case=incident_case,
            event_type=ProcessEventType.INCIDENT_STATUS_CHANGED,
            from_status="NOT_A_STATUS",
            to_status=IncidentStatus.RESOLVED,
        )
    with pytest.raises(ValueError, match="target_user_id"):
        create_process_event(db, case=incident_case, event_type=ProcessEventType.TECHNICIAN_ASSIGNED)
    with pytest.raises(ValueError, match="requires maintenance_id"):
        create_process_event(db, case=incident_case, event_type=ProcessEventType.MAINTENANCE_CREATED)


def test_linked_maintenance_event_requires_correct_incident_case(db: Session):
    case = get_or_create_incident_case(db, db.info["incident_id"])
    db.flush()
    row = create_process_event(
        db,
        case=case,
        event_type=ProcessEventType.MAINTENANCE_STATUS_CHANGED,
        maintenance_id=db.info["maintenance_id"],
        from_status=MaintenanceStatus.SCHEDULED,
        to_status=MaintenanceStatus.IN_PROGRESS,
    )
    assert row.maintenance_id == db.info["maintenance_id"]

    with pytest.raises(ValueError, match="not linked"):
        create_process_event(
            db,
            case=case,
            event_type=ProcessEventType.MAINTENANCE_CREATED,
            maintenance_id=db.info["standalone_maintenance_id"],
        )


def test_event_sequence_is_unique_and_increments_for_equal_timestamps(db: Session):
    case = get_or_create_incident_case(db, db.info["incident_id"])
    timestamp = datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc)
    first = create_process_event(
        db, case=case, event_type=ProcessEventType.INCIDENT_CREATED,
        to_status=IncidentStatus.OPEN, occurred_at=timestamp,
    )
    second = create_process_event(
        db,
        case=case,
        event_type=ProcessEventType.INCIDENT_STATUS_CHANGED,
        from_status=IncidentStatus.OPEN,
        to_status=IncidentStatus.IN_REVIEW,
        occurred_at=timestamp,
    )
    assert first.case_sequence == 1
    assert second.case_sequence == 2
    assert first.occurred_at == second.occurred_at

    duplicate_sequence = ProcessEvent(
        case_id=case.id,
        event_type=ProcessEventType.INCIDENT_CREATED.value,
        to_status=IncidentStatus.OPEN.value,
        occurred_at=timestamp,
        case_sequence=1,
        source=ProcessEventSource.LIVE.value,
        timestamp_quality=ProcessEventTimestampQuality.ACTION_TIME.value,
    )
    db.add(duplicate_sequence)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_writer_stays_in_callers_transaction_and_event_rolls_back(db: Session):
    case = get_or_create_incident_case(db, db.info["incident_id"])
    event_row = create_process_event(
        db, case=case, event_type=ProcessEventType.INCIDENT_CREATED, to_status=IncidentStatus.OPEN
    )
    event_id = event_row.id

    assert db.in_transaction()
    assert db.query(ProcessEvent).filter(ProcessEvent.id == event_id).one()
    db.rollback()
    assert db.query(ProcessEvent).filter(ProcessEvent.id == event_id).count() == 0
    assert db.query(ProcessCase).filter(ProcessCase.incident_id == db.info["incident_id"]).count() == 0


def test_event_failure_can_rollback_business_change_in_same_transaction(db: Session):
    incident = db.get(Incident, db.info["incident_id"])
    incident.title = "Uncommitted title"
    case = get_or_create_incident_case(db, incident.id)
    create_process_event(
        db,
        case=case,
        event_type=ProcessEventType.INCIDENT_CREATED,
        to_status=IncidentStatus.OPEN,
        source_event_key="stable-key",
    )
    db.commit()

    incident.title = "Must roll back"
    with pytest.raises(IntegrityError):
        create_process_event(
            db,
            case=case,
            event_type=ProcessEventType.INCIDENT_CREATED,
            to_status=IncidentStatus.OPEN,
            source_event_key="stable-key",
        )
    db.rollback()
    db.expire_all()
    assert db.get(Incident, incident.id).title == "Uncommitted title"
    assert db.query(ProcessEvent).filter(ProcessEvent.source_event_key == "stable-key").count() == 1


def test_source_quality_and_source_key_constraints(db: Session):
    case = get_or_create_incident_case(db, db.info["incident_id"])
    event_row = create_process_event(
        db,
        case=case,
        event_type=ProcessEventType.INCIDENT_CREATED,
        to_status=IncidentStatus.OPEN,
        source=ProcessEventSource.BACKFILL,
        timestamp_quality=ProcessEventTimestampQuality.LEGACY_FIELD,
        source_event_key="backfill:incident:created:1",
        metadata={"migration": "004"},
    )
    assert event_row.source == ProcessEventSource.BACKFILL
    assert event_row.timestamp_quality == ProcessEventTimestampQuality.LEGACY_FIELD
    assert event_row.event_metadata == {"migration": "004"}

    duplicate_key = ProcessEvent(
        case_id=case.id,
        event_type=ProcessEventType.INCIDENT_CREATED.value,
        to_status=IncidentStatus.OPEN.value,
        occurred_at=datetime.now(timezone.utc),
        case_sequence=2,
        source=ProcessEventSource.BACKFILL.value,
        timestamp_quality=ProcessEventTimestampQuality.LEGACY_FIELD.value,
        source_event_key="backfill:incident:created:1",
    )
    db.add(duplicate_key)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_deleted_target_user_is_set_null_on_assignment_event(db: Session):
    case = get_or_create_incident_case(db, db.info["incident_id"])
    target = User(
        email="assigned-technician@example.invalid",
        password_hash="not-a-real-password-hash",
        full_name="Assigned Technician",
        role=UserRole.IT_ASSET_MANAGER,
    )
    db.add(target)
    db.flush()
    event_row = create_process_event(
        db,
        case=case,
        event_type=ProcessEventType.TECHNICIAN_ASSIGNED,
        target_user_id=target.id,
    )
    db.flush()
    event_id = event_row.id

    db.delete(target)
    db.flush()
    db.expire_all()
    assert db.get(ProcessEvent, event_id).target_user_id is None
