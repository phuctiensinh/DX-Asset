"""Deterministic process-mining metrics over the structured event log only."""

from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from statistics import mean, median
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.enums import (
    IncidentStatus,
    MaintenanceStatus,
    ProcessCaseType,
    ProcessEventSource,
    ProcessEventTimestampQuality,
    ProcessEventType,
)
from app.models.process_case import ProcessCase
from app.models.process_event import ProcessEvent
from app.schemas.process_mining import (
    DurationStatistics,
    ObservedFlowEdge,
    ProcessBottleneck,
    ProcessCaseDetail,
    ProcessConformanceMetrics,
    ProcessDeviation,
    ProcessEventDetail,
    ProcessMiningCohort,
    ProcessMiningCaseListItem,
    ProcessMiningCasesResponse,
    ProcessMiningDataQuality,
    ProcessMiningFilters,
    ProcessMiningSummary,
    ProcessReworkMetrics,
    ProcessVariant,
    ProcessVariantReport,
)


# Kept aligned with app.api.v1.incidents.VALID_TRANSITIONS. A regression test
# verifies parity so analytics never invents a separate workflow definition.
INCIDENT_VALID_TRANSITIONS = {
    IncidentStatus.OPEN.value: {
        IncidentStatus.OPEN.value,
        IncidentStatus.IN_REVIEW.value,
        IncidentStatus.IN_PROGRESS.value,
        IncidentStatus.CANCELLED.value,
    },
    IncidentStatus.IN_REVIEW.value: {
        IncidentStatus.IN_REVIEW.value,
        IncidentStatus.IN_PROGRESS.value,
        IncidentStatus.WAITING_FOR_INFO.value,
        IncidentStatus.RESOLVED.value,
        IncidentStatus.CANCELLED.value,
    },
    IncidentStatus.IN_PROGRESS.value: {
        IncidentStatus.IN_PROGRESS.value,
        IncidentStatus.WAITING_FOR_INFO.value,
        IncidentStatus.RESOLVED.value,
        IncidentStatus.CANCELLED.value,
    },
    IncidentStatus.WAITING_FOR_INFO.value: {
        IncidentStatus.WAITING_FOR_INFO.value,
        IncidentStatus.IN_PROGRESS.value,
        IncidentStatus.RESOLVED.value,
        IncidentStatus.CANCELLED.value,
    },
    IncidentStatus.RESOLVED.value: {
        IncidentStatus.RESOLVED.value,
        IncidentStatus.CLOSED.value,
        IncidentStatus.IN_PROGRESS.value,
    },
    IncidentStatus.CLOSED.value: {IncidentStatus.CLOSED.value},
    IncidentStatus.CANCELLED.value: {IncidentStatus.CANCELLED.value},
}

_INCIDENT_CREATED = ProcessEventType.INCIDENT_CREATED.value
_MAINTENANCE_CREATED = ProcessEventType.MAINTENANCE_CREATED.value
_INCIDENT_STATUS = ProcessEventType.INCIDENT_STATUS_CHANGED.value
_MAINTENANCE_STATUS = ProcessEventType.MAINTENANCE_STATUS_CHANGED.value
_TECH_ASSIGNED = ProcessEventType.TECHNICIAN_ASSIGNED.value
_AMBIGUOUS = ProcessEventTimestampQuality.AMBIGUOUS.value


def _value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _valid_timestamp(event: ProcessEvent) -> bool:
    return (
        event.occurred_at is not None
        and _value(event.timestamp_quality) != _AMBIGUOUS
    )


def _seconds(start: ProcessEvent, end: ProcessEvent) -> Optional[float]:
    if not _valid_timestamp(start) or not _valid_timestamp(end):
        return None
    start_at = start.occurred_at
    end_at = end.occurred_at
    if start_at.tzinfo is None:
        start_at = start_at.replace(tzinfo=timezone.utc)
    if end_at.tzinfo is None:
        end_at = end_at.replace(tzinfo=timezone.utc)
    seconds = (end_at - start_at).total_seconds()
    return seconds if seconds >= 0 else None


