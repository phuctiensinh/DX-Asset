from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.enums import AssetActionType

class AssetStatusCounts(BaseModel):
    total: int
    by_status: Dict[str, int]
    in_stock: int
    assigned: int
    in_maintenance: int
    damaged: int
    retired: int
    lost: int
    inactive: int

class AssignmentStatusCounts(BaseModel):
    total: int
    by_status: Dict[str, int]
    active: int
    returned: int

class IncidentStatusCounts(BaseModel):
    total: int
    by_status: Dict[str, int]
    open: int
    in_review: int
    in_progress: int
    waiting_for_info: int
    resolved: int
    closed: int
    cancelled: int
    pending: int

class DepartmentAssetStats(BaseModel):
    department_id: Optional[int] = None
    department_code: str
    department_name: str
    total_assets: int
    assigned_assets: int
    in_stock_assets: int

class RecentActivityItem(BaseModel):
    id: int
    asset_id: int
    asset_code: str
    asset_name: str
    action_type: AssetActionType
    performed_by_id: Optional[int] = None
    performed_by_name: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DashboardSummaryResponse(BaseModel):
    assets: AssetStatusCounts
    assignments: AssignmentStatusCounts
    incidents: IncidentStatusCounts
    departments: List[DepartmentAssetStats]
    recent_activities: List[RecentActivityItem]
