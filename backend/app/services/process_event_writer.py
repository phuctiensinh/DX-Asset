from datetime import datetime, timezone
from typing import Any, Optional, Union

from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.models.enums import (
    IncidentStatus,
    MaintenanceStatus,
    ProcessCaseType,
    ProcessEventSource,
    ProcessEventTimestampQuality,
    ProcessEventType,
)
from app.models.incident import Incident
from app.models.maintenance import Maintenance
from app.models.process_case import ProcessCase
from app.models.process_event import ProcessEvent


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def get_or_create_incident_case(db: Session, incident: Union[Incident, int]) -> ProcessCase:
    incident_id = incident.id if isinstance(incident, Incident) else incident
    return _get_or_create_case(db, ProcessCaseType.INCIDENT, "incident_id", incident_id)


def get_or_create_maintenance_case(db: Session, maintenance: Union[Maintenance, int]) -> ProcessCase:
    maintenance_id = maintenance.id if isinstance(maintenance, Maintenance) else maintenance
    return _get_or_create_case(db, ProcessCaseType.MAINTENANCE, "maintenance_id", maintenance_id)


def _get_or_create_case(
    db: Session,
    case_type: ProcessCaseType,
    entity_field: str,
    entity_id: int,
) -> ProcessCase:
    if entity_id is None:
        raise ValueError(f"{entity_field} is required to create a process case")

    field = getattr(ProcessCase, entity_field)
    existing = db.query(ProcessCase).filter(field == entity_id).with_for_update().first()
    if existing:
        if _enum_value(existing.case_type) != case_type.value:
            raise ValueError("Existing process case has an incompatible case type")
        return existing

    values = {"case_type": case_type.value, entity_field: entity_id}
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        insert_statement = pg_insert(ProcessCase).values(**values)
    elif dialect == "sqlite":
        insert_statement = sqlite_insert(ProcessCase).values(**values)
    else:
        raise RuntimeError(f"Unsupported database dialect for race-safe case creation: {dialect}")

    # A targeted conflict action makes concurrent get-or-create safe without a
    # savepoint or rolling back the caller's business transaction.
    db.execute(insert_statement.on_conflict_do_nothing(index_elements=[field]))
    existing = db.query(ProcessCase).filter(field == entity_id).with_for_update().first()
    if existing is None:
        raise RuntimeError("Process case insert did not produce a row")
    if _enum_value(existing.case_type) != case_type.value:
        raise ValueError("Existing process case has an incompatible case type")
    return existing


