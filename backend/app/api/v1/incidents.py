import uuid
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import User
from app.models.asset import Asset
from app.models.incident import Incident
from app.models.history import AssetHistory
from app.models.enums import UserRole, AssetStatus, IncidentCategory, IncidentPriority, IncidentStatus, AssetActionType
from app.schemas.incident import (
    IncidentCreate,
    IncidentUpdate,
    IncidentResponse,
    IncidentListResponse,
)

router = APIRouter()

VALID_TRANSITIONS = {
    IncidentStatus.OPEN: {
        IncidentStatus.OPEN,
        IncidentStatus.IN_REVIEW,
        IncidentStatus.IN_PROGRESS,
        IncidentStatus.CANCELLED,
    },
    IncidentStatus.IN_REVIEW: {
        IncidentStatus.IN_REVIEW,
        IncidentStatus.IN_PROGRESS,
        IncidentStatus.WAITING_FOR_INFO,
        IncidentStatus.RESOLVED,
        IncidentStatus.CANCELLED,
    },
    IncidentStatus.IN_PROGRESS: {
        IncidentStatus.IN_PROGRESS,
        IncidentStatus.WAITING_FOR_INFO,
        IncidentStatus.RESOLVED,
        IncidentStatus.CANCELLED,
    },
    IncidentStatus.WAITING_FOR_INFO: {
        IncidentStatus.WAITING_FOR_INFO,
        IncidentStatus.IN_PROGRESS,
        IncidentStatus.RESOLVED,
        IncidentStatus.CANCELLED,
    },
    IncidentStatus.RESOLVED: {
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED,
        IncidentStatus.IN_PROGRESS,
    },
    IncidentStatus.CLOSED: {IncidentStatus.CLOSED},
    IncidentStatus.CANCELLED: {IncidentStatus.CANCELLED},
}

def _get_incident_query(db: Session):
    return db.query(Incident).options(
        joinedload(Incident.asset),
        joinedload(Incident.reporter),
        joinedload(Incident.assigned_it),
    )

@router.get("", response_model=IncidentListResponse)
def list_incidents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_filter: Optional[IncidentStatus] = Query(None, alias="status", description="Lọc theo trạng thái phiếu"),
    priority_filter: Optional[IncidentPriority] = Query(None, alias="priority", description="Lọc theo độ ưu tiên"),
    category_filter: Optional[IncidentCategory] = Query(None, alias="category", description="Lọc theo phân loại sự cố"),
    asset_id: Optional[int] = Query(None, description="Lọc theo ID tài sản"),
    reporter_id: Optional[int] = Query(None, description="Lọc theo ID người báo cáo"),
    search: Optional[str] = Query(None, description="Tìm kiếm mã phiếu, tiêu đề, mã TS hoặc người báo cáo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy danh sách phiếu báo hỏng sự cố (Tất cả người dùng đã đăng nhập)."""
    query = _get_incident_query(db)

    if status_filter:
        query = query.filter(Incident.status == status_filter)

    if priority_filter:
        query = query.filter(Incident.priority == priority_filter)

    if category_filter:
        query = query.filter(Incident.category == category_filter)

    if asset_id:
        query = query.filter(Incident.asset_id == asset_id)

    if reporter_id:
        query = query.filter(Incident.reporter_id == reporter_id)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.join(Incident.asset).join(Incident.reporter).filter(
            or_(
                Incident.ticket_code.ilike(term),
                Incident.title.ilike(term),
                Incident.description.ilike(term),
                Asset.asset_code.ilike(term),
                Asset.name.ilike(term),
                User.full_name.ilike(term),
            )
        )

    total = query.count()
    items = query.order_by(Incident.id.desc()).offset(skip).limit(limit).all()

    return IncidentListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )

