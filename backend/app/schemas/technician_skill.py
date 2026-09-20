from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from app.models.enums import IncidentCategory, UserRole

class TechnicianSkillBase(BaseModel):
    category: IncidentCategory
    skill_level: int = Field(3, ge=1, le=5)

class TechnicianSkillCreate(TechnicianSkillBase):
    pass

class TechnicianSkillResponse(TechnicianSkillBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)

class TechnicianProfileResponse(BaseModel):
    user_id: int
    full_name: str
    email: str
    role: UserRole
    active_workload: int
    active_incidents: int
    active_maintenances: int
    skills: List[TechnicianSkillResponse]

    model_config = ConfigDict(from_attributes=True)
