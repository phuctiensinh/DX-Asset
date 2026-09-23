from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.optimization import (
    AllocationRequest, AllocationResponse, CapacityRequest, CapacityResponse,
    ReplacementRecommendationsResponse, ReplacementSimulationRequest, ReplacementSimulationResponse,
)
from app.services.optimization import OptimizationService

router = APIRouter()
ROLES = (UserRole.ADMIN, UserRole.IT_ASSET_MANAGER, UserRole.MANAGER)


@router.post("/what-if/allocation", response_model=AllocationResponse, dependencies=[Depends(require_roles(*ROLES))])
def allocation(payload: AllocationRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return OptimizationService.simulate_allocation(db, payload)


@router.post("/what-if/capacity", response_model=CapacityResponse, dependencies=[Depends(require_roles(*ROLES))])
def capacity(payload: CapacityRequest, user: User = Depends(get_current_user)):
    return OptimizationService.simulate_capacity(payload)


@router.post("/what-if/replacement", response_model=ReplacementSimulationResponse, dependencies=[Depends(require_roles(*ROLES))])
def replacement(payload: ReplacementSimulationRequest, user: User = Depends(get_current_user)):
    return OptimizationService.simulate_replacement(payload)


@router.get("/recommendations/replacements", response_model=ReplacementRecommendationsResponse, dependencies=[Depends(require_roles(*ROLES))])
def replacements(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return OptimizationService.get_replacement_recommendations(db, limit, offset)
