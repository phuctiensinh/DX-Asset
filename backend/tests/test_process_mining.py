from datetime import datetime, timedelta, timezone
import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.asset import Asset
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
)
from app.models.incident import Incident
from app.models.maintenance import Maintenance
from app.models.process_case import ProcessCase
from app.models.user import User
from app.schemas.process_mining import ProcessMiningFilters
from app.services.process_event_writer import create_process_event
from app.services.process_mining import INCIDENT_VALID_TRANSITIONS, ProcessMiningService


def _stamp(year: int, seconds: int = 0) -> datetime:
    return datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)


def _filters(year: int, **kwargs) -> ProcessMiningFilters:
    return ProcessMiningFilters(
        date_from=_stamp(year),
        date_to=_stamp(year + 1),
        **kwargs,
    )


def _add_incident_case(
    db: Session,
    admin: User,
    year: int,
    specs: list[dict],
    *,
    maintenance: bool = False,
) -> tuple[ProcessCase, Incident, Maintenance | None]:
    asset = Asset(
        asset_code=f"PM-{uuid.uuid4().hex[:12].upper()}",
        name="Synthetic process mining asset",
        category="Laptop",
        status=AssetStatus.IN_STOCK,
    )
    db.add(asset)
    db.flush()
    incident = Incident(
        ticket_code=f"PM-{uuid.uuid4().hex[:12].upper()}",
        asset_id=asset.id,
        reporter_id=admin.id,
        title="Synthetic process case",
        description="Created for deterministic process mining tests",
        category=IncidentCategory.HARDWARE,
        priority=IncidentPriority.MEDIUM,
        status=IncidentStatus.RESOLVED,
        created_at=_stamp(year),
    )
    db.add(incident)
    db.flush()
    case = ProcessCase(case_type=ProcessCaseType.INCIDENT, incident_id=incident.id)
    db.add(case)
    db.flush()
    maintenance_row = None
    if maintenance:
        maintenance_row = Maintenance(
            maintenance_code=f"PM-{uuid.uuid4().hex[:12].upper()}",
            asset_id=asset.id,
            incident_id=incident.id,
            title="Synthetic linked maintenance",
            status=MaintenanceStatus.COMPLETED,
            created_at=_stamp(year),
        )
        db.add(maintenance_row)
        db.flush()

    for index, spec in enumerate(specs):
        event_type = spec["type"]
        source = spec.get("source", ProcessEventSource.LIVE)
        occurred_at = _stamp(year, spec.get("seconds", index))
        attach_maintenance = spec.get(
            "maintenance",
            event_type in (ProcessEventType.MAINTENANCE_CREATED, ProcessEventType.MAINTENANCE_STATUS_CHANGED),
        )
        create_process_event(
            db,
            case=case,
            event_type=event_type,
            occurred_at=occurred_at,
            from_status=spec.get("from"),
            to_status=spec.get("to"),
            maintenance_id=(
                maintenance_row.id if attach_maintenance and maintenance_row else None
            ),
            performed_by_id=spec.get("performed_by_id"),
            target_user_id=spec.get("target_user_id"),
            source=source,
            timestamp_quality=spec.get(
                "quality", ProcessEventTimestampQuality.ACTION_TIME
            ),
            source_event_key=f"pm-test:{uuid.uuid4().hex}:{index}",
        )
    db.flush()
    return case, incident, maintenance_row


def _add_maintenance_case(
    db: Session,
    admin: User,
    year: int,
    specs: list[dict],
) -> tuple[ProcessCase, Maintenance]:
    asset = Asset(
        asset_code=f"PM-{uuid.uuid4().hex[:12].upper()}",
        name="Synthetic maintenance asset",
        category="Monitor",
        status=AssetStatus.IN_STOCK,
    )
    db.add(asset)
    db.flush()
    maintenance = Maintenance(
        maintenance_code=f"PM-{uuid.uuid4().hex[:12].upper()}",
        asset_id=asset.id,
        title="Synthetic independent maintenance",
        status=MaintenanceStatus.COMPLETED,
        created_at=_stamp(year),
    )
    db.add(maintenance)
    db.flush()
    case = ProcessCase(case_type=ProcessCaseType.MAINTENANCE, maintenance_id=maintenance.id)
    db.add(case)
    db.flush()
    for index, spec in enumerate(specs):
        create_process_event(
            db,
            case=case,
            event_type=spec["type"],
            maintenance_id=maintenance.id,
            occurred_at=_stamp(year, spec.get("seconds", index)),
            from_status=spec.get("from"),
            to_status=spec.get("to"),
            performed_by_id=spec.get("performed_by_id"),
            target_user_id=spec.get("target_user_id"),
            source=spec.get("source", ProcessEventSource.LIVE),
            timestamp_quality=spec.get("quality", ProcessEventTimestampQuality.ACTION_TIME),
            source_event_key=f"pm-test:{uuid.uuid4().hex}:{index}",
        )
    db.flush()
    return case, maintenance


