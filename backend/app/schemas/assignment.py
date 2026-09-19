from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.models.enums import AssignmentStatus
from app.schemas.user import UserResponse
from app.schemas.asset import AssetResponse

class AssignmentBase(BaseModel):
    notes: Optional[str] = None

class AssignmentCreate(AssignmentBase):
    asset_id: int
    user_id: int  # assigned_to_user_id
    department_id: Optional[int] = None
    assigned_date: Optional[datetime] = None

class AssignmentReturn(AssignmentBase):
    notes: Optional[str] = None

class AssignmentTransfer(AssignmentBase):
    target_user_id: int
    department_id: Optional[int] = None

class AssignmentResponse(AssignmentBase):
    id: int
    asset_id: int
    assigned_to_user_id: int
    assigned_by_user_id: int
    assigned_date: datetime
    return_date: Optional[datetime] = None
    status: AssignmentStatus
    created_at: datetime

    asset: Optional[AssetResponse] = None
    assigned_to_user: Optional[UserResponse] = None
    assigned_by_user: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)

class AssignmentListResponse(BaseModel):
    items: List[AssignmentResponse]
    total: int
    skip: int
    limit: int
