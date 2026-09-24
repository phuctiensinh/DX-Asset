from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import (
    ProcessCaseType,
    ProcessEventSource,
    ProcessEventTimestampQuality,
    ProcessEventType,
)


class ProcessMiningFilters(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    case_type: Optional[ProcessCaseType] = None
    source: Optional[ProcessEventSource] = None

    @field_validator("date_from", "date_to")
    @classmethod
    def require_timezone_for_dates(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Process mining date filters must include a timezone")
        return value

    @model_validator(mode="after")
    def require_ordered_date_range(self):
        if self.date_from is not None and self.date_to is not None and self.date_from >= self.date_to:
            raise ValueError("date_from must be earlier than exclusive date_to")
        return self


class DurationStatistics(BaseModel):
    unit: Literal["seconds"] = "seconds"
    count: int = Field(ge=0)
    min: Optional[float] = None
    max: Optional[float] = None
    average: Optional[float] = None
    median: Optional[float] = None


class ProcessMiningCohort(BaseModel):
    source: Literal["ALL", "LIVE", "BACKFILL"]
    case_type: Optional[ProcessCaseType] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    total_cases: int = Field(ge=0)
    eventful_cases: int = Field(ge=0)
    coverage_note: str


class ProcessMiningDataQuality(BaseModel):
    total_cases: int = Field(ge=0)
    total_events: int = Field(ge=0)
    live_events: int = Field(ge=0)
    backfill_events: int = Field(ge=0)
    action_time_events: int = Field(ge=0)
    legacy_field_events: int = Field(ge=0)
    ambiguous_timestamp_events: int = Field(ge=0)
    cases_without_creation_event: int = Field(ge=0)
    cases_without_completion_event: int = Field(ge=0)
    incomplete_cases: int = Field(ge=0)
    live_case_count: int = Field(ge=0)
    backfill_case_count: int = Field(ge=0)
    cases_with_mixed_sources: int = Field(ge=0)
    cohort_note: str


class ObservedFlowEdge(BaseModel):
    from_event: ProcessEventType
    to_event: ProcessEventType
    count: int = Field(ge=0)
    median_duration: Optional[float] = None
    unit: Literal["seconds"] = "seconds"


class ProcessMiningSummary(BaseModel):
    cohort: ProcessMiningCohort
    total_cases: int = Field(ge=0)
    completed_cases: int = Field(ge=0)
    incomplete_cases: int = Field(ge=0)
    total_events: int = Field(ge=0)
    live_events: int = Field(ge=0)
    backfill_events: int = Field(ge=0)
    processing_time: DurationStatistics
    first_action_time: DurationStatistics
    maintenance_duration: DurationStatistics
    data_quality: ProcessMiningDataQuality
    observed_flow: list[ObservedFlowEdge] = Field(default_factory=list)


class ProcessVariant(BaseModel):
    variant_id: str
    event_sequence: list[ProcessEventType]
    case_count: int = Field(ge=0)
    percentage: float = Field(ge=0, le=100)


class ProcessVariantReport(BaseModel):
    cohort: ProcessMiningCohort
    denominator_cases: int = Field(ge=0)
    variants: list[ProcessVariant]


class ProcessBottleneck(BaseModel):
    from_event: ProcessEventType
    to_event: ProcessEventType
    count: int = Field(ge=0)
    min_duration: float
    max_duration: float
    average_duration: float
    median_duration: float
    unit: Literal["seconds"] = "seconds"


class ProcessReworkMetrics(BaseModel):
    source: ProcessEventSource
    total_rework_cases: int = Field(ge=0)
    total_rework_events: int = Field(ge=0)
    eligible_cases: int = Field(ge=0)
    denominator_description: str
    rework_rate: Optional[float] = Field(default=None, ge=0, le=1)


class ProcessDeviation(BaseModel):
    case_id: int
    event_id: int
    from_status: str
    to_status: str
    reason: str


class ProcessConformanceMetrics(BaseModel):
    eligible_cases: int = Field(ge=0)
    conforming_cases: int = Field(ge=0)
    deviating_cases: int = Field(ge=0)
    conformance_rate: Optional[float] = Field(default=None, ge=0, le=1)
    deviations: list[ProcessDeviation]
    note: str


class ProcessEventDetail(BaseModel):
    id: int
    event_type: ProcessEventType
    from_status: Optional[str]
    to_status: Optional[str]
    performed_by_id: Optional[int]
    target_user_id: Optional[int]
    occurred_at: datetime
    source: ProcessEventSource
    timestamp_quality: ProcessEventTimestampQuality
    sequence: int


class ProcessCaseDetail(BaseModel):
    case_id: int
    case_type: ProcessCaseType
    incident_id: Optional[int]
    maintenance_id: Optional[int]
    source_coverage: list[ProcessEventSource]
    events: list[ProcessEventDetail]
    processing_time: Optional[float]
    first_action_time: Optional[float]
    rework_events: int = Field(ge=0)
    conformance: ProcessConformanceMetrics
    unit: Literal["seconds"] = "seconds"


class ProcessMiningCaseListItem(BaseModel):
    case_id: int
    case_type: ProcessCaseType
    incident_id: Optional[int]
    maintenance_id: Optional[int]
    created_at: datetime
    event_count: int = Field(ge=0)
    source_coverage: list[ProcessEventSource]
    first_event_at: Optional[datetime]
    last_event_at: Optional[datetime]
    completed: bool
    processing_duration: Optional[float]
    unit: Literal["seconds"] = "seconds"


class ProcessMiningCasesResponse(BaseModel):
    items: list[ProcessMiningCaseListItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