def _created_incident_event(seconds: int = 0, source=ProcessEventSource.LIVE) -> dict:
    return {
        "type": ProcessEventType.INCIDENT_CREATED,
        "seconds": seconds,
        "to": IncidentStatus.OPEN,
        "source": source,
        "quality": ProcessEventTimestampQuality.ACTION_TIME,
    }


def test_empty_data_returns_empty_metrics_without_division_by_zero(db: Session):
    filters = ProcessMiningFilters(date_from=_stamp(2090), date_to=_stamp(2091))
    summary = ProcessMiningService.get_summary(db, filters)
    assert summary.total_cases == summary.total_events == 0
    assert summary.completed_cases == summary.incomplete_cases == 0
    assert summary.processing_time.count == summary.first_action_time.count == 0
    assert summary.maintenance_duration.count == 0
    assert ProcessMiningService.get_variants(db, filters).variants == []
    assert ProcessMiningService.get_bottlenecks(db, filters) == []
    assert ProcessMiningService.get_observed_flow(db, filters) == []
    rework = ProcessMiningService.get_rework(db, filters)
    assert rework.eligible_cases == 0 and rework.rework_rate is None
    conformance = ProcessMiningService.get_conformance(db, filters)
    assert conformance.eligible_cases == 0 and conformance.conformance_rate is None
    assert ProcessMiningService.get_case_detail(db, 999999, filters) is None


def test_incident_completion_processing_first_action_and_incomplete_case(db: Session, admin_user: User):
    completed_case, _, _ = _add_incident_case(db, admin_user, 2040, [
        _created_incident_event(),
        {"type": ProcessEventType.TECHNICIAN_ASSIGNED, "seconds": 10, "target_user_id": admin_user.id},
        {"type": ProcessEventType.INCIDENT_STATUS_CHANGED, "seconds": 20, "from": IncidentStatus.OPEN, "to": IncidentStatus.IN_REVIEW},
        {"type": ProcessEventType.INCIDENT_STATUS_CHANGED, "seconds": 30, "from": IncidentStatus.IN_REVIEW, "to": IncidentStatus.IN_PROGRESS},
        {"type": ProcessEventType.INCIDENT_STATUS_CHANGED, "seconds": 60, "from": IncidentStatus.IN_PROGRESS, "to": IncidentStatus.RESOLVED},
        {"type": ProcessEventType.INCIDENT_STATUS_CHANGED, "seconds": 120, "from": IncidentStatus.RESOLVED, "to": IncidentStatus.CLOSED},
    ])
    _add_incident_case(db, admin_user, 2040, [_created_incident_event(200)])
    result = ProcessMiningService.get_summary(db, _filters(2040, case_type=ProcessCaseType.INCIDENT))
    assert (result.total_cases, result.completed_cases, result.incomplete_cases) == (2, 1, 1)
    assert result.processing_time.count == 1
    assert result.processing_time.min == result.processing_time.max == 120
    assert result.first_action_time.count == 1
    assert result.first_action_time.average == 10
    assert result.data_quality.cases_without_creation_event == 0
    assert result.data_quality.cases_without_completion_event == 1
    detail = ProcessMiningService.get_case_detail(
        db, completed_case.id, _filters(2040, case_type=ProcessCaseType.INCIDENT)
    )
    assert detail is not None
    assert detail.processing_time == 120
    assert detail.first_action_time == 10
    assert detail.events[0].event_type == ProcessEventType.INCIDENT_CREATED
    assert detail.events[0].sequence == 1


def test_incident_resolved_is_not_completed_without_closed_event(db: Session, admin_user: User):
    _add_incident_case(db, admin_user, 2041, [
        _created_incident_event(),
        {"type": ProcessEventType.INCIDENT_STATUS_CHANGED, "seconds": 50, "from": IncidentStatus.IN_PROGRESS, "to": IncidentStatus.RESOLVED},
    ])
    result = ProcessMiningService.get_summary(db, _filters(2041, case_type=ProcessCaseType.INCIDENT))
    assert result.completed_cases == 0
    assert result.processing_time.count == 0


