from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from decimal import Decimal
from app.models.enums import AssetStatus

class ComponentScores(BaseModel):
    incident_score: float = Field(..., description="Score from incident frequency (0-100)")
    cost_score: float = Field(..., description="Score from repair cost (0-100)")
    repeat_score: float = Field(..., description="Score from repeated failures (0 or 100)")
    status_score: float = Field(..., description="Score from asset operational status (0-100)")
    mttr_score: float = Field(..., description="Score from MTTR hours (0-100)")

class AssetHealthRiskScore(BaseModel):
    risk_score: float = Field(..., description="Analytical Risk Score 0-100")
    health_score: float = Field(..., description="Health Score 100 - Risk Score")
    risk_level: str = Field(..., description="LOW, MEDIUM, HIGH, or CRITICAL")
    warning_reasons: List[str] = Field(default_factory=list, description="Vietnamese warning reason explanations")
    component_scores: ComponentScores

class AssetIntelligenceMetrics(BaseModel):
    incident_count: int = Field(0, description="Total incident count")
    maintenance_count: int = Field(0, description="Total maintenance count")
    total_repair_cost: float = Field(0.0, description="Total repair cost without double counting")
    avg_repair_cost: float = Field(0.0, description="Average repair cost per event")
    mttr_hours: Optional[float] = Field(None, description="Mean Time To Repair in hours, null if no completed repairs")
    downtime_hours: float = Field(0.0, description="Total asset downtime in hours")
    has_repeated_failure: bool = Field(False, description="True if repeated failures in same category within 60 days")
    repeated_categories: List[str] = Field(default_factory=list, description="Categories with repeated failures")

class AssetIntelligenceDetailResponse(BaseModel):
    asset_id: int
    asset_code: str
    asset_name: str
    category: str
    brand: Optional[str] = None
    model: Optional[str] = None
    status: AssetStatus
    location: Optional[str] = None
    department_name: Optional[str] = None
    metrics: AssetIntelligenceMetrics
    health_risk: AssetHealthRiskScore

class RiskMatrixItem(BaseModel):
    asset_id: int
    asset_code: str
    asset_name: str
    category: str
    status: AssetStatus
    department_name: Optional[str] = None
    risk_score: float
    health_score: float
    risk_level: str
    warning_reasons: List[str]
    incident_count: int
    total_repair_cost: float

class IntelligenceSummaryResponse(BaseModel):
    total_assets_analyzed: int
    assets_with_incidents: int
    assets_in_maintenance: int
    total_repair_cost: float
    avg_mttr_hours: Optional[float] = None
    risk_distribution: Dict[str, int]
    high_risk_count: int
    critical_risk_count: int
    total_warning_assets: int

class TopFailureItem(BaseModel):
    asset_id: int
    asset_code: str
    asset_name: str
    category: str
    incident_count: int
    top_category: Optional[str] = None

class TopCostlyItem(BaseModel):
    asset_id: int
    asset_code: str
    asset_name: str
    category: str
    total_repair_cost: float
    maintenance_count: int
