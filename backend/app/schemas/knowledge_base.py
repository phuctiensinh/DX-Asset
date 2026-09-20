from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from app.models.enums import IncidentCategory, IncidentPriority, IncidentStatus

class LinkedMaintenanceInfo(BaseModel):
    maintenance_code: str
    status: str
    repair_cost: float
    duration_hours: Optional[float] = None
    resolution_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class SimilarIncidentItem(BaseModel):
    incident_id: int
    ticket_code: str
    title: str
    category: IncidentCategory
    priority: IncidentPriority
    status: IncidentStatus
    resolution_notes: str
    repair_cost: float
    resolved_at: Optional[datetime] = None
    asset_code: Optional[str] = None
    asset_name: Optional[str] = None
    similarity_score: float
    similarity_reasons: List[str]
    linked_maintenance: Optional[LinkedMaintenanceInfo] = None

    model_config = ConfigDict(from_attributes=True)

class SimilarIncidentListResponse(BaseModel):
    target_incident_id: int
    target_ticket_code: str
    total_found: int
    items: List[SimilarIncidentItem]
