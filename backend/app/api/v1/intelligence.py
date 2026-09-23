from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import User
from app.models.asset import Asset
from app.models.enums import UserRole
from app.schemas.intelligence import (
    AssetIntelligenceDetailResponse,
    IntelligenceSummaryResponse,
    RiskMatrixItem,
    TopFailureItem,
    TopCostlyItem,
)
from app.services.asset_intelligence import AssetIntelligenceService

router = APIRouter()

ALLOWED_ANALYTICS_ROLES = [UserRole.ADMIN, UserRole.IT_ASSET_MANAGER, UserRole.MANAGER]

@router.get(
    "/summary",
    response_model=IntelligenceSummaryResponse,
    dependencies=[Depends(require_roles(*ALLOWED_ANALYTICS_ROLES))]
)
def get_intelligence_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get global asset intelligence summary analytics."""
    return AssetIntelligenceService.get_intelligence_summary(db)

@router.get(
    "/risk-matrix",
    dependencies=[Depends(require_roles(*ALLOWED_ANALYTICS_ROLES))]
)
def get_risk_matrix(
    risk_level: Optional[str] = Query(None, description="Filter by risk level: LOW, MEDIUM, HIGH, CRITICAL"),
    category: Optional[str] = Query(None, description="Filter by asset category"),
    search: Optional[str] = Query(None, description="Search query by code or name"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get paginated risk matrix of assets with risk scores and warning reasons."""
    items, total = AssetIntelligenceService.get_risk_matrix(
        db,
        risk_level=risk_level,
        category=category,
        search=search,
        limit=limit,
        offset=offset,
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }

@router.get(
    "/top-failures",
    response_model=List[TopFailureItem],
    dependencies=[Depends(require_roles(*ALLOWED_ANALYTICS_ROLES))]
)
def get_top_failures(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get top failing assets by incident frequency."""
    return AssetIntelligenceService.get_top_failures(db, limit=limit)

@router.get(
    "/top-costly",
    response_model=List[TopCostlyItem],
    dependencies=[Depends(require_roles(*ALLOWED_ANALYTICS_ROLES))]
)
def get_top_costly(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get top costly assets by total repair cost."""
    return AssetIntelligenceService.get_top_costly(db, limit=limit)

@router.get(
    "/assets/{asset_id}",
    response_model=AssetIntelligenceDetailResponse
)
def get_asset_intelligence_detail(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get deep-dive asset intelligence detail for a specific asset."""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID {asset_id} not found"
        )

    # RBAC check: EMPLOYEE can only view intelligence of their currently assigned asset
    if current_user.role == UserRole.EMPLOYEE:
        if asset.current_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employees can only view intelligence for their assigned assets"
            )

    detail = AssetIntelligenceService.get_asset_intelligence_detail(db, asset_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Intelligence details for Asset ID {asset_id} not found"
        )

    return detail
