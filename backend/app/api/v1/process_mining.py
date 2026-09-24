from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.models.enums import ProcessCaseType, ProcessEventSource, UserRole
from app.models.user import User
from app.schemas.process_mining import (
    ProcessBottleneck,
    ProcessCaseDetail,
    ProcessMiningCasesResponse,
    ProcessMiningFilters,
    ProcessMiningSummary,
    ProcessVariantReport,
)
from app.services.process_mining import ProcessMiningService

router = APIRouter()
_ANALYTICS_ROLES = (
    UserRole.ADMIN,
    UserRole.IT_ASSET_MANAGER,
    UserRole.MANAGER,
)


def process_mining_filters(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    case_type: ProcessCaseType | None = None,
    source: ProcessEventSource | None = None,
) -> ProcessMiningFilters:
    for name, value in (("date_from", date_from), ("date_to", date_to)):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise HTTPException(status_code=422, detail=f"{name} must include a timezone")
    if date_from is not None and date_to is not None and date_from >= date_to:
        raise HTTPException(status_code=422, detail="date_from must be earlier than exclusive date_to")
    return ProcessMiningFilters(
        date_from=date_from,
        date_to=date_to,
        case_type=case_type,
        source=source,
    )


@router.get("/summary", response_model=ProcessMiningSummary)
def get_summary(
    filters: ProcessMiningFilters = Depends(process_mining_filters),
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*_ANALYTICS_ROLES)),
):
    return ProcessMiningService.get_summary(db, filters)


@router.get("/variants", response_model=ProcessVariantReport)
def get_variants(
    filters: ProcessMiningFilters = Depends(process_mining_filters),
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*_ANALYTICS_ROLES)),
):
    return ProcessMiningService.get_variants(db, filters)


@router.get("/bottlenecks", response_model=list[ProcessBottleneck])
def get_bottlenecks(
    filters: ProcessMiningFilters = Depends(process_mining_filters),
    min_sample: Annotated[int, Query(ge=1)] = 5,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*_ANALYTICS_ROLES)),
):
    return ProcessMiningService.get_bottlenecks(db, filters, min_sample=min_sample)


@router.get("/cases", response_model=ProcessMiningCasesResponse)
def get_cases(
    filters: ProcessMiningFilters = Depends(process_mining_filters),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*_ANALYTICS_ROLES)),
):
    return ProcessMiningService.get_cases(db, filters, page=page, page_size=page_size)


@router.get("/cases/{case_id}", response_model=ProcessCaseDetail)
def get_case_detail(
    case_id: int,
    filters: ProcessMiningFilters = Depends(process_mining_filters),
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*_ANALYTICS_ROLES)),
):
    case = ProcessMiningService.get_case_detail(db, case_id, filters)
    if case is None:
        raise HTTPException(status_code=404, detail="Process case not found")
    return case
