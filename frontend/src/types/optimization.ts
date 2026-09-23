export interface AllocationRequest {
  department_id: number; asset_category: string; requested_quantity: number;
  location?: string; brand?: string; model?: string;
}
export interface AllocationResponse {
  department_id: number; asset_category: string; requested_quantity: number;
  available_quantity: number; shortage_quantity: number; enough: boolean;
  candidates: { asset_id: number; asset_code: string; name: string; category: string; brand?: string | null; model?: string | null; location?: string | null }[];
  assumptions: string[]; warnings: string[];
}
export interface CapacityRequest {
  current_sla_days: number; target_sla_days: number; expected_incidents: number;
  incidents_per_technician_per_day: number; current_technician_count?: number;
}
export interface CapacityResponse {
  current_sla_days: number; target_sla_days: number; expected_incidents: number;
  incidents_per_technician_per_day: number; estimated_required_technicians: number;
  current_technician_count?: number | null; estimated_gap?: number | null; assumptions: string[]; warnings: string[];
}
export interface ReplacementSimulationRequest {
  quantity: number; unit_cost: number; useful_life_years: number; simulation_horizon_years: number;
  residual_value?: number; residual_value_rate?: number;
}
export interface ReplacementSimulationResponse {
  quantity: number; unit_cost: number; total_initial_cost: number; useful_life_years: number;
  simulation_horizon_years: number; residual_value: number; annual_depreciation: number;
  estimated_book_value_by_year: { year: number; depreciation_expense: number; estimated_book_value: number }[];
  estimated_replacement_cost: number; assumptions: string[]; warnings: string[];
}
export interface ReplacementRecommendation {
  asset_id: number; asset_code: string; name: string; category: string; status: string;
  replacement_recommendation_score: number; priority_level: string; risk_score: number; health_score: number;
  repair_cost: number; incident_count: number; maintenance_count: number; repeated_failure: boolean;
  purchase_date?: string | null; age_years?: number | null; reasons: string[];
}
export interface ReplacementRecommendationsResponse { items: ReplacementRecommendation[]; total: number; limit: number; offset: number }
