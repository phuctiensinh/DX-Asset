import re
import logging
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_

from app.models.incident import Incident
from app.models.maintenance import Maintenance
from app.models.asset import Asset
from app.models.enums import IncidentCategory, IncidentPriority, IncidentStatus, MaintenanceStatus
from app.schemas.knowledge_base import (
    SimilarIncidentItem,
    SimilarIncidentListResponse,
    LinkedMaintenanceInfo,
)

logger = logging.getLogger(__name__)

STOP_WORDS: Set[str] = {
    "bị", "lỗi", "không", "đã", "cho", "và", "của", "với", "là", "các", "như", "theo",
    "được", "khi", "tại", "về", "trên", "dưới", "này", "đó", "ra", "vào", "gì", "nào",
    "the", "a", "an", "is", "in", "to", "and", "or", "of", "for", "with", "on", "at", "by"
}

def tokenize_text(text: str) -> Set[str]:
    """Tokenizes text into normalized unique keywords, removing punctuation and stop words."""
    if not text:
        return set()
    clean = re.sub(r"[^\w\s]", " ", text.lower())
    words = re.findall(r"\w+", clean)
    return {w for w in words if len(w) >= 2 and w not in STOP_WORDS}

class KnowledgeBaseService:
    @staticmethod
    def get_similar_incidents(
        db: Session,
        target_incident_id: int,
        limit: int = 5,
        min_score: float = 30.0,
    ) -> SimilarIncidentListResponse:
        target = db.query(Incident).options(
            joinedload(Incident.asset)
        ).filter(Incident.id == target_incident_id).first()

        if not target:
            raise ValueError(f"Không tìm thấy phiếu sự cố với ID {target_incident_id}")

        # 1. Knowledge Source Eligibility Filter in DB
        # Must be RESOLVED or CLOSED, have non-empty resolution_notes, and exclude target incident itself
        candidate_query = db.query(Incident).options(
            joinedload(Incident.asset),
            joinedload(Incident.maintenances)
        ).filter(
            Incident.id != target.id,
            Incident.status.in_([IncidentStatus.RESOLVED, IncidentStatus.CLOSED]),
            Incident.resolution_notes.isnot(None),
            func.length(func.trim(Incident.resolution_notes)) > 0
        ).order_by(Incident.id.desc()).limit(50)

        candidates = candidate_query.all()

        target_tokens = tokenize_text(f"{target.title} {target.description}")

        scored_items: List[Tuple[float, SimilarIncidentItem]] = []

        for cand in candidates:
            # 1. Category Match (Max 40 pts)
            category_score = 0.0
            reasons = []
            if cand.category == target.category:
                category_score = 40.0
                reasons.append(f"✓ Cùng danh mục sự cố: {cand.category.value} (+40 điểm)")

            # 2. Text Overlap Score (Max 40 pts) using Jaccard Similarity
            cand_tokens = tokenize_text(f"{cand.title} {cand.description}")
            jaccard = 0.0
            if target_tokens and cand_tokens:
                intersection = target_tokens.intersection(cand_tokens)
                union = target_tokens.union(cand_tokens)
                if union:
                    jaccard = len(intersection) / len(union)

            text_score = jaccard * 40.0
            if text_score > 0:
                matched_kw = list(target_tokens.intersection(cand_tokens))[:3]
                kw_str = ", ".join([f"'{k}'" for k in matched_kw])
                reasons.append(f"✓ Trùng khớp từ khóa lỗi: {kw_str} (+{int(text_score)} điểm)")

            # 3. Asset Type Match (Max 10 pts)
            asset_score = 0.0
            if target.asset and cand.asset and target.asset.category and cand.asset.category:
                if target.asset.category.lower() == cand.asset.category.lower():
                    asset_score = 10.0
                    reasons.append(f"✓ Cùng loại tài sản: {cand.asset.category} (+10 điểm)")

            # 4. Resolution Quality Bonus (Max 10 pts)
            res_bonus = 0.0
            linked_maint_info: Optional[LinkedMaintenanceInfo] = None
            
            # Find completed maintenance if any
            completed_mnt = None
            if cand.maintenances:
                for m in cand.maintenances:
                    if m.status == MaintenanceStatus.COMPLETED:
                        completed_mnt = m
                        break
                if not completed_mnt:
                    completed_mnt = cand.maintenances[0]

            if completed_mnt:
                res_bonus = 10.0
                duration_h = None
                if completed_mnt.completed_date and completed_mnt.start_date:
                    duration_h = round((completed_mnt.completed_date - completed_mnt.start_date).total_seconds() / 3600.0, 1)
                
                linked_maint_info = LinkedMaintenanceInfo(
                    maintenance_code=completed_mnt.maintenance_code,
                    status=str(completed_mnt.status),
                    repair_cost=float(completed_mnt.repair_cost or 0.0),
                    duration_hours=duration_h,
                    resolution_notes=completed_mnt.resolution_notes,
                )
                reasons.append(f"✓ Đã hoàn thành đợt bảo trì [{completed_mnt.maintenance_code}] (+10 điểm)")
            elif cand.resolution_notes and len(cand.resolution_notes.strip()) > 15:
                res_bonus = 5.0
                reasons.append(f"✓ Có phương án giải quyết chi tiết (+5 điểm)")

            total_score = min(100.0, category_score + text_score + asset_score + res_bonus)

            if total_score >= min_score:
                item = SimilarIncidentItem(
                    incident_id=cand.id,
                    ticket_code=cand.ticket_code,
                    title=cand.title,
                    category=cand.category,
                    priority=cand.priority,
                    status=cand.status,
                    resolution_notes=cand.resolution_notes or "Chưa có ghi chú",
                    repair_cost=float(cand.repair_cost or 0.0),
                    resolved_at=cand.resolved_at or cand.updated_at,
                    asset_code=cand.asset.asset_code if cand.asset else None,
                    asset_name=cand.asset.name if cand.asset else None,
                    similarity_score=round(total_score, 1),
                    similarity_reasons=reasons,
                    linked_maintenance=linked_maint_info,
                )
                scored_items.append((total_score, item))

        # Rank by total score descending
        scored_items.sort(key=lambda x: x[0], reverse=True)
        final_items = [item for _, item in scored_items[:limit]]

        return SimilarIncidentListResponse(
            target_incident_id=target.id,
            target_ticket_code=target.ticket_code,
            total_found=len(final_items),
            items=final_items,
        )
