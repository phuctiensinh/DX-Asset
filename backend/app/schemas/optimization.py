from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class AllocationRequest(BaseModel):
    department_id: int = Field(gt=0)
    asset_category: str = Field(min_length=1, max_length=50)
    requested_quantity: int = Field(gt=0, le=10000)
    location: Optional[str] = Field(default=None, max_length=100)
    brand: Optional[str] = Field(default=None, max_length=50)
    model: Optional[str] = Field(default=None, max_length=50)


class AllocationCandidate(BaseModel):
    asset_id: int
    asset_code: str
    name: str
    category: str
    brand: Optional[str]
    model: Optional[str]
    location: Optional[str]


class AllocationResponse(BaseModel):
    department_id: int
    asset_category: str
    requested_quantity: int
    available_quantity: int
    shortage_quantity: int
    enough: bool
    candidates: List[AllocationCandidate]
    assumptions: List[str]
    warnings: List[str]


class CapacityRequest(BaseModel):
    current_sla_days: float = Field(gt=0, le=3650)
    target_sla_days: float = Field(gt=0, le=3650)
    expected_incidents: int = Field(ge=0, le=1000000)
    incidents_per_technician_per_day: float = Field(gt=0, le=100000)
    current_technician_count: Optional[int] = Field(default=None, ge=0, le=100000)


class CapacityResponse(BaseModel):
    current_sla_days: float
    target_sla_days: float
    expected_incidents: int
    incidents_per_technician_per_day: float
    estimated_required_technicians: int
    current_technician_count: Optional[int]
    estimated_gap: Optional[int]
    assumptions: List[str]
    warnings: List[str]


class ReplacementSimulationRequest(BaseModel):
    quantity: int = Field(gt=0, le=1000000)
    unit_cost: float = Field(ge=0, le=1e15)
    useful_life_years: float = Field(gt=0, le=1000)
    simulation_horizon_years: int = Field(gt=0, le=1000)
    residual_value: Optional[float] = Field(default=None, ge=0, le=1e15)
    residual_value_rate: Optional[float] = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_residual(self):
        if self.residual_value is not None and self.residual_value_rate is not None:
            raise ValueError("Provide residual_value or residual_value_rate, not both")
        if self.residual_value is not None and self.residual_value > self.unit_cost:
            raise ValueError("residual_value cannot exceed unit_cost")
        return self


class BookValueYear(BaseModel):
    year: int
    depreciation_expense: float
    estimated_book_value: float


class ReplacementSimulationResponse(BaseModel):
    quantity: int
    unit_cost: float
    total_initial_cost: float
    useful_life_years: float
    simulation_horizon_years: int
    residual_value: float
    annual_depreciation: float
    estimated_book_value_by_year: List[BookValueYear]
    estimated_replacement_cost: float
    assumptions: List[str]
    warnings: List[str]


class ReplacementRecommendation(BaseModel):
    asset_id: int
    asset_code: str
    name: str
    category: str
    status: str
    replacement_recommendation_score: float
    priority_level: str
    risk_score: float
    health_score: float
    repair_cost: float
    incident_count: int
    maintenance_count: int
    repeated_failure: bool
    purchase_date: Optional[date]
    age_years: Optional[float]
    reasons: List[str]


class ReplacementRecommendationsResponse(BaseModel):
    items: List[ReplacementRecommendation]
    total: int
    limit: int
    offset: int