def test_linked_maintenance_creation_is_a_meaningful_incident_first_action(db: Session, admin_user: User):
    _add_incident_case(db, admin_user, 2051, [
        _created_incident_event(),
        {"type": ProcessEventType.MAINTENANCE_CREATED, "seconds": 15},
    ], maintenance=True)
    result = ProcessMiningService.get_summary(db, _filters(2051, case_type=ProcessCaseType.INCIDENT))
    assert result.first_action_time.count == 1
    assert result.first_action_time.average == 15


def test_duration_statistics_min_max_average_and_median(db: Session, admin_user: User):
    for index, (processing, first_action) in enumerate(((10, 2), (20, 5), (60, 8))):
        _add_incident_case(db, admin_user, 2052, [
            _created_incident_event(index * 100),
            {"type": ProcessEventType.TECHNICIAN_ASSIGNED, "seconds": index * 100 + first_action, "target_user_id": admin_user.id},
            {"type": ProcessEventType.INCIDENT_STATUS_CHANGED, "seconds": index * 100 + processing, "from": IncidentStatus.RESOLVED, "to": IncidentStatus.CLOSED},
        ])
    for index, (start, finish) in enumerate(((5, 25), (10, 30), (20, 60))):
        _add_maintenance_case(db, admin_user, 2052, [
            {"type": ProcessEventType.MAINTENANCE_CREATED, "seconds": 1000 + index * 100},
            {"type": ProcessEventType.MAINTENANCE_STATUS_CHANGED, "seconds": 1000 + index * 100 + start, "from": MaintenanceStatus.SCHEDULED, "to": MaintenanceStatus.IN_PROGRESS},
            {"type": ProcessEventType.MAINTENANCE_STATUS_CHANGED, "seconds": 1000 + index * 100 + finish, "from": MaintenanceStatus.IN_PROGRESS, "to": MaintenanceStatus.COMPLETED},
        ])
    incident_result = ProcessMiningService.get_summary(
        db, _filters(2052, case_type=ProcessCaseType.INCIDENT)
    )
    maintenance_result = ProcessMiningService.get_summary(
        db, _filters(2052, case_type=ProcessCaseType.MAINTENANCE)
    )
    assert (incident_result.processing_time.min, incident_result.processing_time.max, incident_result.processing_time.average, incident_result.processing_time.median) == (10, 60, 30, 20)
    assert (incident_result.first_action_time.min, incident_result.first_action_time.max, incident_result.first_action_time.average, incident_result.first_action_time.median) == (2, 8, 5, 5)
    assert (maintenance_result.maintenance_duration.min, maintenance_result.maintenance_duration.max, maintenance_result.maintenance_duration.average, maintenance_result.maintenance_duration.median) == pytest.approx((20, 40, 80 / 3, 20))


def test_maintenance_completion_and_duration_require_events_not_snapshot(db: Session, admin_user: User):
    _add_maintenance_case(db, admin_user, 2042, [
        {"type": ProcessEventType.MAINTENANCE_CREATED, "seconds": 0},
        {"type": ProcessEventType.MAINTENANCE_STATUS_CHANGED, "seconds": 20, "from": MaintenanceStatus.SCHEDULED, "to": MaintenanceStatus.IN_PROGRESS},
        {"type": ProcessEventType.MAINTENANCE_STATUS_CHANGED, "seconds": 80, "from": MaintenanceStatus.IN_PROGRESS, "to": MaintenanceStatus.COMPLETED},
    ])
    _add_maintenance_case(db, admin_user, 2042, [
        {"type": ProcessEventType.MAINTENANCE_CREATED, "seconds": 100},
    ])
    result = ProcessMiningService.get_summary(db, _filters(2042, case_type=ProcessCaseType.MAINTENANCE))
    assert (result.total_cases, result.completed_cases, result.incomplete_cases) == (2, 1, 1)
    assert result.processing_time.count == 1 and result.processing_time.average == 80
    assert result.maintenance_duration.count == 1 and result.maintenance_duration.average == 60


