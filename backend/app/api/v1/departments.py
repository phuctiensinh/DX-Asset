from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.department import Department
from app.schemas.user import DepartmentResponse

router = APIRouter()

@router.get("", response_model=List[DepartmentResponse])
def list_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy danh sách phòng ban cho dropdown chọn lựa."""
    departments = db.query(Department).order_by(Department.name.asc()).all()
    return departments
