from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.core.database import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import User
from app.models.enums import UserRole, AssetStatus, AssetActionType
from app.models.asset import Asset
from app.models.department import Department
from app.models.history import AssetHistory
from app.schemas.asset import AssetCreate, AssetUpdate, AssetResponse, AssetListResponse

router = APIRouter()

@router.get("", response_model=AssetListResponse)
def list_assets(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None, description="Tìm kiếm theo mã tài sản, tên hoặc số serial"),
    status_filter: Optional[AssetStatus] = Query(None, alias="status", description="Lọc theo trạng thái"),
    category_filter: Optional[str] = Query(None, alias="category", description="Lọc theo loại tài sản"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy danh sách tài sản với tìm kiếm, lọc và phân trang (Tất cả vai trò đã đăng nhập)."""
    query = db.query(Asset).options(
        joinedload(Asset.department),
        joinedload(Asset.current_user)
    )

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Asset.asset_code.ilike(term),
                Asset.name.ilike(term),
                Asset.serial_number.ilike(term)
            )
        )

    if status_filter:
        query = query.filter(Asset.status == status_filter)

    if category_filter and category_filter.strip():
        query = query.filter(Asset.category == category_filter.strip())

    total = query.count()
    items = query.order_by(Asset.id.desc()).offset(skip).limit(limit).all()

    return AssetListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit
    )

@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy thông tin chi tiết một tài sản theo ID."""
    asset = db.query(Asset).options(
        joinedload(Asset.department),
        joinedload(Asset.current_user)
    ).filter(Asset.id == asset_id).first()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy tài sản với ID {asset_id}"
        )

    return asset

@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(
    asset_in: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.IT_ASSET_MANAGER)),
):
    """Tạo tài sản mới (Chỉ dành cho ADMIN và IT_ASSET_MANAGER)."""
    # Check duplicate asset code
    existing_code = db.query(Asset).filter(Asset.asset_code == asset_in.asset_code).first()
    if existing_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mã tài sản '{asset_in.asset_code}' đã tồn tại trong hệ thống."
        )

    # Check duplicate serial number if provided
    if asset_in.serial_number:
        existing_serial = db.query(Asset).filter(Asset.serial_number == asset_in.serial_number).first()
        if existing_serial:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Số serial '{asset_in.serial_number}' đã tồn tại trong hệ thống."
            )

    # Verify department exists if department_id provided
    if asset_in.department_id:
        dept = db.query(Department).filter(Department.id == asset_in.department_id).first()
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Phòng ban với ID {asset_in.department_id} không tồn tại."
            )

    # Verify user exists if current_user_id provided
    if asset_in.current_user_id:
        u = db.query(User).filter(User.id == asset_in.current_user_id).first()
        if not u:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Người dùng với ID {asset_in.current_user_id} không tồn tại."
            )

    asset_data = asset_in.model_dump()
    if not asset_data.get("qr_code_url"):
        asset_data["qr_code_url"] = f"/assets/{asset_in.asset_code}"

    asset = Asset(**asset_data)
    db.add(asset)
    db.flush()

    # Record AssetHistory
    history = AssetHistory(
        asset_id=asset.id,
        action_type=AssetActionType.CREATED,
        performed_by_id=current_user.id,
        details=f"Tạo mới tài sản '{asset.name}' (Mã: {asset.asset_code})",
    )
    db.add(history)

    db.commit()
    db.refresh(asset)

    # Reload with relationships
    return db.query(Asset).options(
        joinedload(Asset.department),
        joinedload(Asset.current_user)
    ).filter(Asset.id == asset.id).first()

@router.patch("/{asset_id}", response_model=AssetResponse)
def update_asset(
    asset_id: int,
    asset_in: AssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.IT_ASSET_MANAGER)),
):
    """Cập nhật thông tin tài sản (Chỉ dành cho ADMIN và IT_ASSET_MANAGER)."""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy tài sản với ID {asset_id}"
        )

    update_data = asset_in.model_dump(exclude_unset=True)

    # Check duplicate serial number if updated
    if "serial_number" in update_data and update_data["serial_number"]:
        serial_sn = update_data["serial_number"]
        existing_serial = db.query(Asset).filter(
            Asset.serial_number == serial_sn,
            Asset.id != asset_id
        ).first()
        if existing_serial:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Số serial '{serial_sn}' đã tồn tại trong hệ thống."
            )

    # Track status change for history audit
    old_status = asset.status
    status_changed = "status" in update_data and update_data["status"] != old_status

    for field, value in update_data.items():
        setattr(asset, field, value)

    # Audit history
    if status_changed:
        history = AssetHistory(
            asset_id=asset.id,
            action_type=AssetActionType.STATUS_CHANGED,
            performed_by_id=current_user.id,
            details=f"Cập nhật trạng thái từ '{old_status}' sang '{asset.status}'",
        )
        db.add(history)

    db.commit()
    db.refresh(asset)

    return db.query(Asset).options(
        joinedload(Asset.department),
        joinedload(Asset.current_user)
    ).filter(Asset.id == asset_id).first()

@router.delete("/{asset_id}", response_model=AssetResponse)
def soft_delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.IT_ASSET_MANAGER)),
):
    """Thanh lý / Ngừng hoạt động tài sản (Soft-delete / RETIRED) (Chỉ dành cho ADMIN và IT_ASSET_MANAGER)."""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy tài sản với ID {asset_id}"
        )

    asset.status = AssetStatus.RETIRED
    asset.current_user_id = None

    history = AssetHistory(
        asset_id=asset.id,
        action_type=AssetActionType.STATUS_CHANGED,
        performed_by_id=current_user.id,
        details="Tài sản đã được thanh lý (RETIRED) khỏi hệ thống.",
    )
    db.add(history)

    db.commit()
    db.refresh(asset)

    return db.query(Asset).options(
        joinedload(Asset.department),
        joinedload(Asset.current_user)
    ).filter(Asset.id == asset_id).first()
