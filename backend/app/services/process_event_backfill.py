"""Conservative, repeatable backfill of structured process events."""

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import update
from sqlalchemy.orm import Session

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
from app.services.process_event_writer import (
    create_process_event,
    get_or_create_incident_case,
    get_or_create_maintenance_case,
)


def _enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _utc_sort_value(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _as_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _case_event_exists(
    db: Session,
    *,
    case_id: int,
    event_type: ProcessEventType,
    maintenance_id: int | None = None,
    from_status: str | None = None,
    to_status: str | None = None,
    occurred_at: datetime | None = None,
) -> bool:
    query = db.query(ProcessEvent.id).filter(
        ProcessEvent.case_id == case_id,
        ProcessEvent.event_type == event_type.value,
    )
    if maintenance_id is not None:
        query = query.filter(ProcessEvent.maintenance_id == maintenance_id)
    if from_status is not None or to_status is not None:
        query = query.filter(
            ProcessEvent.from_status == from_status,
            ProcessEvent.to_status == to_status,
        )
    if occurred_at is not None:
        query = query.filter(ProcessEvent.occurred_at == occurred_at)
    return query.first() is not None


def _record_event(
    db: Session,
    created: Counter[str],
    *,
    case: ProcessCase,
    event_type: ProcessEventType,
    occurred_at: datetime,
    source_event_key: str,
    metadata: dict[str, Any],
    from_status: Any = None,
    to_status: Any = None,
    maintenance_id: int | None = None,
) -> bool:
    existing_by_key = db.query(ProcessEvent).filter(
        ProcessEvent.source_event_key == source_event_key
    ).first()
    if existing_by_key is not None:
        if (
            existing_by_key.case_id != case.id
            or _enum_value(existing_by_key.event_type) != event_type.value
            or existing_by_key.maintenance_id != maintenance_id
        ):
            raise ValueError(f"Backfill key {source_event_key!r} already belongs to a different event")
        return False

    if event_type in (ProcessEventType.INCIDENT_CREATED, ProcessEventType.MAINTENANCE_CREATED):
        existing_creation = db.query(ProcessEvent.id).filter(
            ProcessEvent.case_id == case.id,
            ProcessEvent.event_type == event_type.value,
        )
        if maintenance_id is not None:
            existing_creation = existing_creation.filter(ProcessEvent.maintenance_id == maintenance_id)
        if existing_creation.first() is not None:
            return False

    from_value = _enum_value(from_status) if from_status is not None else None
    to_value = _enum_value(to_status) if to_status is not None else None
    if _case_event_exists(
        db,
        case_id=case.id,
        event_type=event_type,
        maintenance_id=maintenance_id,
        from_status=from_value,
        to_status=to_value,
        occurred_at=occurred_at,
    ):
        return False

    create_process_event(
        db,
        case=case,
        event_type=event_type,
        occurred_at=_as_utc_datetime(occurred_at),
        from_status=from_status,
        to_status=to_status,
        maintenance_id=maintenance_id,
        source=ProcessEventSource.BACKFILL,
        timestamp_quality=ProcessEventTimestampQuality.LEGACY_FIELD
        if event_type in (ProcessEventType.INCIDENT_CREATED, ProcessEventType.MAINTENANCE_CREATED)
        else ProcessEventTimestampQuality.ACTION_TIME,
        source_event_key=source_event_key,
        metadata=metadata,
    )
    created[event_type.value] += 1
    return True


def _normalize_case_sequences(db: Session, case_ids: set[int]) -> None:
    """Make sequence follow occurred_at with stable semantic tie-breaks."""
    def event_priority(event: ProcessEvent) -> int:
        event_type = _enum_value(event.event_type)
        if event_type == ProcessEventType.INCIDENT_CREATED.value:
            return 0
        if event_type == ProcessEventType.MAINTENANCE_CREATED.value:
            return 1
        if event_type == ProcessEventType.TECHNICIAN_ASSIGNED.value:
            return 2
        if event_type == ProcessEventType.MAINTENANCE_STATUS_CHANGED.value:
            if (
                event.from_status == MaintenanceStatus.SCHEDULED.value
                and event.to_status == MaintenanceStatus.IN_PROGRESS.value
            ):
                return 3
            if (
                event.from_status == MaintenanceStatus.IN_PROGRESS.value
                and event.to_status == MaintenanceStatus.COMPLETED.value
            ):
                return 4
            return 5
        if event_type == ProcessEventType.INCIDENT_STATUS_CHANGED.value:
            return 6
        return 7

    for case_id in sorted(case_ids):
        db.query(ProcessCase).filter(ProcessCase.id == case_id).with_for_update().one()
        events = db.query(ProcessEvent).filter(ProcessEvent.case_id == case_id).all()
        if not events:
            continue
        events.sort(
            key=lambda event: (
                _utc_sort_value(event.occurred_at),
                event_priority(event),
                event.source_event_key or "",
                event.case_sequence,
                event.id,
            )
        )
        current_max = max(event.case_sequence for event in events)
        offset = current_max + len(events) + 1
        db.execute(
            update(ProcessEvent)
            .where(ProcessEvent.case_id == case_id)
            .values(case_sequence=ProcessEvent.case_sequence + offset)
            .execution_options(synchronize_session=False)
        )
        db.flush()
        for sequence, event in enumerate(events, start=1):
            db.expire(event, ["case_sequence"])
            event.case_sequence = sequence
        db.flush()


def backfill_process_events(db: Session) -> dict[str, Any]:
    """Backfill provable legacy events; leaves commit/rollback to the caller.

    A savepoint makes partial case/event writes roll back if any record fails,
    without committing the caller's transaction.
    """
    report: dict[str, Any] = {
        "incident_cases_created": 0,
        "maintenance_cases_created": 0,
        "events_created": Counter(),
        "incident_status_transitions_skipped": 0,
        "technician_assignments_skipped": 0,
        "maintenance_starts_skipped": 0,
        "maintenance_completions_skipped": 0,
    }
    created: Counter[str] = report["events_created"]
    affected_case_ids: set[int] = set()

    with db.begin_nested():
        incidents = db.query(Incident).order_by(Incident.id).all()
        incident_cases: dict[int, ProcessCase] = {}
        for incident in incidents:
            before = db.query(ProcessCase.id).filter(ProcessCase.incident_id == incident.id).first()
            case = get_or_create_incident_case(db, incident)
            incident_cases[incident.id] = case
            affected_case_ids.add(case.id)
            if before is None:
                report["incident_cases_created"] += 1

            _record_event(
                db,
                created,
                case=case,
                event_type=ProcessEventType.INCIDENT_CREATED,
                to_status=IncidentStatus(_enum_value(incident.status)),
                occurred_at=incident.created_at,
                source_event_key=f"legacy:incident:{incident.id}:created",
                metadata={
                    "backfill_reason": "legacy_incident_created_at",
                    "source_record": "incidents",
                    "source_id": incident.id,
                    "status_source": "current_incident_snapshot",
                },
            )
            report["incident_status_transitions_skipped"] += 1
            if incident.assigned_it_id is not None:
                report["technician_assignments_skipped"] += 1

        maintenances = db.query(Maintenance).order_by(Maintenance.id).all()
        for maintenance in maintenances:
            if maintenance.incident_id is not None:
                case = incident_cases.get(maintenance.incident_id)
                if case is None:
                    case = get_or_create_incident_case(db, maintenance.incident_id)
                    incident_cases[maintenance.incident_id] = case
                case_type = ProcessCaseType.INCIDENT
            else:
                before = db.query(ProcessCase.id).filter(
                    ProcessCase.maintenance_id == maintenance.id
                ).first()
                case = get_or_create_maintenance_case(db, maintenance)
                case_type = ProcessCaseType.MAINTENANCE
                if before is None:
                    report["maintenance_cases_created"] += 1
            affected_case_ids.add(case.id)

            _record_event(
                db,
                created,
                case=case,
                event_type=ProcessEventType.MAINTENANCE_CREATED,
                maintenance_id=maintenance.id,
                occurred_at=maintenance.created_at,
                source_event_key=f"legacy:maintenance:{maintenance.id}:created",
                metadata={
                    "backfill_reason": "legacy_maintenance_created_at",
                    "source_record": "maintenances",
                    "source_id": maintenance.id,
                    "case_type": case_type.value,
                    "creation_status_not_inferred": True,
                },
            )

            has_action_start = (
                maintenance.start_date is not None
                and _utc_sort_value(maintenance.start_date) > _utc_sort_value(maintenance.created_at)
            )
            if has_action_start:
                start_status = MaintenanceStatus.IN_PROGRESS
                _record_event(
                    db,
                    created,
                    case=case,
                    event_type=ProcessEventType.MAINTENANCE_STATUS_CHANGED,
                    maintenance_id=maintenance.id,
                    from_status=MaintenanceStatus.SCHEDULED,
                    to_status=start_status,
                    occurred_at=maintenance.start_date,
                    source_event_key=f"legacy:maintenance:{maintenance.id}:started",
                    metadata={
                        "backfill_reason": "legacy_maintenance_start_date",
                        "source_record": "maintenances.start_date",
                        "source_id": maintenance.id,
                    },
                )
            elif _enum_value(maintenance.status) in (
                MaintenanceStatus.IN_PROGRESS.value,
                MaintenanceStatus.COMPLETED.value,
            ):
                report["maintenance_starts_skipped"] += 1

            has_action_completion = (
                maintenance.completed_date is not None
                and has_action_start
                and _utc_sort_value(maintenance.completed_date) >= _utc_sort_value(maintenance.start_date)
            )
            if has_action_completion:
                _record_event(
                    db,
                    created,
                    case=case,
                    event_type=ProcessEventType.MAINTENANCE_STATUS_CHANGED,
                    maintenance_id=maintenance.id,
                    from_status=MaintenanceStatus.IN_PROGRESS,
                    to_status=MaintenanceStatus.COMPLETED,
                    occurred_at=maintenance.completed_date,
                    source_event_key=f"legacy:maintenance:{maintenance.id}:completed",
                    metadata={
                        "backfill_reason": "legacy_maintenance_completed_date",
                        "source_record": "maintenances.completed_date",
                        "source_id": maintenance.id,
                    },
                )
            elif maintenance.completed_date is not None:
                report["maintenance_completions_skipped"] += 1

        _normalize_case_sequences(db, affected_case_ids)
        db.flush()

    return report
