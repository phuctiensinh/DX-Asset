from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import User
from app.models.department import Department
from app.models.asset import Asset
from app.models.assignment import AssetAssignment
from app.models.history import AssetHistory
from app.models.enums import UserRole, AssetStatus, AssignmentStatus, AssetActionType
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentReturn,
    AssignmentTransfer,
    AssignmentResponse,
    AssignmentListResponse,
)

router = APIRouter()

def _get_assignment_query(db: Session):
    return db.query(AssetAssignment).options(
        joinedload(AssetAssignment.asset),
        joinedload(AssetAssignment.assigned_to_user),
        joinedload(AssetAssignment.assigned_by_user),
    )

@router.get("", response_model=AssignmentListResponse)
def list_assignments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_filter: Optional[AssignmentStatus] = Query(None, alias="status", description="Lọc theo trạng thái (ACTIVE/RETURNED)"),
    asset_id: Optional[int] = Query(None, description="Lọc theo ID tài sản"),
    user_id: Optional[int] = Query(None, description="Lọc theo ID người được cấp"),
    search: Optional[str] = Query(None, description="Tìm kiếm theo mã tài sản, tên tài sản hoặc tên người nhận"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy danh sách cấp phát tài sản với tìm kiếm, lọc và phân trang (Tất cả người dùng đã đăng nhập)."""
    query = _get_assignment_query(db)

    if status_filter:
        query = query.filter(AssetAssignment.status == status_filter)

    if asset_id:
        query = query.filter(AssetAssignment.asset_id == asset_id)

    if user_id:
        query = query.filter(AssetAssignment.assigned_to_user_id == user_id)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.join(AssetAssignment.asset).join(AssetAssignment.assigned_to_user).filter(
            or_(
                Asset.asset_code.ilike(term),
                Asset.name.ilike(term),
                User.full_name.ilike(term),
                User.email.ilike(term),
            )
        )

    total = query.count()
    items = query.order_by(AssetAssignment.id.desc()).offset(skip).limit(limit).all()

    return AssignmentListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )

@router.get("/{assignment_id}", response_model=AssignmentResponse)
def get_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy thông tin chi tiết một lượt cấp phát theo ID."""
    assignment = _get_assignment_query(db).filter(AssetAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy thông tin cấp phát với ID {assignment_id}"
        )
    return assignment

@router.post("", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(
    assignment_in: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.IT_ASSET_MANAGER)),
):
    """Cấp phát tài sản cho nhân viên (Chỉ dành cho ADMIN và IT_ASSET_MANAGER)."""
    # 1. Verify asset exists
    asset = db.query(Asset).filter(Asset.id == assignment_in.asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy tài sản với ID {assignment_in.asset_id}"
        )

    # 2. Verify target user exists
    target_user = db.query(User).filter(User.id == assignment_in.user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy người dùng với ID {assignment_in.user_id}"
        )

    # 3. Verify department exists if provided
    if assignment_in.department_id:
        dept = db.query(Department).filter(Department.id == assignment_in.department_id).first()
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy phòng ban với ID {assignment_in.department_id}"
            )

    # 4. Verify asset is not RETIRED or INACTIVE
    if asset.status in (AssetStatus.RETIRED, AssetStatus.INACTIVE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tài sản '{asset.asset_code}' đang ở trạng thái '{asset.status}', không thể cấp phát."
        )

    # 5. Verify asset has no existing ACTIVE assignment
    active_asm = db.query(AssetAssignment).filter(
        AssetAssignment.asset_id == asset.id,
        AssetAssignment.status == AssignmentStatus.ACTIVE
    ).first()
    if active_asm or asset.status == AssetStatus.ASSIGNED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tài sản '{asset.asset_code}' đã có lượt cấp phát đang hoạt động (ACTIVE)."
        )

    # 6. Create Assignment
    assigned_date = assignment_in.assigned_date or datetime.now(timezone.utc)
    assignment = AssetAssignment(
        asset_id=asset.id,
        assigned_to_user_id=target_user.id,
        assigned_by_user_id=current_user.id,
        assigned_date=assigned_date,
        status=AssignmentStatus.ACTIVE,
        notes=assignment_in.notes,
    )
    db.add(assignment)

    # 7. Update Asset state
    asset.status = AssetStatus.ASSIGNED
    asset.current_user_id = target_user.id
    if assignment_in.department_id:
        asset.department_id = assignment_in.department_id
    elif target_user.department_id:
        asset.department_id = target_user.department_id

    # 8. Record AssetHistory
    history_details = f"Tài sản {asset.asset_code} ({asset.name}) được cấp cho {target_user.full_name} ({target_user.email})"
    if assignment_in.notes:
        history_details += f" - Ghi chú: {assignment_in.notes}"

    history = AssetHistory(
        asset_id=asset.id,
        action_type=AssetActionType.ASSIGNED,
        performed_by_id=current_user.id,
        details=history_details,
    )
    db.add(history)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tài sản hoặc lượt cấp phát đã được cập nhật bởi một yêu cầu khác. Vui lòng tải lại dữ liệu và thử lại."
        )
    db.refresh(assignment)

    return _get_assignment_query(db).filter(AssetAssignment.id == assignment.id).first()

