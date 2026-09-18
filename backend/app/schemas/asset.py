from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date, datetime
from app.models.enums import AssetStatus
from app.schemas.user import UserResponse, DepartmentResponse

class AssetBase(BaseModel):
    asset_code: str
    name: str
    category: str
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    status: AssetStatus = AssetStatus.IN_STOCK
    purchase_date: Optional[date] = None
    warranty_expiry: Optional[date] = None
    current_user_id: Optional[int] = None
    department_id: Optional[int] = None
    location: Optional[str] = None
    description: Optional[str] = None
    qr_code_url: Optional[str] = None

class AssetCreate(AssetBase):
    pass

class AssetUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    status: Optional[AssetStatus] = None
    purchase_date: Optional[date] = None
    warranty_expiry: Optional[date] = None
    current_user_id: Optional[int] = None
    department_id: Optional[int] = None
    location: Optional[str] = None
    description: Optional[str] = None
    qr_code_url: Optional[str] = None

class AssetResponse(AssetBase):
    id: int
    created_at: datetime
    updated_at: datetime
    current_user: Optional[UserResponse] = None
    department: Optional[DepartmentResponse] = None

    model_config = ConfigDict(from_attributes=True)

class AssetListResponse(BaseModel):
    items: List[AssetResponse]
    total: int
    skip: int
    limit: int
