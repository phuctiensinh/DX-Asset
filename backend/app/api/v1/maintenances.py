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
from app.models.maintenance import Maintenance
from app.models.history import AssetHistory
from app.models.assignment import AssetAssignment
from app.models.enums import (
    UserRole,
    AssetStatus,
    AssignmentStatus,
    MaintenanceStatus,
    IncidentStatus,
    AssetActionType,
)
from app.schemas.maintenance import (
    MaintenanceCreate,
    MaintenanceUpdate,
    MaintenanceStart,
    MaintenanceComplete,
    MaintenanceResponse,
    MaintenanceListResponse,
)

router = APIRouter()

def _get_maintenance_query(db: Session):
    return db.query(Maintenance).options(
        joinedload(Maintenance.asset),
        joinedload(Maintenance.incident),
        joinedload(Maintenance.technician),
    )

@router.get("", response_model=MaintenanceListResponse)
def list_maintenances(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_filter: Optional[MaintenanceStatus] = Query(None, alias="status", description="Lọc theo trạng thái bảo trì"),
    asset_id: Optional[int] = Query(None, description="Lọc theo ID tài sản"),
    incident_id: Optional[int] = Query(None, description="Lọc theo ID sự cố"),
    technician_id: Optional[int] = Query(None, description="Lọc theo kỹ thuật viên"),
    search: Optional[str] = Query(None, description="Tìm kiếm mã bảo trì, tiêu đề, mã TS hoặc kỹ thuật viên"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy danh sách các đợt bảo trì (Tất cả người dùng đã đăng nhập)."""
    query = _get_maintenance_query(db)

    if status_filter:
        query = query.filter(Maintenance.status == status_filter)

    if asset_id:
        query = query.filter(Maintenance.asset_id == asset_id)

    if incident_id:
        query = query.filter(Maintenance.incident_id == incident_id)

    if technician_id:
        query = query.filter(Maintenance.technician_id == technician_id)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.join(Maintenance.asset).outerjoin(Maintenance.technician).filter(
            or_(
                Maintenance.maintenance_code.ilike(term),
                Maintenance.title.ilike(term),
                Maintenance.description.ilike(term),
                Asset.asset_code.ilike(term),
                Asset.name.ilike(term),
                User.full_name.ilike(term),
            )
        )

    total = query.count()
    items = query.order_by(Maintenance.id.desc()).offset(skip).limit(limit).all()

    return MaintenanceListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )

@router.get("/{maintenance_id}", response_model=MaintenanceResponse)
def get_maintenance(
    maintenance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy thông tin chi tiết đợt bảo trì theo ID."""
    maintenance = _get_maintenance_query(db).filter(Maintenance.id == maintenance_id).first()
    if not maintenance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy phiếu bảo trì với ID {maintenance_id}"
        )
    return maintenance

@router.post("", response_model=MaintenanceResponse, status_code=status.HTTP_201_CREATED)
def create_maintenance(
    maintenance_in: MaintenanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.IT_ASSET_MANAGER)),
):
    """Tạo phiếu bảo trì mới (Chỉ dành cho ADMIN và IT_ASSET_MANAGER)."""
    # 1. Verify asset
    asset = db.query(Asset).filter(Asset.id == maintenance_in.asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy tài sản với ID {maintenance_in.asset_id}"
        )

    if asset.status in (AssetStatus.RETIRED, AssetStatus.LOST, AssetStatus.INACTIVE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tài sản '{asset.asset_code}' đang ở trạng thái '{asset.status}', không thể đưa vào bảo trì."
        )

    # 2. Verify incident if provided
    if maintenance_in.incident_id:
        incident = db.query(Incident).filter(Incident.id == maintenance_in.incident_id).first()
        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy phiếu sự cố với ID {maintenance_in.incident_id}"
            )
        if incident.asset_id != asset.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Phiếu sự cố '{incident.ticket_code}' thuộc tài sản ID {incident.asset_id}, không khớp với tài sản ID {asset.id}."
            )

    # 3. Verify technician if provided
    if maintenance_in.technician_id:
        tech = db.query(User).filter(User.id == maintenance_in.technician_id).first()
        if not tech:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy kỹ thuật viên với ID {maintenance_in.technician_id}"
            )

    # 4. Maintenance code
    if maintenance_in.maintenance_code:
        mnt_code = maintenance_in.maintenance_code.strip()
        existing = db.query(Maintenance).filter(Maintenance.maintenance_code == mnt_code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã phiếu bảo trì '{mnt_code}' đã tồn tại."
            )
    else:
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        mnt_code = f"MNT-{date_str}-{uuid.uuid4().hex[:4].upper()}"

    tech_id = maintenance_in.technician_id if maintenance_in.technician_id else current_user.id

    maintenance = Maintenance(
        maintenance_code=mnt_code,
        asset_id=asset.id,
        incident_id=maintenance_in.incident_id,
        technician_id=tech_id,
        status=MaintenanceStatus.SCHEDULED,
        title=maintenance_in.title.strip(),
        description=maintenance_in.description.strip() if maintenance_in.description else None,
        repair_cost=maintenance_in.repair_cost or 0.00,
    )
    db.add(maintenance)

    # Record history
    history = AssetHistory(
        asset_id=asset.id,
        action_type=AssetActionType.MAINTENANCE_UPDATED,
        performed_by_id=current_user.id,
        details=f"Lên kế hoạch bảo trì [{mnt_code}]: {maintenance.title}",
    )
    db.add(history)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tạo phiếu bảo trì thất bại do xung đột dữ liệu."
        )
    db.refresh(maintenance)

    return _get_maintenance_query(db).filter(Maintenance.id == maintenance.id).first()

