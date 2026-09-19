from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from app.models.enums import IncidentCategory, IncidentPriority, IncidentStatus
from app.schemas.user import UserResponse
from app.schemas.asset import AssetResponse

class IncidentBase(BaseModel):
    title: str = Field(..., max_length=150)
    description: str
    category: IncidentCategory = IncidentCategory.HARDWARE
    priority: IncidentPriority = IncidentPriority.MEDIUM

class IncidentCreate(IncidentBase):
    asset_id: int
    ticket_code: Optional[str] = None

class IncidentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[IncidentCategory] = None
    priority: Optional[IncidentPriority] = None
    status: Optional[IncidentStatus] = None
    assigned_it_id: Optional[int] = None
    resolution_notes: Optional[str] = None
    repair_cost: Optional[float] = Field(None, ge=0)

class IncidentResponse(IncidentBase):
    id: int
    ticket_code: str
    asset_id: int
    reporter_id: int
    status: IncidentStatus
    assigned_it_id: Optional[int] = None
    resolution_notes: Optional[str] = None
    repair_cost: float
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    asset: Optional[AssetResponse] = None
    reporter: Optional[UserResponse] = None
    assigned_it: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)

class IncidentListResponse(BaseModel):
    items: List[IncidentResponse]
    total: int
    skip: int
    limit: int
