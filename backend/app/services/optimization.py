import math
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.enums import AssetStatus, IncidentStatus, MaintenanceStatus
from app.models.incident import Incident
from app.models.maintenance import Maintenance
from app.schemas.optimization import (
    AllocationCandidate, AllocationRequest, AllocationResponse,
    BookValueYear, CapacityRequest, CapacityResponse,
    ReplacementRecommendation, ReplacementRecommendationsResponse,
    ReplacementSimulationRequest, ReplacementSimulationResponse,
)


class OptimizationService:
    @staticmethod
    def simulate_allocation(db: Session, request: AllocationRequest) -> AllocationResponse:
        query = db.query(Asset).filter(
            Asset.status == AssetStatus.IN_STOCK,
            func.lower(Asset.category) == request.asset_category.strip().lower(),
        )
        if request.location:
            query = query.filter(func.lower(Asset.location) == request.location.strip().lower())
        if request.brand:
            query = query.filter(func.lower(Asset.brand) == request.brand.strip().lower())
        if request.model:
            query = query.filter(func.lower(Asset.model) == request.model.strip().lower())
        count = query.order_by(None).count()
        assets = query.order_by(Asset.asset_code).limit(500).all()
        return AllocationResponse(
            department_id=request.department_id,
            asset_category=request.asset_category,
            requested_quantity=request.requested_quantity,
            available_quantity=count,
            shortage_quantity=max(0, request.requested_quantity - count),
            enough=count >= request.requested_quantity,
            candidates=[AllocationCandidate(
                asset_id=a.id, asset_code=a.asset_code, name=a.name, category=a.category,
                brand=a.brand, model=a.model, location=a.location,
            ) for a in assets[:request.requested_quantity]],
            assumptions=["Only assets with status IN_STOCK are counted; ASSIGNED assets are unavailable.",
                         "Category and optional filters must match the current asset record.",
                         "The requested department is a simulation target; no assignment is created."],
            warnings=["Candidates are recommendations only and have NOT been assigned."] +
                     (["Candidate list is capped at 500 assets."] if count > 500 else []),
        )

    @staticmethod
    def simulate_capacity(request: CapacityRequest) -> CapacityResponse:
        required = math.ceil(request.expected_incidents / (request.target_sla_days * request.incidents_per_technician_per_day)) if request.expected_incidents else 0
        gap = required - request.current_technician_count if request.current_technician_count is not None else None
        return CapacityResponse(
            current_sla_days=request.current_sla_days, target_sla_days=request.target_sla_days,
            expected_incidents=request.expected_incidents,
            incidents_per_technician_per_day=request.incidents_per_technician_per_day,
            estimated_required_technicians=required, current_technician_count=request.current_technician_count,
            estimated_gap=gap,
            assumptions=["Scenario estimate based on the supplied incident volume, target SLA, and per-technician daily capacity.",
                         "Assumes incidents are distributed evenly across the target SLA window; this is not a guaranteed staffing requirement."],
            warnings=["This is a scenario estimate based on the supplied capacity assumptions.",
                      "Current SLA is shown for comparison and does not change system configuration."],
        )

    @staticmethod
    def simulate_replacement(request: ReplacementSimulationRequest) -> ReplacementSimulationResponse:
        total_cost = request.quantity * request.unit_cost
        residual = request.residual_value if request.residual_value is not None else total_cost * (request.residual_value_rate or 0)
        residual = round(residual, 2)
        annual = (total_cost - residual) / request.useful_life_years
        rows = []
        previous_value = total_cost
        for year in range(1, request.simulation_horizon_years + 1):
            value = max(residual, total_cost - annual * min(year, request.useful_life_years))
            rounded_value = round(value, 2)
            depreciation_expense = round(previous_value - rounded_value, 2)
            rows.append(BookValueYear(
                year=year,
                depreciation_expense=depreciation_expense,
                estimated_book_value=rounded_value,
            ))
            previous_value = rounded_value
        return ReplacementSimulationResponse(
            quantity=request.quantity, unit_cost=request.unit_cost, total_initial_cost=round(total_cost, 2),
            useful_life_years=request.useful_life_years, simulation_horizon_years=request.simulation_horizon_years,
            residual_value=residual, annual_depreciation=round(annual, 2), estimated_book_value_by_year=rows,
            estimated_replacement_cost=round(total_cost, 2),
            assumptions=["Simulation based on user-provided assumptions.", "Straight-line depreciation is used; no tax, inflation, financing, or disposal costs are included."],
            warnings=["This is not actual financial accounting and is not derived from asset acquisition records."],
        )

    @staticmethod
    def get_replacement_recommendations(db: Session, limit: int = 20, offset: int = 0) -> ReplacementRecommendationsResponse:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=60)
        # Bound the candidate set before calculating scores. Grouped aggregates avoid per-asset queries.
        assets_q = db.query(Asset).order_by(Asset.id)
        candidates = assets_q.limit(5000).all()
        asset_ids = [a.id for a in candidates]
        if not asset_ids:
            return ReplacementRecommendationsResponse(items=[], total=0, limit=limit, offset=offset)
        inc_rows = db.query(
            Incident.asset_id, func.count(Incident.id),
            func.sum(case((Incident.id.notin_(
                db.query(Maintenance.incident_id).filter(Maintenance.incident_id.isnot(None))
            ), Incident.repair_cost), else_=0)),
        ).filter(Incident.asset_id.in_(asset_ids), Incident.status != IncidentStatus.CANCELLED).group_by(Incident.asset_id).all()
        repeated_rows = db.query(Incident.asset_id, Incident.category, func.count(Incident.id)).filter(
            Incident.asset_id.in_(asset_ids), Incident.status != IncidentStatus.CANCELLED,
            Incident.created_at >= cutoff,
        ).group_by(Incident.asset_id, Incident.category).having(func.count(Incident.id) >= 2).all()
        repeated_assets = {row[0] for row in repeated_rows}
        mnt_rows = db.query(
            Maintenance.asset_id, func.count(Maintenance.id), func.sum(Maintenance.repair_cost),
        ).filter(Maintenance.asset_id.in_(asset_ids), Maintenance.status != MaintenanceStatus.CANCELLED).group_by(Maintenance.asset_id).all()
        inc = {row[0]: (int(row[1] or 0), float(row[2] or 0)) for row in inc_rows}
        mnt = {row[0]: (int(row[1] or 0), float(row[2] or 0)) for row in mnt_rows}
        # Same transparent core risk weighting used by Asset Intelligence, supplemented with recurrence,
        # maintenance frequency, and age. These are heuristic recommendation scores, not an optimizer.
        scored = []
        for a in candidates:
            ic, incident_cost = inc.get(a.id, (0, 0.0))
            mc, maintenance_cost = mnt.get(a.id, (0, 0.0))
            cost = incident_cost + maintenance_cost
            repeated = a.id in repeated_assets
            risk = min(100.0, 0.25 * min(100, ic * 25) + 0.25 * min(100, cost / 2_000_000 * 20) +
                       0.20 * (100 if repeated else 0) +
                       0.20 * (100 if a.status == AssetStatus.DAMAGED else 60 if a.status == AssetStatus.IN_MAINTENANCE else 0))
            age = max(0.0, (date.today() - a.purchase_date).days / 365.25) if a.purchase_date else None
            age_component = min(20.0, age * 2) if age is not None else 0
            score = round(min(100.0, risk * 0.7 + min(20, mc * 4) + age_component), 1)
            reasons = []
            if risk >= 40: reasons.append(f"Elevated asset risk score ({risk:.1f}/100).")
            if repeated: reasons.append("Repeated incidents recorded within the last 60 days.")
            if cost >= 2_000_000: reasons.append(f"Recorded repair cost is high ({cost:,.0f} VND).")
            if mc >= 3: reasons.append(f"Frequent maintenance recorded ({mc} events).")
            if age is not None and age >= 5: reasons.append(f"Long usage period ({age:.1f} years since purchase).")
            if a.status in (AssetStatus.DAMAGED, AssetStatus.IN_MAINTENANCE): reasons.append(f"Current status is {a.status.value}.")
            if not reasons: reasons.append("Included for comparison; available history indicates no strong replacement signal.")
            priority = "HIGH" if score >= 60 else "MEDIUM" if score >= 30 else "LOW"
            scored.append(ReplacementRecommendation(
                asset_id=a.id, asset_code=a.asset_code, name=a.name, category=a.category, status=a.status.value,
                replacement_recommendation_score=score, priority_level=priority, risk_score=round(risk, 1),
                health_score=round(max(0, 100-risk), 1), repair_cost=round(cost, 2), incident_count=ic,
                maintenance_count=mc, repeated_failure=repeated, purchase_date=a.purchase_date,
                age_years=round(age, 1) if age is not None else None, reasons=reasons,
            ))
        scored.sort(key=lambda item: (-item.replacement_recommendation_score, item.asset_code))
        return ReplacementRecommendationsResponse(items=scored[offset:offset+limit], total=len(scored), limit=limit, offset=offset)
