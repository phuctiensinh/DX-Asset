from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from app.models.enums import MaintenanceStatus
from app.schemas.user import UserResponse
from app.schemas.asset import AssetResponse
from app.schemas.incident import IncidentResponse

class MaintenanceBase(BaseModel):
    title: str = Field(..., max_length=150)
    description: Optional[str] = None

class MaintenanceCreate(MaintenanceBase):
    asset_id: int
    incident_id: Optional[int] = None
    technician_id: Optional[int] = None
    repair_cost: Optional[float] = Field(default=0.00, ge=0)
    maintenance_code: Optional[str] = None

class MaintenanceUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    technician_id: Optional[int] = None
    repair_cost: Optional[float] = Field(None, ge=0)
    resolution_notes: Optional[str] = None
    status: Optional[MaintenanceStatus] = None

class MaintenanceStart(BaseModel):
    technician_id: Optional[int] = None
    notes: Optional[str] = None

class MaintenanceComplete(BaseModel):
    resolution_notes: Optional[str] = None
    repair_cost: Optional[float] = Field(None, ge=0)

class MaintenanceResponse(MaintenanceBase):
    id: int
    maintenance_code: str
    asset_id: int
    incident_id: Optional[int] = None
    technician_id: Optional[int] = None
    status: MaintenanceStatus
    start_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    repair_cost: float
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    asset: Optional[AssetResponse] = None
    incident: Optional[IncidentResponse] = None
    technician: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)

class MaintenanceListResponse(BaseModel):
    items: List[MaintenanceResponse]
    total: int
    skip: int
    limit: int
