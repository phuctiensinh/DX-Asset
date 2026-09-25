import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import User
from app.models.technician_skill import TechnicianSkill
from app.models.enums import UserRole
from app.schemas.user import UserResponse, UserRoleUpdate
from app.schemas.technician_skill import (
    TechnicianSkillCreate,
    TechnicianSkillResponse,
    TechnicianProfileResponse,
)
from app.services.smart_routing import SmartRoutingService

logger = logging.getLogger(__name__)

router = APIRouter()

SYSTEM_OWNER_EMAIL = "2424801030008@student.tdmu.edu.vn"

@router.get("", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Lấy danh sách tất cả người dùng (Chỉ dành cho ADMIN)."""
    users = db.query(User).order_by(User.created_at.desc()).all()
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

@router.get("/{user_id}", response_model=UserResponse)
def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Xem chi tiết thông tin người dùng (Chỉ dành cho ADMIN)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy người dùng với ID {user_id}"
        )
    return user

@router.patch("/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int,
    role_in: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Cập nhật vai trò (Role) của người dùng (Chỉ dành cho ADMIN)."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy người dùng với ID {user_id}"
        )

    # Protection 1: Cannot demote or change role of System Owner
    if target_user.email == SYSTEM_OWNER_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không thể thay đổi role của System Owner (2424801030008@student.tdmu.edu.vn)"
        )

    # Protection 2: Cannot promote any user to ADMIN role
    if role_in.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không thể gán role ADMIN cho người dùng khác. Chỉ System Owner được giữ role ADMIN"
        )

    old_role = target_user.role
    if old_role != role_in.role:
        target_user.role = role_in.role
        db.commit()
        db.refresh(target_user)
        logger.info(
            f"ROLE_CHANGE_AUDIT: Admin '{current_user.email}' (ID {current_user.id}) "
            f"changed role of target user '{target_user.email}' (ID {target_user.id}) "
            f"from '{old_role}' to '{target_user.role}'"
        )

    return target_user

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
