from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from app.models.enums import IncidentCategory, IncidentPriority, UserRole

class ClassificationResponse(BaseModel):
    category: IncidentCategory
    suggested_queue: str
    ai_confidence: float
    ai_reasoning: str

    model_config = ConfigDict(from_attributes=True)

class TechnicianRecommendationItem(BaseModel):
    user_id: int
    full_name: str
    email: str
    role: UserRole
    total_score: float
    skill_score: float
    workload_score: float
    sla_score: float
    active_workload: int
    reasons: List[str]

    model_config = ConfigDict(from_attributes=True)

class RecommendationsResponse(BaseModel):
    incident_id: int
    ticket_code: str
    category: IncidentCategory
    priority: IncidentPriority
    suggested_queue: str
    recommendations: List[TechnicianRecommendationItem]

class AssignIncidentRequest(BaseModel):
    technician_id: int
    notes: Optional[str] = None