def test_variants_group_by_event_type_with_deterministic_percentages(db: Session, admin_user: User):
    sequence_a = [_created_incident_event(), {"type": ProcessEventType.TECHNICIAN_ASSIGNED, "seconds": 10, "target_user_id": admin_user.id}]
    sequence_b = [_created_incident_event(100), {"type": ProcessEventType.TECHNICIAN_ASSIGNED, "seconds": 110, "target_user_id": admin_user.id}]
    sequence_c = [_created_incident_event(200), {"type": ProcessEventType.INCIDENT_STATUS_CHANGED, "seconds": 210, "from": IncidentStatus.OPEN, "to": IncidentStatus.IN_REVIEW}]
    _add_incident_case(db, admin_user, 2043, sequence_a)
    _add_incident_case(db, admin_user, 2043, sequence_b)
    _add_incident_case(db, admin_user, 2043, sequence_c)
    report = ProcessMiningService.get_variants(db, _filters(2043, case_type=ProcessCaseType.INCIDENT))
    assert report.denominator_cases == 3
    assert [variant.case_count for variant in report.variants] == [2, 1]
    assert report.variants[0].percentage == pytest.approx(200 / 3)
    assert report.variants[1].percentage == pytest.approx(100 / 3)
    assert report.variants[0].event_sequence == [ProcessEventType.INCIDENT_CREATED, ProcessEventType.TECHNICIAN_ASSIGNED]
    assert report.variants[0].variant_id == ProcessMiningService.get_variants(
        db, _filters(2043, case_type=ProcessCaseType.INCIDENT)
    ).variants[0].variant_id


def test_source_filters_and_mixed_source_coverage_are_explicit(db: Session, admin_user: User):
    _add_incident_case(db, admin_user, 2044, [
        _created_incident_event(),
        {"type": ProcessEventType.INCIDENT_STATUS_CHANGED, "seconds": 10, "from": IncidentStatus.OPEN, "to": IncidentStatus.IN_REVIEW, "source": ProcessEventSource.BACKFILL, "quality": ProcessEventTimestampQuality.LEGACY_FIELD},
    ])
    live = ProcessMiningService.get_summary(db, _filters(2044, source=ProcessEventSource.LIVE))
    backfill = ProcessMiningService.get_summary(db, _filters(2044, source=ProcessEventSource.BACKFILL))
    assert (live.total_events, live.live_events, live.backfill_events) == (1, 1, 0)
    assert (backfill.total_events, backfill.live_events, backfill.backfill_events) == (1, 0, 1)
    assert live.data_quality.cases_with_mixed_sources == 1
    assert ProcessMiningService.get_variants(db, _filters(2044, source=ProcessEventSource.LIVE)).cohort.source == "LIVE"
    assert ProcessMiningService.get_variants(db, _filters(2044, source=ProcessEventSource.BACKFILL)).cohort.source == "BACKFILL"


def test_bottlenecks_minimum_sample_ranking_and_observed_flow(db: Session, admin_user: User):
    for index in range(5):
        _add_incident_case(db, admin_user, 2045, [
            _created_incident_event(index * 100),
            {"type": ProcessEventType.INCIDENT_STATUS_CHANGED, "seconds": index * 100 + 200, "from": IncidentStatus.OPEN, "to": IncidentStatus.IN_REVIEW},
        ])
        _add_incident_case(db, admin_user, 2045, [
            _created_incident_event(index * 100 + 1000),
            {"type": ProcessEventType.TECHNICIAN_ASSIGNED, "seconds": index * 100 + 1100, "target_user_id": admin_user.id},
        ])
        _add_incident_case(db, admin_user, 2045, [
            _created_incident_event(index * 100 + 2000),
            {"type": ProcessEventType.MAINTENANCE_CREATED, "seconds": index * 100 + 2100},
        ], maintenance=True)
    for index in range(4):
        _add_maintenance_case(db, admin_user, 2045, [
            {"type": ProcessEventType.MAINTENANCE_CREATED, "seconds": 3000 + index * 100},
            {"type": ProcessEventType.MAINTENANCE_STATUS_CHANGED, "seconds": 3050 + index * 100, "from": MaintenanceStatus.SCHEDULED, "to": MaintenanceStatus.IN_PROGRESS},
        ])

    filters = _filters(2045)
    bottlenecks = ProcessMiningService.get_bottlenecks(db, filters, min_sample=5)
    assert len(bottlenecks) == 3
    assert bottlenecks[0].median_duration == 200
    assert all(row.median_duration == 100 for row in bottlenecks[1:])
    assert (bottlenecks[1].from_event.value, bottlenecks[1].to_event.value) < (
        bottlenecks[2].from_event.value, bottlenecks[2].to_event.value
    )
    flow = ProcessMiningService.get_observed_flow(db, filters)
    assert ProcessMiningService.get_summary(db, filters).observed_flow == flow
    rare_edge = next(edge for edge in flow if edge.to_event == ProcessEventType.MAINTENANCE_STATUS_CHANGED)
    assert rare_edge.count == 4
    assert rare_edge.median_duration == 50
    assert ProcessMiningService.get_bottlenecks(db, filters, min_sample=1)[-1].count == 4
    with pytest.raises(ValueError, match="min_sample"):
        ProcessMiningService.get_bottlenecks(db, filters, min_sample=0)