@router.patch("/{assignment_id}/return", response_model=AssignmentResponse)
def return_assignment(
    assignment_id: int,
    return_in: Optional[AssignmentReturn] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.IT_ASSET_MANAGER)),
):
    """Thu hồi tài sản từ lượt cấp phát đang ACTIVE (Chỉ dành cho ADMIN và IT_ASSET_MANAGER)."""
    assignment = db.query(AssetAssignment).filter(AssetAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy thông tin cấp phát với ID {assignment_id}"
        )

    if assignment.status != AssignmentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lượt cấp phát #{assignment_id} đã ở trạng thái '{assignment.status}', không thể thu hồi."
        )

    now_utc = datetime.now(timezone.utc)
    assignment.status = AssignmentStatus.RETURNED
    assignment.return_date = now_utc

    if return_in and return_in.notes:
        if assignment.notes:
            assignment.notes = f"{assignment.notes} | [Thu hồi]: {return_in.notes}"
        else:
            assignment.notes = f"[Thu hồi]: {return_in.notes}"

    # Update Asset status
    asset = db.query(Asset).filter(Asset.id == assignment.asset_id).first()
    if asset:
        asset.status = AssetStatus.IN_STOCK
        asset.current_user_id = None

    # Audit AssetHistory
    target_user = db.query(User).filter(User.id == assignment.assigned_to_user_id).first()
    user_info = f"{target_user.full_name} ({target_user.email})" if target_user else f"ID #{assignment.assigned_to_user_id}"
    asset_code_info = asset.asset_code if asset else f"Asset #{assignment.asset_id}"

    history_details = f"Thu hồi tài sản {asset_code_info} từ {user_info}"
    if return_in and return_in.notes:
        history_details += f" - Lý do/Ghi chú: {return_in.notes}"

    history = AssetHistory(
        asset_id=assignment.asset_id,
        action_type=AssetActionType.RETURNED,
        performed_by_id=current_user.id,
        details=history_details,
    )
    db.add(history)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lượt cấp phát hoặc tài sản đã được cập nhật bởi một yêu cầu khác. Vui lòng tải lại dữ liệu và thử lại."
        )
    db.refresh(assignment)

    return _get_assignment_query(db).filter(AssetAssignment.id == assignment_id).first()

@router.patch("/{assignment_id}/transfer", response_model=AssignmentResponse)
def transfer_assignment(
    assignment_id: int,
    transfer_in: AssignmentTransfer,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.IT_ASSET_MANAGER)),
):
    """Chuyển giao tài sản từ người dùng hiện tại sang người dùng mới (Chỉ dành cho ADMIN và IT_ASSET_MANAGER)."""
    old_assignment = db.query(AssetAssignment).filter(AssetAssignment.id == assignment_id).first()
    if not old_assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy thông tin cấp phát với ID {assignment_id}"
        )

    if old_assignment.status != AssignmentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lượt cấp phát #{assignment_id} không ở trạng thái ACTIVE để chuyển giao."
        )

    new_user = db.query(User).filter(User.id == transfer_in.target_user_id).first()
    if not new_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy người dùng nhận chuyển giao với ID {transfer_in.target_user_id}"
        )

    if old_assignment.assigned_to_user_id == new_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Người dùng nhận mới không thể trùng với người đang giữ tài sản hiện tại."
        )

    now_utc = datetime.now(timezone.utc)
    asset = db.query(Asset).filter(Asset.id == old_assignment.asset_id).first()
    old_user = db.query(User).filter(User.id == old_assignment.assigned_to_user_id).first()

    # 1. Close old assignment as RETURNED
    old_assignment.status = AssignmentStatus.RETURNED
    old_assignment.return_date = now_utc
    transfer_note = f"[Chuyển giao sang {new_user.full_name}]"
    old_assignment.notes = f"{old_assignment.notes} | {transfer_note}" if old_assignment.notes else transfer_note

    # Record RETURNED history for old assignment
    old_user_str = f"{old_user.full_name} ({old_user.email})" if old_user else f"ID #{old_assignment.assigned_to_user_id}"
    new_user_str = f"{new_user.full_name} ({new_user.email})"
    asset_code_str = asset.asset_code if asset else f"Asset #{old_assignment.asset_id}"

    history_return = AssetHistory(
        asset_id=old_assignment.asset_id,
        action_type=AssetActionType.RETURNED,
        performed_by_id=current_user.id,
        details=f"Thu hồi tài sản {asset_code_str} từ {old_user_str} để chuyển giao cho {new_user_str}",
    )
    db.add(history_return)

    # 2. Create new ACTIVE assignment
    new_assignment = AssetAssignment(
        asset_id=old_assignment.asset_id,
        assigned_to_user_id=new_user.id,
        assigned_by_user_id=current_user.id,
        assigned_date=now_utc,
        status=AssignmentStatus.ACTIVE,
        notes=transfer_in.notes or f"Chuyển giao từ {old_user_str}",
    )
    db.add(new_assignment)

    # 3. Update Asset state
    if asset:
        asset.status = AssetStatus.ASSIGNED
        asset.current_user_id = new_user.id
        if transfer_in.department_id:
            asset.department_id = transfer_in.department_id
        elif new_user.department_id:
            asset.department_id = new_user.department_id

    # Record ASSIGNED history for new assignment
    history_assign = AssetHistory(
        asset_id=old_assignment.asset_id,
        action_type=AssetActionType.ASSIGNED,
        performed_by_id=current_user.id,
        details=f"Cấp phát tài sản {asset_code_str} cho {new_user_str} (Nhận chuyển giao)",
    )
    db.add(history_assign)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Thao tác chuyển giao thất bại do xung đột dữ liệu hoặc tài sản đã được cập nhật bởi yêu cầu khác. Vui lòng tải lại dữ liệu và thử lại."
        )
    db.refresh(new_assignment)

    return _get_assignment_query(db).filter(AssetAssignment.id == new_assignment.id).first()
