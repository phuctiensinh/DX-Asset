from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, case, or_, and_

from app.models.asset import Asset
from app.models.incident import Incident
from app.models.maintenance import Maintenance
from app.models.enums import AssetStatus, IncidentStatus, MaintenanceStatus, IncidentCategory
from app.schemas.intelligence import (
    AssetHealthRiskScore,
    ComponentScores,
    AssetIntelligenceMetrics,
    AssetIntelligenceDetailResponse,
    IntelligenceSummaryResponse,
    RiskMatrixItem,
    TopFailureItem,
    TopCostlyItem,
)

class AssetIntelligenceService:

    @staticmethod
    def calculate_asset_metrics(db: Session, asset: Asset) -> AssetIntelligenceMetrics:
        now_dt = datetime.now(timezone.utc)

        # 1. Fetch Incidents & Maintenances for the target asset
        incidents = db.query(Incident).filter(
            Incident.asset_id == asset.id,
            Incident.status != IncidentStatus.CANCELLED
        ).all()

        maintenances = db.query(Maintenance).filter(
            Maintenance.asset_id == asset.id,
            Maintenance.status != MaintenanceStatus.CANCELLED
        ).all()

        incident_count = len(incidents)
        maintenance_count = len(maintenances)

        # Track linked incident IDs to avoid double counting repair cost and MTTR
        linked_incident_ids = set()
        for m in maintenances:
            if m.incident_id is not None:
                linked_incident_ids.add(m.incident_id)

        # 2. Total Repair Cost Calculation (Rule 3)
        # Maintenance repair cost
        mnt_cost = sum(float(m.repair_cost or 0.0) for m in maintenances)
        # Standalone Incidents repair cost (incidents not linked to a maintenance)
        standalone_inc_cost = sum(
            float(inc.repair_cost or 0.0)
            for inc in incidents
            if inc.id not in linked_incident_ids
        )
        total_repair_cost = mnt_cost + standalone_inc_cost

        # Count events for avg repair cost calculation
        cost_events_count = 0
        for m in maintenances:
            if (m.repair_cost or 0) > 0:
                cost_events_count += 1
        for inc in incidents:
            if inc.id not in linked_incident_ids and (inc.repair_cost or 0) > 0:
                cost_events_count += 1

        avg_repair_cost = total_repair_cost / cost_events_count if cost_events_count > 0 else 0.0

        # 3. MTTR Calculation (Rule 4 - No double counting)
        mttr_durations_hours: List[float] = []

        # A. Maintenance linked or independent completed maintenance
        for m in maintenances:
            if m.status == MaintenanceStatus.COMPLETED and m.completed_date is not None:
                start = m.start_date or m.created_at
                end = m.completed_date
                if start and end and end >= start:
                    duration_hrs = (end - start).total_seconds() / 3600.0
                    mttr_durations_hours.append(duration_hrs)

        # B. Standalone Incidents that are RESOLVED or CLOSED with resolved_at != NULL
        for inc in incidents:
            if inc.id not in linked_incident_ids:
                if inc.status in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED) and inc.resolved_at is not None:
                    start = inc.created_at
                    end = inc.resolved_at
                    if start and end and end >= start:
                        duration_hrs = (end - start).total_seconds() / 3600.0
                        mttr_durations_hours.append(duration_hrs)

        avg_mttr_hours = sum(mttr_durations_hours) / len(mttr_durations_hours) if mttr_durations_hours else None

        # 4. Downtime Calculation (Rule 5)
        downtime_durations_hours: List[float] = []

        for m in maintenances:
            start = m.start_date or m.created_at
            if not start:
                continue
            
            # Ensure start is timezone aware
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)

            if m.status == MaintenanceStatus.COMPLETED and m.completed_date is not None:
                end = m.completed_date
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
                if end >= start:
                    downtime_durations_hours.append((end - start).total_seconds() / 3600.0)
            elif m.status == MaintenanceStatus.IN_PROGRESS:
                if now_dt >= start:
                    downtime_durations_hours.append((now_dt - start).total_seconds() / 3600.0)

        total_downtime_hours = max(0.0, sum(downtime_durations_hours))

        # 5. Repeated Failure Calculation (Rule 6 - 60 days)
        sixty_days_ago = now_dt - timedelta(days=60)
        recent_category_counts: Dict[str, int] = {}

        for inc in incidents:
            inc_created = inc.created_at
            if inc_created and inc_created.tzinfo is None:
                inc_created = inc_created.replace(tzinfo=timezone.utc)

            if inc_created and inc_created >= sixty_days_ago:
                cat_val = inc.category.value if hasattr(inc.category, 'value') else str(inc.category)
                recent_category_counts[cat_val] = recent_category_counts.get(cat_val, 0) + 1

        repeated_categories = [cat for cat, count in recent_category_counts.items() if count >= 2]
        has_repeated_failure = len(repeated_categories) > 0

        return AssetIntelligenceMetrics(
            incident_count=incident_count,
            maintenance_count=maintenance_count,
            total_repair_cost=round(total_repair_cost, 2),
            avg_repair_cost=round(avg_repair_cost, 2),
            mttr_hours=round(avg_mttr_hours, 1) if avg_mttr_hours is not None else None,
            downtime_hours=round(total_downtime_hours, 1),
            has_repeated_failure=has_repeated_failure,
            repeated_categories=repeated_categories,
        )

    @staticmethod
    def calculate_risk_score(
        asset_status: AssetStatus,
        metrics: AssetIntelligenceMetrics
    ) -> AssetHealthRiskScore:
        # Rule 7: Analytical Risk Score Formula
        # Incident score: min(100, count * 25)
        incident_score = min(100.0, float(metrics.incident_count) * 25.0)

        # Cost score: min(100, cost / 2_000_000 * 20)
        cost_score = min(100.0, (metrics.total_repair_cost / 2000000.0) * 20.0)

        # Repeat score: 100 if repeated failure else 0
        repeat_score = 100.0 if metrics.has_repeated_failure else 0.0

        # Status score: DAMAGED=100, IN_MAINTENANCE=60, else 0
        status_val = asset_status.value if hasattr(asset_status, 'value') else str(asset_status)
        if status_val == AssetStatus.DAMAGED.value:
            status_score = 100.0
        elif status_val == AssetStatus.IN_MAINTENANCE.value:
            status_score = 60.0
        else:
            status_score = 0.0

        # MTTR score: min(100, avg_mttr / 48 * 50) if mttr_hours is not null else 0
        if metrics.mttr_hours is not None:
            mttr_score = min(100.0, (metrics.mttr_hours / 48.0) * 50.0)
        else:
            mttr_score = 0.0

        # Weighted composite score
        risk_score = round(
            0.25 * incident_score +
            0.25 * cost_score +
            0.20 * repeat_score +
            0.20 * status_score +
            0.10 * mttr_score,
            1
        )

        health_score = max(0.0, round(100.0 - risk_score, 1))

        # Risk Level classification
        if risk_score <= 15.0:
            risk_level = "LOW"
        elif risk_score <= 40.0:
            risk_level = "MEDIUM"
        elif risk_score <= 70.0:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"

        # Rule 8: Warning Reasons Generation
        warning_reasons: List[str] = []

        if status_val == AssetStatus.DAMAGED.value:
            warning_reasons.append("Tài sản hiện đang bị hỏng (DAMAGED)")
        elif status_val == AssetStatus.IN_MAINTENANCE.value:
            warning_reasons.append("Tài sản hiện đang trong quá trình bảo trì (IN_MAINTENANCE)")

        if metrics.incident_count >= 3:
            warning_reasons.append(f"Tài sản có {metrics.incident_count} sự cố trong lịch sử vận hành")
        elif metrics.incident_count > 0:
            warning_reasons.append(f"Đã ghi nhận {metrics.incident_count} sự cố")

        if metrics.total_repair_cost >= 2000000.0:
            formatted_cost = f"{metrics.total_repair_cost:,.0f}".replace(",", ".")
            warning_reasons.append(f"Chi phí sửa chữa {formatted_cost} VNĐ vượt ngưỡng cảnh báo (2 triệu VNĐ)")

        if metrics.has_repeated_failure:
            cats_str = ", ".join(metrics.repeated_categories)
            warning_reasons.append(f"Lỗi danh mục ({cats_str}) lặp lại nhiều hơn 1 lần trong 60 ngày qua")

        if metrics.mttr_hours is not None and metrics.mttr_hours >= 48.0:
            warning_reasons.append(f"Thời gian khắc phục trung bình (MTTR) kéo dài ({metrics.mttr_hours:.1f} giờ)")

        component_scores = ComponentScores(
            incident_score=round(incident_score, 1),
            cost_score=round(cost_score, 1),
            repeat_score=round(repeat_score, 1),
            status_score=round(status_score, 1),
            mttr_score=round(mttr_score, 1),
        )

        return AssetHealthRiskScore(
            risk_score=risk_score,
            health_score=health_score,
            risk_level=risk_level,
            warning_reasons=warning_reasons,
            component_scores=component_scores,
        )

    @staticmethod
    def get_asset_intelligence_detail(db: Session, asset_id: int) -> Optional[AssetIntelligenceDetailResponse]:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            return None

        metrics = AssetIntelligenceService.calculate_asset_metrics(db, asset)
        health_risk = AssetIntelligenceService.calculate_risk_score(asset.status, metrics)

        dept_name = asset.department.name if asset.department else None

        return AssetIntelligenceDetailResponse(
            asset_id=asset.id,
            asset_code=asset.asset_code,
            asset_name=asset.name,
            category=asset.category,
            brand=asset.brand,
            model=asset.model,
            status=asset.status,
            location=asset.location,
            department_name=dept_name,
            metrics=metrics,
            health_risk=health_risk,
        )

    @staticmethod
    def get_intelligence_summary(db: Session) -> IntelligenceSummaryResponse:
        assets = db.query(Asset).all()
        total_assets = len(assets)

        assets_with_incidents_count = 0
        assets_in_maintenance_count = 0
        total_system_repair_cost = 0.0
        all_mttr_hours: List[float] = []
        
        risk_distribution = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        high_risk_count = 0
        critical_risk_count = 0
        total_warning_assets = 0

        for asset in assets:
            status_val = asset.status.value if hasattr(asset.status, 'value') else str(asset.status)
            if status_val == AssetStatus.IN_MAINTENANCE.value:
                assets_in_maintenance_count += 1

            metrics = AssetIntelligenceService.calculate_asset_metrics(db, asset)
            if metrics.incident_count > 0:
                assets_with_incidents_count += 1

            total_system_repair_cost += metrics.total_repair_cost
            if metrics.mttr_hours is not None:
                all_mttr_hours.append(metrics.mttr_hours)

            health_risk = AssetIntelligenceService.calculate_risk_score(asset.status, metrics)
            risk_distribution[health_risk.risk_level] = risk_distribution.get(health_risk.risk_level, 0) + 1

            if health_risk.risk_level == "HIGH":
                high_risk_count += 1
            elif health_risk.risk_level == "CRITICAL":
                critical_risk_count += 1

            if len(health_risk.warning_reasons) > 0:
                total_warning_assets += 1

        avg_system_mttr = sum(all_mttr_hours) / len(all_mttr_hours) if all_mttr_hours else None

        return IntelligenceSummaryResponse(
            total_assets_analyzed=total_assets,
            assets_with_incidents=assets_with_incidents_count,
            assets_in_maintenance=assets_in_maintenance_count,
            total_repair_cost=round(total_system_repair_cost, 2),
            avg_mttr_hours=round(avg_system_mttr, 1) if avg_system_mttr is not None else None,
            risk_distribution=risk_distribution,
            high_risk_count=high_risk_count,
            critical_risk_count=critical_risk_count,
            total_warning_assets=total_warning_assets,
        )

    @staticmethod
    def get_risk_matrix(
        db: Session,
        risk_level: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[RiskMatrixItem], int]:
        query = db.query(Asset)

        if category:
            query = query.filter(Asset.category == category)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Asset.asset_code.ilike(search_pattern),
                    Asset.name.ilike(search_pattern)
                )
            )

        all_matching_assets = query.all()
        matrix_items: List[RiskMatrixItem] = []

        for asset in all_matching_assets:
            metrics = AssetIntelligenceService.calculate_asset_metrics(db, asset)
            health_risk = AssetIntelligenceService.calculate_risk_score(asset.status, metrics)

            if risk_level and health_risk.risk_level != risk_level.upper():
                continue

            dept_name = asset.department.name if asset.department else None

            matrix_items.append(
                RiskMatrixItem(
                    asset_id=asset.id,
                    asset_code=asset.asset_code,
                    asset_name=asset.name,
                    category=asset.category,
                    status=asset.status,
                    department_name=dept_name,
                    risk_score=health_risk.risk_score,
                    health_score=health_risk.health_score,
                    risk_level=health_risk.risk_level,
                    warning_reasons=health_risk.warning_reasons,
                    incident_count=metrics.incident_count,
                    total_repair_cost=metrics.total_repair_cost,
                )
            )

        # Sort matrix items by risk_score descending
        matrix_items.sort(key=lambda x: x.risk_score, reverse=True)
        total_count = len(matrix_items)

        paged_items = matrix_items[offset : offset + limit]
        return paged_items, total_count

    @staticmethod
    def get_top_failures(db: Session, limit: int = 5) -> List[TopFailureItem]:
        assets = db.query(Asset).all()
        items: List[TopFailureItem] = []

        for asset in assets:
            metrics = AssetIntelligenceService.calculate_asset_metrics(db, asset)
            if metrics.incident_count > 0:
                # Find top incident category
                cat_counts: Dict[str, int] = {}
                for inc in asset.incidents:
                    if inc.status != IncidentStatus.CANCELLED:
                        c = inc.category.value if hasattr(inc.category, 'value') else str(inc.category)
                        cat_counts[c] = cat_counts.get(c, 0) + 1

                top_cat = max(cat_counts.items(), key=lambda x: x[1])[0] if cat_counts else None

                items.append(
                    TopFailureItem(
                        asset_id=asset.id,
                        asset_code=asset.asset_code,
                        asset_name=asset.name,
                        category=asset.category,
                        incident_count=metrics.incident_count,
                        top_category=top_cat,
                    )
                )

        items.sort(key=lambda x: x.incident_count, reverse=True)
        return items[:limit]

    @staticmethod
    def get_top_costly(db: Session, limit: int = 5) -> List[TopCostlyItem]:
        assets = db.query(Asset).all()
        items: List[TopCostlyItem] = []

        for asset in assets:
            metrics = AssetIntelligenceService.calculate_asset_metrics(db, asset)
            if metrics.total_repair_cost > 0:
                items.append(
                    TopCostlyItem(
                        asset_id=asset.id,
                        asset_code=asset.asset_code,
                        asset_name=asset.name,
                        category=asset.category,
                        total_repair_cost=metrics.total_repair_cost,
                        maintenance_count=metrics.maintenance_count,
                    )
                )

        items.sort(key=lambda x: x.total_repair_cost, reverse=True)
        return items[:limit]
