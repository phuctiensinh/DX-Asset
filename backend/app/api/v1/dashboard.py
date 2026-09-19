from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.asset import Asset
from app.models.assignment import AssetAssignment
from app.models.incident import Incident
from app.models.department import Department
from app.models.history import AssetHistory
from app.models.enums import AssetStatus, AssignmentStatus, IncidentStatus
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    AssetStatusCounts,
    AssignmentStatusCounts,
    IncidentStatusCounts,
    DepartmentAssetStats,
    RecentActivityItem,
)

router = APIRouter()

@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve real-time aggregated dashboard summary statistics including:
    - Asset status distribution
    - Assignment status breakdown
    - Incident status counts
    - Department asset allocation
    - Recent 10 asset activity logs
    """
    # 1. Asset status counts aggregation
    asset_status_query = db.query(Asset.status, func.count(Asset.id)).group_by(Asset.status).all()
    asset_counts_dict = {status.value: 0 for status in AssetStatus}
    total_assets = 0
    for status_val, count in asset_status_query:
        # Handle string or Enum instance keys returned by DB driver
        key = status_val.value if hasattr(status_val, 'value') else str(status_val)
        asset_counts_dict[key] = count
        total_assets += count

    assets_summary = AssetStatusCounts(
        total=total_assets,
        by_status=asset_counts_dict,
        in_stock=asset_counts_dict.get(AssetStatus.IN_STOCK.value, 0),
        assigned=asset_counts_dict.get(AssetStatus.ASSIGNED.value, 0),
        in_maintenance=asset_counts_dict.get(AssetStatus.IN_MAINTENANCE.value, 0),
        damaged=asset_counts_dict.get(AssetStatus.DAMAGED.value, 0),
        retired=asset_counts_dict.get(AssetStatus.RETIRED.value, 0),
        lost=asset_counts_dict.get(AssetStatus.LOST.value, 0),
        inactive=asset_counts_dict.get(AssetStatus.INACTIVE.value, 0),
    )

    # 2. Assignment status counts aggregation
    assignment_status_query = db.query(AssetAssignment.status, func.count(AssetAssignment.id)).group_by(AssetAssignment.status).all()
    assignment_counts_dict = {status.value: 0 for status in AssignmentStatus}
    total_assignments = 0
    for status_val, count in assignment_status_query:
        key = status_val.value if hasattr(status_val, 'value') else str(status_val)
        assignment_counts_dict[key] = count
        total_assignments += count

    assignments_summary = AssignmentStatusCounts(
        total=total_assignments,
        by_status=assignment_counts_dict,
        active=assignment_counts_dict.get(AssignmentStatus.ACTIVE.value, 0),
        returned=assignment_counts_dict.get(AssignmentStatus.RETURNED.value, 0),
    )

    # 3. Incident status counts aggregation
    incident_status_query = db.query(Incident.status, func.count(Incident.id)).group_by(Incident.status).all()
    incident_counts_dict = {status.value: 0 for status in IncidentStatus}
    total_incidents = 0
    for status_val, count in incident_status_query:
        key = status_val.value if hasattr(status_val, 'value') else str(status_val)
        incident_counts_dict[key] = count
        total_incidents += count

    pending_incidents = (
        incident_counts_dict.get(IncidentStatus.OPEN.value, 0) +
        incident_counts_dict.get(IncidentStatus.IN_REVIEW.value, 0) +
        incident_counts_dict.get(IncidentStatus.IN_PROGRESS.value, 0) +
        incident_counts_dict.get(IncidentStatus.WAITING_FOR_INFO.value, 0)
    )

    incidents_summary = IncidentStatusCounts(
        total=total_incidents,
        by_status=incident_counts_dict,
        open=incident_counts_dict.get(IncidentStatus.OPEN.value, 0),
        in_review=incident_counts_dict.get(IncidentStatus.IN_REVIEW.value, 0),
        in_progress=incident_counts_dict.get(IncidentStatus.IN_PROGRESS.value, 0),
        waiting_for_info=incident_counts_dict.get(IncidentStatus.WAITING_FOR_INFO.value, 0),
        resolved=incident_counts_dict.get(IncidentStatus.RESOLVED.value, 0),
        closed=incident_counts_dict.get(IncidentStatus.CLOSED.value, 0),
        cancelled=incident_counts_dict.get(IncidentStatus.CANCELLED.value, 0),
        pending=pending_incidents,
    )

    # 4. Department statistics aggregation
    dept_rows = (
        db.query(
            Department.id,
            Department.code,
            Department.name,
            func.count(Asset.id).label("total_assets"),
            func.count(case((Asset.status == AssetStatus.ASSIGNED, Asset.id))).label("assigned_assets"),
            func.count(case((Asset.status == AssetStatus.IN_STOCK, Asset.id))).label("in_stock_assets"),
        )
        .outerjoin(Asset, Department.id == Asset.department_id)
        .group_by(Department.id, Department.code, Department.name)
        .order_by(Department.name.asc())
        .all()
    )

    department_stats: List[DepartmentAssetStats] = [
        DepartmentAssetStats(
            department_id=dept_id,
            department_code=code,
            department_name=name,
            total_assets=total or 0,
            assigned_assets=assigned or 0,
            in_stock_assets=in_stock or 0,
        )
        for dept_id, code, name, total, assigned, in_stock in dept_rows
    ]

    # Check if there are assets with no department assigned
    unassigned_row = (
        db.query(
            func.count(Asset.id).label("total_assets"),
            func.count(case((Asset.status == AssetStatus.ASSIGNED, Asset.id))).label("assigned_assets"),
            func.count(case((Asset.status == AssetStatus.IN_STOCK, Asset.id))).label("in_stock_assets"),
        )
        .filter(Asset.department_id.is_(None))
        .first()
    )

    if unassigned_row and unassigned_row.total_assets and unassigned_row.total_assets > 0:
        department_stats.append(
            DepartmentAssetStats(
                department_id=None,
                department_code="UNASSIGNED",
                department_name="Chưa gán phòng ban",
                total_assets=unassigned_row.total_assets or 0,
                assigned_assets=unassigned_row.assigned_assets or 0,
                in_stock_assets=unassigned_row.in_stock_assets or 0,
            )
        )

    # 5. Recent 10 asset activities
    recent_history = (
        db.query(AssetHistory, Asset, User)
        .join(Asset, AssetHistory.asset_id == Asset.id)
        .outerjoin(User, AssetHistory.performed_by_id == User.id)
        .order_by(AssetHistory.created_at.desc(), AssetHistory.id.desc())
        .limit(10)
        .all()
    )

    recent_activities: List[RecentActivityItem] = []
    for history, asset, user in recent_history:
        performer_name = "Hệ thống"
        if user:
            performer_name = user.full_name
        elif history.performed_by_id:
            performer_name = f"User #{history.performed_by_id}"

        recent_activities.append(
            RecentActivityItem(
                id=history.id,
                asset_id=history.asset_id,
                asset_code=asset.asset_code if asset else "N/A",
                asset_name=asset.name if asset else "N/A",
                action_type=history.action_type,
                performed_by_id=history.performed_by_id,
                performed_by_name=performer_name,
                details=history.details,
                created_at=history.created_at,
            )
        )

    return DashboardSummaryResponse(
        assets=assets_summary,
        assignments=assignments_summary,
        incidents=incidents_summary,
        departments=department_stats,
        recent_activities=recent_activities,
    )