@router.patch("/{maintenance_id}/start", response_model=MaintenanceResponse)
def start_maintenance(
    maintenance_id: int,
    start_in: Optional[MaintenanceStart] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.IT_ASSET_MANAGER)),
):
    """Bắt đầu thực hiện bảo trì tài sản (Chuyển Maintenance -> IN_PROGRESS, Asset -> IN_MAINTENANCE)."""
    maintenance = db.query(Maintenance).filter(Maintenance.id == maintenance_id).first()
    if not maintenance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy phiếu bảo trì với ID {maintenance_id}"
        )

    if maintenance.status == MaintenanceStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phiếu bảo trì này đã hoàn thành, không thể bắt đầu lại."
        )
    if maintenance.status == MaintenanceStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phiếu bảo trì này đã bị hủy, không thể bắt đầu."
        )

    asset = db.query(Asset).filter(Asset.id == maintenance.asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tài sản liên quan đến phiếu bảo trì này."
        )

    if asset.status in (AssetStatus.RETIRED, AssetStatus.LOST, AssetStatus.INACTIVE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tài sản '{asset.asset_code}' đang ở trạng thái '{asset.status}', không thể đưa vào bảo trì."
        )

    # 1. Update maintenance status & start_date
    maintenance.status = MaintenanceStatus.IN_PROGRESS
    if not maintenance.start_date:
        maintenance.start_date = datetime.now(timezone.utc)

    if start_in:
        if start_in.technician_id:
            tech = db.query(User).filter(User.id == start_in.technician_id).first()
            if not tech:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Không tìm thấy kỹ thuật viên với ID {start_in.technician_id}"
                )
            maintenance.technician_id = start_in.technician_id

    if not maintenance.technician_id:
        maintenance.technician_id = current_user.id

    # 2. Update asset status to IN_MAINTENANCE (keep current_user_id & department_id)
    old_asset_status = asset.status
    asset.status = AssetStatus.IN_MAINTENANCE

    # If linked to Incident, update Incident status to IN_PROGRESS if OPEN/IN_REVIEW
    if maintenance.incident_id:
        incident = db.query(Incident).filter(Incident.id == maintenance.incident_id).first()
        if incident and incident.status in (IncidentStatus.OPEN, IncidentStatus.IN_REVIEW):
            incident.status = IncidentStatus.IN_PROGRESS

    # 3. Audit AssetHistory
    history = AssetHistory(
        asset_id=asset.id,
        action_type=AssetActionType.MAINTENANCE_STARTED,
        performed_by_id=current_user.id,
        details=f"Bắt đầu bảo trì [{maintenance.maintenance_code}]. Trạng thái tài sản '{old_asset_status}' -> '{asset.status}'",
    )
    db.add(history)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lỗi giao dịch khi bắt đầu bảo trì."
        )
    db.refresh(maintenance)

    return _get_maintenance_query(db).filter(Maintenance.id == maintenance.id).first()

