export type ProcessCaseType = 'INCIDENT' | 'MAINTENANCE';
export type ProcessEventSource = 'LIVE' | 'BACKFILL';
export type ProcessEventTimestampQuality = 'ACTION_TIME' | 'LEGACY_FIELD' | 'AMBIGUOUS';

export interface ProcessMiningFilters {
  date_from?: string;
  date_to?: string;
  case_type?: ProcessCaseType;
  source?: ProcessEventSource;
}

export interface ProcessMiningCohort {
  source: 'ALL' | ProcessEventSource;
  case_type: ProcessCaseType | null;
  date_from: string | null;
  date_to: string | null;
  total_cases: number;
  eventful_cases: number;
  coverage_note: string;
}

export interface ProcessMiningDurationStatistics {
  unit: 'seconds';
  count: number;
  min: number | null;
  max: number | null;
  average: number | null;
  median: number | null;
}

export interface ProcessMiningDataQuality {
  total_cases: number;
  total_events: number;
  live_events: number;
  backfill_events: number;
  action_time_events: number;
  legacy_field_events: number;
  ambiguous_timestamp_events: number;
  cases_without_creation_event: number;
  cases_without_completion_event: number;
  incomplete_cases: number;
  live_case_count: number;
  backfill_case_count: number;
  cases_with_mixed_sources: number;
  cohort_note: string;
}

export interface ProcessMiningObservedFlowEdge {
  from_event: string;
  to_event: string;
  count: number;
  median_duration: number | null;
  unit: 'seconds';
}

export interface ProcessMiningSummary {
  cohort: ProcessMiningCohort;
  total_cases: number;
  completed_cases: number;
  incomplete_cases: number;
  total_events: number;
  live_events: number;
  backfill_events: number;
  processing_time: ProcessMiningDurationStatistics;
  first_action_time: ProcessMiningDurationStatistics;
  maintenance_duration: ProcessMiningDurationStatistics;
  data_quality: ProcessMiningDataQuality;
  observed_flow: ProcessMiningObservedFlowEdge[];
}

export interface ProcessMiningVariant {
  variant_id: string;
  event_sequence: string[];
  case_count: number;
  percentage: number;
}

export interface ProcessMiningVariants {
  cohort: ProcessMiningCohort;
  denominator_cases: number;
  variants: ProcessMiningVariant[];
}

export interface ProcessMiningBottleneck {
  from_event: string;
  to_event: string;
  count: number;
  min_duration: number;
  max_duration: number;
  average_duration: number;
  median_duration: number;
  unit: 'seconds';
}

export interface ProcessMiningCaseListItem {
  case_id: number;
  case_type: ProcessCaseType;
  incident_id: number | null;
  maintenance_id: number | null;
  created_at: string;
  event_count: number;
  source_coverage: ProcessEventSource[];
  first_event_at: string | null;
  last_event_at: string | null;
  completed: boolean;
  processing_duration: number | null;
  unit: 'seconds';
}

export interface ProcessMiningCases {
  items: ProcessMiningCaseListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface ProcessMiningEvent {
  id: number;
  event_type: string;
  from_status: string | null;
  to_status: string | null;
  performed_by_id: number | null;
  target_user_id: number | null;
  occurred_at: string;
  source: ProcessEventSource;
  timestamp_quality: ProcessEventTimestampQuality;
  sequence: number;
}

export interface ProcessMiningConformance {
  eligible_cases: number;
  conforming_cases: number;
  deviating_cases: number;
  conformance_rate: number | null;
  deviations: { case_id: number; event_id: number; from_status: string; to_status: string; reason: string }[];
  note: string;
}

export interface ProcessMiningCaseDetail {
  case_id: number;
  case_type: ProcessCaseType;
  incident_id: number | null;
  maintenance_id: number | null;
  source_coverage: ProcessEventSource[];
  events: ProcessMiningEvent[];
  processing_time: number | null;
  first_action_time: number | null;
  rework_events: number;
  conformance: ProcessMiningConformance;
  unit: 'seconds';
}
