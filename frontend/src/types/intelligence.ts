export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface ComponentScores {
  incident_score: number;
  cost_score: number;
  repeat_score: number;
  status_score: number;
  mttr_score: number;
}

export interface AssetHealthRiskScore {
  risk_score: number;
  health_score: number;
  risk_level: RiskLevel;
  warning_reasons: string[];
  component_scores: ComponentScores;
}

export interface AssetIntelligenceMetrics {
  incident_count: number;
  maintenance_count: number;
  total_repair_cost: number;
  avg_repair_cost: number;
  mttr_hours: number | null;
  downtime_hours: number;
  has_repeated_failure: boolean;
  repeated_categories: string[];
}

export interface AssetIntelligenceDetailResponse {
  asset_id: number;
  asset_code: string;
  asset_name: string;
  category: string;
  brand?: string | null;
  model?: string | null;
  status: string;
  location?: string | null;
  department_name?: string | null;
  metrics: AssetIntelligenceMetrics;
  health_risk: AssetHealthRiskScore;
}

export interface RiskMatrixItem {
  asset_id: number;
  asset_code: string;
  asset_name: string;
  category: string;
  status: string;
  department_name?: string | null;
  risk_score: number;
  health_score: number;
  risk_level: RiskLevel;
  warning_reasons: string[];
  incident_count: number;
  total_repair_cost: number;
}

export interface RiskMatrixResponse {
  items: RiskMatrixItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface IntelligenceSummaryResponse {
  total_assets_analyzed: number;
  assets_with_incidents: number;
  assets_in_maintenance: number;
  total_repair_cost: number;
  avg_mttr_hours: number | null;
  risk_distribution: Record<RiskLevel, number>;
  high_risk_count: number;
  critical_risk_count: number;
  total_warning_assets: number;
}

export interface TopFailureItem {
  asset_id: number;
  asset_code: string;
  asset_name: string;
  category: string;
  incident_count: number;
  top_category?: string | null;
}

export interface TopCostlyItem {
  asset_id: number;
  asset_code: string;
  asset_name: string;
  category: string;
  total_repair_cost: number;
  maintenance_count: number;
}