def create_process_event(
    db: Session,
    *,
    case: Union[ProcessCase, int],
    event_type: ProcessEventType,
    occurred_at: Optional[datetime] = None,
    from_status: Optional[Any] = None,
    to_status: Optional[Any] = None,
    maintenance_id: Optional[int] = None,
    performed_by_id: Optional[int] = None,
    target_user_id: Optional[int] = None,
    source: ProcessEventSource = ProcessEventSource.LIVE,
    timestamp_quality: ProcessEventTimestampQuality = ProcessEventTimestampQuality.ACTION_TIME,
    source_event_key: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> ProcessEvent:
    """Add one validated event to the caller's transaction; this function never commits."""
    case_id = case.id if isinstance(case, ProcessCase) else case
    locked_case = db.query(ProcessCase).filter(ProcessCase.id == case_id).with_for_update().first()
    if locked_case is None:
        raise ValueError("Process case does not exist")

    event_type = ProcessEventType(_enum_value(event_type))
    source = ProcessEventSource(_enum_value(source))
    timestamp_quality = ProcessEventTimestampQuality(_enum_value(timestamp_quality))
    from_value = _enum_value(from_status)
    to_value = _enum_value(to_status)
    case_type = _enum_value(locked_case.case_type)

    incident_statuses = {status.value for status in IncidentStatus}
    maintenance_statuses = {status.value for status in MaintenanceStatus}

    if event_type == ProcessEventType.INCIDENT_CREATED:
        if case_type != ProcessCaseType.INCIDENT.value:
            raise ValueError("INCIDENT_CREATED requires an Incident case")
        if from_value is not None or to_value not in incident_statuses:
            raise ValueError("INCIDENT_CREATED requires a valid to_status and no from_status")
    elif event_type == ProcessEventType.INCIDENT_STATUS_CHANGED:
        if case_type != ProcessCaseType.INCIDENT.value:
            raise ValueError("INCIDENT_STATUS_CHANGED requires an Incident case")
        _validate_status_pair(from_value, to_value, incident_statuses, "Incident")
    elif event_type == ProcessEventType.TECHNICIAN_ASSIGNED:
        if case_type != ProcessCaseType.INCIDENT.value:
            raise ValueError("TECHNICIAN_ASSIGNED requires an Incident case")
        if target_user_id is None:
            raise ValueError("TECHNICIAN_ASSIGNED requires target_user_id")
        _require_no_statuses(from_value, to_value)
    elif event_type in (ProcessEventType.MAINTENANCE_CREATED, ProcessEventType.MAINTENANCE_STATUS_CHANGED):
        if maintenance_id is None:
            if case_type == ProcessCaseType.MAINTENANCE.value:
                maintenance_id = locked_case.maintenance_id
            else:
                raise ValueError(f"{event_type.value} requires maintenance_id")
        maintenance = db.query(Maintenance).filter(Maintenance.id == maintenance_id).first()
        if maintenance is None:
            raise ValueError("Maintenance does not exist")
        if case_type == ProcessCaseType.MAINTENANCE.value:
            if locked_case.maintenance_id != maintenance.id:
                raise ValueError("Maintenance does not belong to this Maintenance case")
        elif case_type == ProcessCaseType.INCIDENT.value:
            if maintenance.incident_id != locked_case.incident_id:
                raise ValueError("Maintenance is not linked to this Incident case")
        else:
            raise ValueError("Unsupported process case type")

        if event_type == ProcessEventType.MAINTENANCE_CREATED:
            _require_no_statuses(from_value, to_value)
        else:
            _validate_status_pair(from_value, to_value, maintenance_statuses, "Maintenance")
    else:  # Defensive if the enum expands in a later phase.
        raise ValueError(f"Unsupported process event type: {event_type}")

    if occurred_at is None:
        occurred_at = datetime.now(timezone.utc)
    if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
        raise ValueError("occurred_at must be timezone-aware")
    occurred_at = occurred_at.astimezone(timezone.utc)

    max_sequence = db.query(func.max(ProcessEvent.case_sequence)).filter(
        ProcessEvent.case_id == case_id
    ).scalar()
    next_sequence = (max_sequence or 0) + 1
    if source == ProcessEventSource.LIVE and source_event_key is None:
        # The sequence is allocated while holding the case row lock, so this key
        # is stable for retries after rollback and distinct for later loops.
        source_event_key = f"process-case:{case_id}:sequence:{next_sequence}"
    event = ProcessEvent(
        case_id=case_id,
        maintenance_id=maintenance_id,
        event_type=event_type.value,
        from_status=from_value,
        to_status=to_value,
        performed_by_id=performed_by_id,
        target_user_id=target_user_id,
        occurred_at=occurred_at,
        case_sequence=next_sequence,
        source=source.value,
        timestamp_quality=timestamp_quality.value,
        source_event_key=source_event_key,
        event_metadata=metadata,
    )
    db.add(event)
    db.flush()
    return event


def _require_no_statuses(from_status: Optional[str], to_status: Optional[str]) -> None:
    if from_status is not None or to_status is not None:
        raise ValueError("from_status and to_status are only valid for status-change events")


def _validate_status_pair(
    from_status: Optional[str],
    to_status: Optional[str],
    allowed_statuses: set[str],
    entity_name: str,
) -> None:
    if from_status is None or to_status is None:
        raise ValueError(f"{entity_name} status-change events require from_status and to_status")
    if from_status not in allowed_statuses or to_status not in allowed_statuses:
        raise ValueError(f"Invalid {entity_name} status value")
