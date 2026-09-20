from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import User
from app.models.technician_skill import TechnicianSkill
from app.models.enums import UserRole, IncidentCategory
from app.schemas.user import UserResponse
from app.schemas.technician_skill import (
    TechnicianSkillCreate,
    TechnicianSkillResponse,
    TechnicianProfileResponse,
)
from app.services.smart_routing import SmartRoutingService

router = APIRouter()

@router.get("", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy danh sách người dùng để phục vụ các form chọn nhân viên (Tất cả người dùng đã đăng nhập)."""
    users = db.query(User).filter(User.is_active == True).order_by(User.full_name.asc()).all()
    return users

@router.get("/technicians/skills", response_model=List[TechnicianProfileResponse])
def get_technicians_skills(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.IT_ASSET_MANAGER)),
):
    """Lấy danh sách Kỹ thuật viên kèm kỹ năng và workload active (ADMIN & IT_ASSET_MANAGER)."""
    tech_users = db.query(User).filter(
        User.role.in_([UserRole.ADMIN, UserRole.IT_ASSET_MANAGER]),
        User.is_active == True
    ).order_by(User.full_name.asc()).all()

    profiles: List[TechnicianProfileResponse] = []
    for u in tech_users:
        active_inc, active_mnt, total_w = SmartRoutingService.calculate_technician_workload(db, u.id)
        skills = db.query(TechnicianSkill).filter(TechnicianSkill.user_id == u.id).all()
        profiles.append(TechnicianProfileResponse(
            user_id=u.id,
            full_name=u.full_name,
            email=u.email,
            role=u.role,
            active_workload=total_w,
            active_incidents=active_inc,
            active_maintenances=active_mnt,
            skills=skills,
        ))

    return profiles

@router.post("/{user_id}/skills", response_model=TechnicianSkillResponse)
def set_technician_skill(
    user_id: int,
    skill_in: TechnicianSkillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.IT_ASSET_MANAGER)),
):
    """Thiết lập / Cập nhật điểm kỹ năng cho Kỹ thuật viên (ADMIN & IT_ASSET_MANAGER)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy người dùng với ID {user_id}"
        )

    if user.role not in (UserRole.ADMIN, UserRole.IT_ASSET_MANAGER):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Người dùng '{user.full_name}' ({user.role}) không phải là Kỹ thuật viên / IT Manager."
        )

    skill = db.query(TechnicianSkill).filter(
        TechnicianSkill.user_id == user.id,
        TechnicianSkill.category == skill_in.category
    ).first()

    if skill:
        skill.skill_level = skill_in.skill_level
    else:
        skill = TechnicianSkill(
            user_id=user.id,
            category=skill_in.category,
            skill_level=skill_in.skill_level,
        )
        db.add(skill)

    db.commit()
    db.refresh(skill)
    return skill