def _duration_statistics(values: list[float]) -> DurationStatistics:
    if not values:
        return DurationStatistics(count=0)
    return DurationStatistics(
        count=len(values),
        min=min(values),
        max=max(values),
        average=mean(values),
        median=median(values),
    )


def _case_completion_event(case: ProcessCase, events: list[ProcessEvent]) -> Optional[ProcessEvent]:
    case_type = _value(case.case_type)
    for event in events:
        event_type = _value(event.event_type)
        if case_type == ProcessCaseType.INCIDENT.value:
            if event_type == _INCIDENT_STATUS and event.to_status == IncidentStatus.CLOSED.value:
                return event
        elif case_type == ProcessCaseType.MAINTENANCE.value:
            if event_type == _MAINTENANCE_STATUS and event.to_status == MaintenanceStatus.COMPLETED.value:
                return event
    return None


def _creation_event(case: ProcessCase, events: list[ProcessEvent]) -> Optional[ProcessEvent]:
    creation_type = (
        _INCIDENT_CREATED
        if _value(case.case_type) == ProcessCaseType.INCIDENT.value
        else _MAINTENANCE_CREATED
    )
    return next((event for event in events if _value(event.event_type) == creation_type), None)


def _processing_seconds(case: ProcessCase, events: list[ProcessEvent]) -> Optional[float]:
    if not events:
        return None
    completion = _case_completion_event(case, events)
    if completion is None:
        return None
    return _seconds(events[0], completion)


def _first_action_seconds(case: ProcessCase, events: list[ProcessEvent]) -> Optional[float]:
    creation = _creation_event(case, events)
    if creation is None:
        return None
    for event in events:
        if event.case_sequence <= creation.case_sequence:
            continue
        return _seconds(creation, event)
    return None


def _maintenance_durations(events: list[ProcessEvent]) -> list[float]:
    by_maintenance: dict[int, list[ProcessEvent]] = defaultdict(list)
    for event in events:
        if event.maintenance_id is not None:
            by_maintenance[event.maintenance_id].append(event)

    durations: list[float] = []
    for maintenance_events in by_maintenance.values():
        ordered = sorted(maintenance_events, key=lambda event: event.case_sequence)
        pending_starts: list[ProcessEvent] = []
        for event in ordered:
            if _value(event.event_type) != _MAINTENANCE_STATUS:
                continue
            if (
                event.from_status == MaintenanceStatus.SCHEDULED.value
                and event.to_status == MaintenanceStatus.IN_PROGRESS.value
            ):
                pending_starts.append(event)
            elif (
                event.from_status == MaintenanceStatus.IN_PROGRESS.value
                and event.to_status == MaintenanceStatus.COMPLETED.value
                and pending_starts
            ):
                start_event = pending_starts.pop(0)
                duration = _seconds(start_event, event)
                if duration is not None:
                    durations.append(duration)
    return durations


def _event_sources(events: list[ProcessEvent]) -> set[str]:
    return {_value(event.source) for event in events}