def test_rework_counts_each_live_reopen_and_uses_explicit_denominator(db: Session, admin_user: User):
    _add_incident_case(db, admin_user, 2046, [
        _created_incident_event(),
        {"type": ProcessEventType.INCIDENT_STATUS_CHANGED, "seconds": 10, "from": IncidentStatus.OPEN, "to": IncidentStatus.IN_REVIEW},
        {"type": ProcessEventType.INCIDENT_STATUS_CHANGED, "seconds": 20, "from": IncidentStatus.IN_REVIEW, "to": IncidentStatus.RESOLVED},
        {"type": ProcessEventType.INCIDENT_STATUS_CHANGED, "seconds": 30, "from": IncidentStatus.RESOLVED, "to": IncidentStatus.IN_PROGRESS},
        {"type": ProcessEventType.INCIDENT_STATUS_CHANGED, "seconds": 40, "from": IncidentStatus.IN_PROGRESS, "to": IncidentStatus.RESOLVED},
        {"type": ProcessEventType.INCIDENT_STATUS_CHANGED, "seconds": 50, "from": IncidentStatus.RESOLVED, "to": IncidentStatus.IN_PROGRESS},
    ])
    _add_incident_case(db, admin_user, 2046, [_created_incident_event(100)])
    _add_incident_case(db, admin_user, 2046, [
        _created_incident_event(200, ProcessEventSource.BACKFILL),
        {"type": ProcessEventType.INCIDENT_STATUS_CHANGED, "seconds": 210, "from": IncidentStatus.RESOLVED, "to": IncidentStatus.IN_PROGRESS, "source": ProcessEventSource.BACKFILL, "quality": ProcessEventTimestampQuality.LEGACY_FIELD},
    ])
    metrics = ProcessMiningService.get_rework(db, _filters(2046))
    assert metrics.source == ProcessEventSource.LIVE
    assert (metrics.total_rework_cases, metrics.total_rework_events, metrics.eligible_cases) == (1, 2, 1)
    assert metrics.rework_rate == 1.0
    assert "LIVE Incident cases" in metrics.denominator_description
    backfill_metrics = ProcessMiningService.get_rework(
        db, _filters(2046, source=ProcessEventSource.BACKFILL)
    )
    assert backfill_metrics.total_rework_events == 1


def test_conformance_valid_invalid_and_optional_steps(db: Session, admin_user: User):
    _add_incident_case(db, admin_user, 2047, [
        _created_incident_event(),
        {"type": ProcessEventType.INCIDENT_STATUS_CHANGED, "seconds": 10, "from": IncidentStatus.OPEN, "to": IncidentStatus.IN_REVIEW},
    ])
    invalid_case, invalid_incident, _ = _add_incident_case(db, admin_user, 2047, [
        _created_incident_event(100),
        {"type": ProcessEventType.INCIDENT_STATUS_CHANGED, "seconds": 110, "from": IncidentStatus.CLOSED, "to": IncidentStatus.OPEN},
    ])
    optional_case, _, _ = _add_incident_case(db, admin_user, 2047, [_created_incident_event(200)])
    metrics = ProcessMiningService.get_conformance(db, _filters(2047))
    assert (metrics.eligible_cases, metrics.conforming_cases, metrics.deviating_cases) == (2, 1, 1)
    assert metrics.conformance_rate == 0.5
    assert len(metrics.deviations) == 1
    assert metrics.deviations[0].from_status == IncidentStatus.CLOSED.value
    optional_detail = ProcessMiningService.get_case_detail(db, optional_case.id, _filters(2047))
    assert optional_detail is not None and optional_detail.conformance.eligible_cases == 0
    invalid_detail = ProcessMiningService.get_case_detail(db, invalid_case.id, _filters(2047))
    assert invalid_detail is not None and len(invalid_detail.conformance.deviations) == 1