@router.patch("/{maintenance_id}/complete", response_model=MaintenanceResponse)
def complete_maintenance(
    maintenance_id: int,
    complete_in: Optional[MaintenanceComplete] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.IT_ASSET_MANAGER)),
):
    """Hoàn thành bảo trì (Chuyển Maintenance -> COMPLETED, Asset -> ASSIGNED hoặc IN_STOCK)."""
    maintenance = db.query(Maintenance).filter(Maintenance.id == maintenance_id).first()
    if not maintenance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy phiếu bảo trì với ID {maintenance_id}"
        )

    if maintenance.status == MaintenanceStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phiếu bảo trì này đã hoàn thành trước đó."
        )
    if maintenance.status == MaintenanceStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phiếu bảo trì này đã bị hủy."
        )

    asset = db.query(Asset).filter(Asset.id == maintenance.asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tài sản liên quan đến phiếu bảo trì này."
        )

    # 1. Update maintenance status, completed_date, details
    maintenance.status = MaintenanceStatus.COMPLETED
    maintenance.completed_date = datetime.now(timezone.utc)
    if not maintenance.start_date:
        maintenance.start_date = maintenance.created_at

    if complete_in:
        if complete_in.resolution_notes is not None:
            maintenance.resolution_notes = complete_in.resolution_notes.strip()
        if complete_in.repair_cost is not None:
            maintenance.repair_cost = complete_in.repair_cost

    # 2. Revert Asset status based on active assignment / current holder
    has_active_assignment = False
    if asset.current_user_id is not None:
        has_active_assignment = True
    else:
        active_assignment = db.query(AssetAssignment).filter(
            AssetAssignment.asset_id == asset.id,
            AssetAssignment.status == AssignmentStatus.ACTIVE
        ).first()
        if active_assignment:
            has_active_assignment = True

    if has_active_assignment:
        asset.status = AssetStatus.ASSIGNED
    else:
        asset.status = AssetStatus.IN_STOCK

    # 3. If linked to an incident, update incident repair cost & optional resolution
    if maintenance.incident_id:
        incident = db.query(Incident).filter(Incident.id == maintenance.incident_id).first()
        if incident:
            incident.repair_cost = maintenance.repair_cost
            if maintenance.resolution_notes:
                if incident.resolution_notes:
                    incident.resolution_notes += f"\n[Bảo trì {maintenance.maintenance_code}]: {maintenance.resolution_notes}"
                else:
                    incident.resolution_notes = f"[Bảo trì {maintenance.maintenance_code}]: {maintenance.resolution_notes}"

    # 4. Audit AssetHistory
    history = AssetHistory(
        asset_id=asset.id,
        action_type=AssetActionType.MAINTENANCE_COMPLETED,
        performed_by_id=current_user.id,
        details=f"Hoàn thành bảo trì [{maintenance.maintenance_code}]. Trạng thái tài sản khôi phục về '{asset.status}'. Chi phí: {float(maintenance.repair_cost):,.0f} VNĐ",
    )
    db.add(history)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lỗi giao dịch khi hoàn thành bảo trì."
        )
    db.refresh(maintenance)

    return _get_maintenance_query(db).filter(Maintenance.id == maintenance.id).first()

@router.patch("/{maintenance_id}", response_model=MaintenanceResponse)
def update_maintenance(
    maintenance_id: int,
    maintenance_in: MaintenanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.IT_ASSET_MANAGER)),
):
    """Cập nhật thông tin phiếu bảo trì (Chỉ dành cho ADMIN và IT_ASSET_MANAGER)."""
    maintenance = db.query(Maintenance).filter(Maintenance.id == maintenance_id).first()
    if not maintenance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy phiếu bảo trì với ID {maintenance_id}"
        )

    update_data = maintenance_in.model_dump(exclude_unset=True)

    if "technician_id" in update_data and update_data["technician_id"] is not None:
        tech = db.query(User).filter(User.id == update_data["technician_id"]).first()
        if not tech:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy kỹ thuật viên với ID {update_data['technician_id']}"
            )

    for field, value in update_data.items():
        setattr(maintenance, field, value)

    # Audit history
    history = AssetHistory(
        asset_id=maintenance.asset_id,
        action_type=AssetActionType.MAINTENANCE_UPDATED,
        performed_by_id=current_user.id,
        details=f"Cập nhật phiếu bảo trì [{maintenance.maintenance_code}]",
    )
    db.add(history)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cập nhật bảo trì thất bại do xung đột dữ liệu."
        )
    db.refresh(maintenance)

    return _get_maintenance_query(db).filter(Maintenance.id == maintenance.id).first()