@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy thông tin chi tiết một phiếu báo hỏng theo ID."""
    incident = _get_incident_query(db).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy phiếu báo hỏng với ID {incident_id}"
        )
    return incident

@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
def create_incident(
    incident_in: IncidentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Gửi báo cáo sự cố tài sản mới (Tất cả người dùng đã đăng nhập)."""
    # 1. Verify asset exists
    asset = db.query(Asset).filter(Asset.id == incident_in.asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy tài sản với ID {incident_in.asset_id}"
        )

    # 2. Verify asset is not RETIRED or INACTIVE
    if asset.status in (AssetStatus.RETIRED, AssetStatus.INACTIVE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tài sản '{asset.asset_code}' đang ở trạng thái '{asset.status}', không thể gửi báo hỏng."
        )

    # 3. Generate or verify unique ticket code
    if incident_in.ticket_code:
        ticket_code = incident_in.ticket_code.strip()
        existing = db.query(Incident).filter(Incident.ticket_code == ticket_code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã phiếu sự cố '{ticket_code}' đã tồn tại trong hệ thống."
            )
    else:
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        ticket_code = f"INC-{date_str}-{uuid.uuid4().hex[:4].upper()}"

    # 4. Create Incident
    incident = Incident(
        ticket_code=ticket_code,
        asset_id=asset.id,
        reporter_id=current_user.id,
        title=incident_in.title.strip(),
        description=incident_in.description.strip(),
        category=incident_in.category,
        priority=incident_in.priority,
        status=IncidentStatus.OPEN,
    )
    db.add(incident)

    # 5. Audit AssetHistory
    history = AssetHistory(
        asset_id=asset.id,
        action_type=AssetActionType.INCIDENT_REPORTED,
        performed_by_id=current_user.id,
        details=f"Gửi phiếu báo hỏng [{ticket_code}]: {incident.title}",
    )
    db.add(history)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mã phiếu sự cố hoặc dữ liệu bị xung đột với một yêu cầu khác. Vui lòng thử lại."
        )
    db.refresh(incident)

    return _get_incident_query(db).filter(Incident.id == incident.id).first()

@router.patch("/{incident_id}", response_model=IncidentResponse)
def update_incident(
    incident_id: int,
    incident_in: IncidentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.IT_ASSET_MANAGER)),
):
    """Cập nhật tiến độ / xử lý phiếu báo hỏng (Chỉ dành cho ADMIN và IT_ASSET_MANAGER)."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy phiếu báo hỏng với ID {incident_id}"
        )

    update_data = incident_in.model_dump(exclude_unset=True)

    # Validate status transition if status is being updated
    if "status" in update_data and update_data["status"] != incident.status:
        new_status = update_data["status"]
        allowed = VALID_TRANSITIONS.get(incident.status, {incident.status})
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Không thể chuyển trạng thái phiếu từ '{incident.status}' sang '{new_status}'."
            )

    # Verify assigned_it_id if provided
    if "assigned_it_id" in update_data and update_data["assigned_it_id"] is not None:
        it_user = db.query(User).filter(User.id == update_data["assigned_it_id"]).first()
        if not it_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy cán bộ IT với ID {update_data['assigned_it_id']}"
            )

    old_status = incident.status
    status_changed = "status" in update_data and update_data["status"] != old_status

    for field, value in update_data.items():
        setattr(incident, field, value)

    # Automatically set resolved_at if status becomes RESOLVED or CLOSED
    if incident.status in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED) and not incident.resolved_at:
        incident.resolved_at = datetime.now(timezone.utc)

    # Audit AssetHistory
    history_details = f"Cập nhật phiếu [{incident.ticket_code}]"
    if status_changed:
        history_details += f": Trạng thái từ '{old_status}' sang '{incident.status}'"
    if incident_in.resolution_notes:
        history_details += f" - Ghi chú xử lý: {incident_in.resolution_notes}"

    history = AssetHistory(
        asset_id=incident.asset_id,
        action_type=AssetActionType.MAINTENANCE_UPDATED,
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
            detail="Cập nhật phiếu thất bại do xung đột dữ liệu. Vui lòng tải lại dữ liệu và thử lại."
        )
    db.refresh(incident)

    return _get_incident_query(db).filter(Incident.id == incident.id).first()