def test_data_quality_and_case_detail_are_serializable_and_source_aware(db: Session, admin_user: User):
    case, incident, _ = _add_incident_case(db, admin_user, 2048, [
        _created_incident_event(),
        {"type": ProcessEventType.TECHNICIAN_ASSIGNED, "seconds": 30, "target_user_id": admin_user.id, "source": ProcessEventSource.BACKFILL, "quality": ProcessEventTimestampQuality.AMBIGUOUS},
    ])
    quality = ProcessMiningService.get_summary(db, _filters(2048)).data_quality
    assert quality.total_cases == 1 and quality.total_events == 2
    assert quality.live_events == quality.backfill_events == 1
    assert quality.action_time_events == 1 and quality.ambiguous_timestamp_events == 1
    assert quality.cases_with_mixed_sources == 1
    detail = ProcessMiningService.get_case_detail(db, case.id, _filters(2048))
    assert detail is not None
    assert detail.case_type == ProcessCaseType.INCIDENT
    assert detail.incident_id == incident.id
    assert detail.source_coverage == [ProcessEventSource.BACKFILL, ProcessEventSource.LIVE]
    assert [event.sequence for event in detail.events] == [1, 2]
    assert detail.events[0].id > 0
    assert detail.events[1].target_user_id == admin_user.id
    assert detail.processing_time is None
    assert detail.first_action_time is None


def test_date_filter_is_occurred_at_inclusive_from_exclusive_to(db: Session, admin_user: User):
    base = _stamp(2049)
    case, _, _ = _add_incident_case(db, admin_user, 2049, [
        _created_incident_event(-1),
        {"type": ProcessEventType.INCIDENT_STATUS_CHANGED, "seconds": 0, "from": IncidentStatus.OPEN, "to": IncidentStatus.IN_REVIEW},
        {"type": ProcessEventType.TECHNICIAN_ASSIGNED, "seconds": 10, "target_user_id": admin_user.id},
    ])
    _add_incident_case(db, admin_user, 2049, [_created_incident_event(10)])
    _add_maintenance_case(db, admin_user, 2049, [
        {"type": ProcessEventType.MAINTENANCE_CREATED, "seconds": 1},
    ])
    filters = ProcessMiningFilters(
        date_from=base,
        date_to=base + timedelta(seconds=10),
        case_type=ProcessCaseType.INCIDENT,
        source=ProcessEventSource.LIVE,
    )
    summary = ProcessMiningService.get_summary(db, filters)
    assert summary.total_cases == 1
    assert summary.total_events == 1
    assert summary.data_quality.cases_without_creation_event == 1
    detail = ProcessMiningService.get_case_detail(db, case.id, filters)
    assert detail is not None
    assert [event.event_type for event in detail.events] == [
        ProcessEventType.INCIDENT_STATUS_CHANGED,
    ]


def test_same_timestamp_uses_case_sequence_and_zero_duration_is_valid(db: Session, admin_user: User):
    _add_incident_case(db, admin_user, 2050, [
        _created_incident_event(),
        {"type": ProcessEventType.TECHNICIAN_ASSIGNED, "seconds": 0, "target_user_id": admin_user.id},
    ])
    summary = ProcessMiningService.get_summary(db, _filters(2050))
    assert summary.first_action_time.count == 1
    assert summary.first_action_time.min == summary.first_action_time.max == 0
    edge = ProcessMiningService.get_observed_flow(db, _filters(2050))[0]
    assert edge.count == 1 and edge.median_duration == 0


def test_filter_schema_requires_timezone_and_exclusive_ordered_boundaries():
    with pytest.raises(ValidationError, match="timezone"):
        ProcessMiningFilters(date_from=datetime(2024, 1, 1))
    with pytest.raises(ValidationError, match="exclusive date_to"):
        ProcessMiningFilters(date_from=_stamp(2024), date_to=_stamp(2024))


def test_conformance_transition_table_matches_incident_route():
    from app.api.v1.incidents import VALID_TRANSITIONS

    assert {
        source.value: {target.value for target in targets}
        for source, targets in VALID_TRANSITIONS.items()
    } == INCIDENT_VALID_TRANSITIONS
