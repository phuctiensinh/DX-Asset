from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter()

@router.get("", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy danh sách người dùng để phục vụ các form chọn nhân viên (Tất cả người dùng đã đăng nhập)."""
    users = db.query(User).filter(User.is_active == True).order_by(User.full_name.asc()).all()
    return users