class ProcessMiningService:
    """Batch-load events and calculate transparent metrics without snapshots."""

    @staticmethod
    def _load_dataset(
        db: Session,
        filters: Optional[ProcessMiningFilters] = None,
    ) -> tuple[list[ProcessCase], dict[int, list[ProcessEvent]], dict[int, set[str]]]:
        filters = filters or ProcessMiningFilters()
        restrict_by_event = any(
            value is not None for value in (filters.date_from, filters.date_to, filters.source)
        )

        case_query = db.query(ProcessCase)
        if filters.case_type is not None:
            case_query = case_query.filter(ProcessCase.case_type == filters.case_type)

        selected_case_ids: Optional[list[int]] = None
        if restrict_by_event:
            matching_ids_query = db.query(ProcessEvent.case_id).join(
                ProcessCase, ProcessCase.id == ProcessEvent.case_id
            )
            if filters.case_type is not None:
                matching_ids_query = matching_ids_query.filter(ProcessCase.case_type == filters.case_type)
            if filters.source is not None:
                matching_ids_query = matching_ids_query.filter(ProcessEvent.source == filters.source)
            if filters.date_from is not None:
                matching_ids_query = matching_ids_query.filter(ProcessEvent.occurred_at >= filters.date_from)
            if filters.date_to is not None:
                matching_ids_query = matching_ids_query.filter(ProcessEvent.occurred_at < filters.date_to)
            selected_case_ids = [row[0] for row in matching_ids_query.distinct().all()]
            if not selected_case_ids:
                return [], {}, {}
            case_query = case_query.filter(ProcessCase.id.in_(selected_case_ids))

        cases = case_query.order_by(ProcessCase.id).all()
        if not cases:
            return [], {}, {}
        case_ids = [case.id for case in cases]

        events_query = db.query(ProcessEvent).filter(ProcessEvent.case_id.in_(case_ids))
        if filters.source is not None:
            events_query = events_query.filter(ProcessEvent.source == filters.source)
        if filters.date_from is not None:
            events_query = events_query.filter(ProcessEvent.occurred_at >= filters.date_from)
        if filters.date_to is not None:
            events_query = events_query.filter(ProcessEvent.occurred_at < filters.date_to)
        events = events_query.order_by(ProcessEvent.case_id, ProcessEvent.case_sequence).all()

        events_by_case: dict[int, list[ProcessEvent]] = defaultdict(list)
        for event in events:
            events_by_case[event.case_id].append(event)

        # Aggregate all-source coverage for selected cases without loading their
        # excluded event rows into Python.
        coverage: dict[int, set[str]] = defaultdict(set)
        source_rows = db.query(ProcessEvent.case_id, ProcessEvent.source).filter(
            ProcessEvent.case_id.in_(case_ids)
        ).distinct().all()
        for case_id, source in source_rows:
            coverage[case_id].add(_value(source))
        return cases, dict(events_by_case), dict(coverage)

    @staticmethod
    def _cohort(
        filters: ProcessMiningFilters,
        cases: list[ProcessCase],
        events_by_case: dict[int, list[ProcessEvent]],
    ) -> ProcessMiningCohort:
        source = _value(filters.source) if filters.source is not None else "ALL"
        eventful_cases = sum(bool(events_by_case.get(case.id)) for case in cases)
        note = (
            "Metrics describe the selected event-log slice. BACKFILL logs may be partial; "
            "source coverage is reported separately and no missing workflow is inferred."
        )
        if filters.date_from is not None or filters.date_to is not None:
            note += " Date window uses occurred_at with inclusive date_from and exclusive date_to."
        return ProcessMiningCohort(
            source=source,
            case_type=filters.case_type,
            date_from=filters.date_from,
            date_to=filters.date_to,
            total_cases=len(cases),
            eventful_cases=eventful_cases,
            coverage_note=note,
        )

    @staticmethod
    def _data_quality(
        cases: list[ProcessCase],
        events_by_case: dict[int, list[ProcessEvent]],
        source_coverage: dict[int, set[str]],
        cohort_note: str,
    ) -> ProcessMiningDataQuality:
        all_events = [event for events in events_by_case.values() for event in events]
        completed_cases = sum(
            _case_completion_event(case, events_by_case.get(case.id, [])) is not None
            for case in cases
        )
        return ProcessMiningDataQuality(
            total_cases=len(cases),
            total_events=len(all_events),
            live_events=sum(_value(event.source) == ProcessEventSource.LIVE.value for event in all_events),
            backfill_events=sum(_value(event.source) == ProcessEventSource.BACKFILL.value for event in all_events),
            action_time_events=sum(_value(event.timestamp_quality) == ProcessEventTimestampQuality.ACTION_TIME.value for event in all_events),
            legacy_field_events=sum(_value(event.timestamp_quality) == ProcessEventTimestampQuality.LEGACY_FIELD.value for event in all_events),
            ambiguous_timestamp_events=sum(_value(event.timestamp_quality) == _AMBIGUOUS for event in all_events),
            cases_without_creation_event=sum(
                _creation_event(case, events_by_case.get(case.id, [])) is None for case in cases
            ),
            cases_without_completion_event=len(cases) - completed_cases,
            incomplete_cases=len(cases) - completed_cases,
            live_case_count=sum(
                any(_value(event.source) == ProcessEventSource.LIVE.value for event in events_by_case.get(case.id, []))
                for case in cases
            ),
            backfill_case_count=sum(
                any(_value(event.source) == ProcessEventSource.BACKFILL.value for event in events_by_case.get(case.id, []))
                for case in cases
            ),
            cases_with_mixed_sources=sum(
                len(source_coverage.get(case.id, set())) > 1 for case in cases
            ),
            cohort_note=cohort_note,
        )

    @staticmethod
    def get_summary(
        db: Session,
        filters: Optional[ProcessMiningFilters] = None,
    ) -> ProcessMiningSummary:
        filters = filters or ProcessMiningFilters()
        cases, events_by_case, source_coverage = ProcessMiningService._load_dataset(db, filters)
        completed = [
            case for case in cases
            if _case_completion_event(case, events_by_case.get(case.id, [])) is not None
        ]
        processing_values = [
            duration for case in completed
            if (duration := _processing_seconds(case, events_by_case.get(case.id, []))) is not None
        ]
        first_action_values = [
            duration for case in cases
            if (duration := _first_action_seconds(case, events_by_case.get(case.id, []))) is not None
        ]
        all_events = [event for rows in events_by_case.values() for event in rows]
        all_events.sort(key=lambda event: (event.case_id, event.case_sequence))
        note = ProcessMiningService._cohort(filters, cases, events_by_case).coverage_note
        quality = ProcessMiningService._data_quality(cases, events_by_case, source_coverage, note)
        return ProcessMiningSummary(
            cohort=ProcessMiningService._cohort(filters, cases, events_by_case),
            total_cases=len(cases),
            completed_cases=len(completed),
            incomplete_cases=len(cases) - len(completed),
            total_events=len(all_events),
            live_events=sum(_value(event.source) == ProcessEventSource.LIVE.value for event in all_events),
            backfill_events=sum(_value(event.source) == ProcessEventSource.BACKFILL.value for event in all_events),
            processing_time=_duration_statistics(processing_values),
            first_action_time=_duration_statistics(first_action_values),
            maintenance_duration=_duration_statistics(_maintenance_durations(all_events)),
            data_quality=quality,
            observed_flow=ProcessMiningService.get_observed_flow(db, filters),
        )

    @staticmethod
    def get_variants(
        db: Session,
        filters: Optional[ProcessMiningFilters] = None,
    ) -> ProcessVariantReport:
        filters = filters or ProcessMiningFilters()
        cases, events_by_case, _ = ProcessMiningService._load_dataset(db, filters)
        grouped: dict[tuple[str, ...], int] = defaultdict(int)
        for case in cases:
            events = events_by_case.get(case.id, [])
            if events:
                grouped[tuple(_value(event.event_type) for event in events)] += 1
        denominator = sum(grouped.values())
        variants = []
        for sequence, case_count in sorted(grouped.items(), key=lambda item: (-item[1], item[0])):
            identity = sha256("|".join(sequence).encode("utf-8")).hexdigest()[:16]
            variants.append(ProcessVariant(
                variant_id=f"variant-{identity}",
                event_sequence=[ProcessEventType(event_type) for event_type in sequence],
                case_count=case_count,
                percentage=(case_count / denominator * 100) if denominator else 0.0,
            ))
        return ProcessVariantReport(
            cohort=ProcessMiningService._cohort(filters, cases, events_by_case),
            denominator_cases=denominator,
            variants=variants,
        )

    @staticmethod
    def _adjacent_observations(
        cases: list[ProcessCase],
        events_by_case: dict[int, list[ProcessEvent]],
    ) -> dict[tuple[str, str], list[Optional[float]]]:
        observations: dict[tuple[str, str], list[Optional[float]]] = defaultdict(list)
        for case in cases:
            events = events_by_case.get(case.id, [])
            for current, following in zip(events, events[1:]):
                pair = (_value(current.event_type), _value(following.event_type))
                observations[pair].append(_seconds(current, following))
        return observations

    @staticmethod
    def get_bottlenecks(
        db: Session,
        filters: Optional[ProcessMiningFilters] = None,
        *,
        min_sample: int = 5,
    ) -> list[ProcessBottleneck]:
        if min_sample < 1:
            raise ValueError("min_sample must be at least 1")
        filters = filters or ProcessMiningFilters()
        cases, events_by_case, _ = ProcessMiningService._load_dataset(db, filters)
        result = []
        for (from_event, to_event), samples_with_invalid in ProcessMiningService._adjacent_observations(cases, events_by_case).items():
            samples = [value for value in samples_with_invalid if value is not None]
            if len(samples) < min_sample:
                continue
            result.append(ProcessBottleneck(
                from_event=ProcessEventType(from_event),
                to_event=ProcessEventType(to_event),
                count=len(samples),
                min_duration=min(samples),
                max_duration=max(samples),
                average_duration=mean(samples),
                median_duration=median(samples),
            ))
        result.sort(key=lambda row: (-row.median_duration, -row.count, row.from_event.value, row.to_event.value))
        return result

    @staticmethod
    def get_observed_flow(
        db: Session,
        filters: Optional[ProcessMiningFilters] = None,
    ) -> list[ObservedFlowEdge]:
        filters = filters or ProcessMiningFilters()
        cases, events_by_case, _ = ProcessMiningService._load_dataset(db, filters)
        result = []
        for (from_event, to_event), samples_with_invalid in ProcessMiningService._adjacent_observations(cases, events_by_case).items():
            samples = [value for value in samples_with_invalid if value is not None]
            result.append(ObservedFlowEdge(
                from_event=ProcessEventType(from_event),
                to_event=ProcessEventType(to_event),
                count=len(samples_with_invalid),
                median_duration=median(samples) if samples else None,
            ))
        result.sort(key=lambda row: (row.from_event.value, row.to_event.value))
        return result

    @staticmethod
    def get_rework(
        db: Session,
        filters: Optional[ProcessMiningFilters] = None,
    ) -> ProcessReworkMetrics:
        filters = filters or ProcessMiningFilters()
        if filters.source is None:
            filters = filters.model_copy(update={"source": ProcessEventSource.LIVE})
        cases, events_by_case, _ = ProcessMiningService._load_dataset(db, filters)
        eligible = 0
        rework_cases = 0
        rework_events = 0
        for case in cases:
            if _value(case.case_type) != ProcessCaseType.INCIDENT.value:
                continue
            events = events_by_case.get(case.id, [])
            observed = [
                event for event in events
                if _value(event.event_type) == _INCIDENT_STATUS
                and event.from_status is not None
                and event.to_status is not None
            ]
            completed = _case_completion_event(case, events) is not None
            if observed or completed:
                eligible += 1
            signals = [
                event for event in observed
                if event.from_status == IncidentStatus.RESOLVED.value
                and event.to_status == IncidentStatus.IN_PROGRESS.value
            ]
            if signals:
                rework_cases += 1
                rework_events += len(signals)
        source = ProcessEventSource(_value(filters.source))
        source_label = source.value
        return ProcessReworkMetrics(
            source=source,
            total_rework_cases=rework_cases,
            total_rework_events=rework_events,
            eligible_cases=eligible,
            denominator_description=(
                f"{source_label} Incident cases with at least one observed status transition or an observed "
                "CLOSED event in the selected date cohort; cases with creation only are excluded."
            ),
            rework_rate=(rework_cases / eligible) if eligible else None,
        )

    @staticmethod
    def _case_conformance(case_id: int, events: list[ProcessEvent]) -> ProcessConformanceMetrics:
        transitions = [
            event for event in events
            if _value(event.event_type) == _INCIDENT_STATUS
            and event.from_status is not None
            and event.to_status is not None
            and _value(event.timestamp_quality) != _AMBIGUOUS
        ]
        deviations = []
        for event in transitions:
            allowed = INCIDENT_VALID_TRANSITIONS.get(event.from_status, set())
            if event.to_status not in allowed:
                deviations.append(ProcessDeviation(
                    case_id=case_id,
                    event_id=event.id,
                    from_status=event.from_status,
                    to_status=event.to_status,
                    reason="Observed transition is not present in Incident VALID_TRANSITIONS.",
                ))
        eligible = bool(transitions)
        deviating = bool(deviations)
        return ProcessConformanceMetrics(
            eligible_cases=1 if eligible else 0,
            conforming_cases=1 if eligible and not deviating else 0,
            deviating_cases=1 if eligible and deviating else 0,
            conformance_rate=(0.0 if deviating else 1.0) if eligible else None,
            deviations=deviations,
            note="Observed Incident status transitions only; optional assignment and maintenance steps are not required.",
        )

    @staticmethod
    def get_conformance(
        db: Session,
        filters: Optional[ProcessMiningFilters] = None,
    ) -> ProcessConformanceMetrics:
        filters = filters or ProcessMiningFilters(case_type=ProcessCaseType.INCIDENT)
        if filters.case_type is None:
            filters = filters.model_copy(update={"case_type": ProcessCaseType.INCIDENT})
        cases, events_by_case, _ = ProcessMiningService._load_dataset(db, filters)
        per_case = [
            ProcessMiningService._case_conformance(case.id, events_by_case.get(case.id, []))
            for case in cases
        ]
        eligible = sum(result.eligible_cases for result in per_case)
        conforming = sum(result.conforming_cases for result in per_case)
        deviating = sum(result.deviating_cases for result in per_case)
        return ProcessConformanceMetrics(
            eligible_cases=eligible,
            conforming_cases=conforming,
            deviating_cases=deviating,
            conformance_rate=conforming / eligible if eligible else None,
            deviations=[deviation for result in per_case for deviation in result.deviations],
            note="Observed Incident status transitions only; optional assignment and maintenance steps are not required.",
        )

    @staticmethod
    def get_case_detail(
        db: Session,
        case_id: int,
        filters: Optional[ProcessMiningFilters] = None,
    ) -> Optional[ProcessCaseDetail]:
        filters = filters or ProcessMiningFilters()
        case_query = db.query(ProcessCase).filter(ProcessCase.id == case_id)
        if filters.case_type is not None:
            case_query = case_query.filter(ProcessCase.case_type == filters.case_type)
        case = case_query.first()
        if case is None:
            return None
        events_query = db.query(ProcessEvent).filter(ProcessEvent.case_id == case.id)
        if filters.source is not None:
            events_query = events_query.filter(ProcessEvent.source == filters.source)
        if filters.date_from is not None:
            events_query = events_query.filter(ProcessEvent.occurred_at >= filters.date_from)
        if filters.date_to is not None:
            events_query = events_query.filter(ProcessEvent.occurred_at < filters.date_to)
        events = events_query.order_by(ProcessEvent.case_sequence).all()
        if (filters.source is not None or filters.date_from is not None or filters.date_to is not None) and not events:
            return None
        source_coverage = {
            _value(source)
            for (source,) in db.query(ProcessEvent.source)
            .filter(ProcessEvent.case_id == case.id)
            .distinct()
            .all()
        }
        completion = _case_completion_event(case, events)
        processing = _processing_seconds(case, events) if completion is not None else None
        first_action = _first_action_seconds(case, events)
        rework_events = sum(
            _value(event.event_type) == _INCIDENT_STATUS
            and event.from_status == IncidentStatus.RESOLVED.value
            and event.to_status == IncidentStatus.IN_PROGRESS.value
            and _value(event.source) == ProcessEventSource.LIVE.value
            for event in events
        )
        return ProcessCaseDetail(
            case_id=case.id,
            case_type=case.case_type,
            incident_id=case.incident_id,
            maintenance_id=case.maintenance_id,
            source_coverage=[ProcessEventSource(value) for value in sorted(source_coverage)],
            events=[
                ProcessEventDetail(
                    id=event.id,
                    event_type=event.event_type,
                    from_status=event.from_status,
                    to_status=event.to_status,
                    performed_by_id=event.performed_by_id,
                    target_user_id=event.target_user_id,
                    occurred_at=event.occurred_at,
                    source=event.source,
                    timestamp_quality=event.timestamp_quality,
                    sequence=event.case_sequence,
                )
                for event in events
            ],
            processing_time=processing,
            first_action_time=first_action,
            rework_events=rework_events,
            conformance=ProcessMiningService._case_conformance(case.id, events),
        )

    @staticmethod
    def get_cases(
        db: Session,
        filters: Optional[ProcessMiningFilters] = None,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> ProcessMiningCasesResponse:
        """Return a bounded, serialized case page and aggregates for its event slice."""
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be positive")
        filters = filters or ProcessMiningFilters()
        query = db.query(ProcessCase)
        if filters.case_type is not None:
            query = query.filter(ProcessCase.case_type == filters.case_type)
        restrict_by_event = any(
            value is not None for value in (filters.date_from, filters.date_to, filters.source)
        )
        if restrict_by_event:
            matching_events = db.query(ProcessEvent.case_id).filter(
                ProcessEvent.case_id == ProcessCase.id
            )
            if filters.source is not None:
                matching_events = matching_events.filter(ProcessEvent.source == filters.source)
            if filters.date_from is not None:
                matching_events = matching_events.filter(ProcessEvent.occurred_at >= filters.date_from)
            if filters.date_to is not None:
                matching_events = matching_events.filter(ProcessEvent.occurred_at < filters.date_to)
            query = query.filter(matching_events.exists())

        total = query.count()
        cases = query.order_by(ProcessCase.created_at.desc(), ProcessCase.id.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        case_ids = [case.id for case in cases]
        events_by_case: dict[int, list[ProcessEvent]] = defaultdict(list)
        coverage: dict[int, set[str]] = defaultdict(set)
        if case_ids:
            event_query = db.query(ProcessEvent).filter(ProcessEvent.case_id.in_(case_ids))
            if filters.source is not None:
                event_query = event_query.filter(ProcessEvent.source == filters.source)
            if filters.date_from is not None:
                event_query = event_query.filter(ProcessEvent.occurred_at >= filters.date_from)
            if filters.date_to is not None:
                event_query = event_query.filter(ProcessEvent.occurred_at < filters.date_to)
            for event in event_query.order_by(ProcessEvent.case_id, ProcessEvent.case_sequence).all():
                events_by_case[event.case_id].append(event)
            for case_id, source in db.query(ProcessEvent.case_id, ProcessEvent.source).filter(
                ProcessEvent.case_id.in_(case_ids)
            ).distinct().all():
                coverage[case_id].add(_value(source))

        items = []
        for case in cases:
            events = events_by_case.get(case.id, [])
            completion = _case_completion_event(case, events)
            processing = _processing_seconds(case, events) if completion is not None else None
            items.append(ProcessMiningCaseListItem(
                case_id=case.id,
                case_type=case.case_type,
                incident_id=case.incident_id,
                maintenance_id=case.maintenance_id,
                created_at=case.created_at,
                event_count=len(events),
                source_coverage=[ProcessEventSource(value) for value in sorted(coverage.get(case.id, set()))],
                first_event_at=events[0].occurred_at if events else None,
                last_event_at=events[-1].occurred_at if events else None,
                completed=completion is not None,
                processing_duration=processing,
            ))
        return ProcessMiningCasesResponse(items=items, total=total, page=page, page_size=page_size)
