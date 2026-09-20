import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.config import settings
from app.models.user import User
from app.models.incident import Incident
from app.models.maintenance import Maintenance
from app.models.technician_skill import TechnicianSkill
from app.models.enums import UserRole, IncidentCategory, IncidentPriority, IncidentStatus, MaintenanceStatus

logger = logging.getLogger(__name__)

QUEUE_MAPPING: Dict[IncidentCategory, str] = {
    IncidentCategory.HARDWARE: "HARDWARE_SUPPORT",
    IncidentCategory.SOFTWARE: "SOFTWARE_SUPPORT",
    IncidentCategory.NETWORK: "NETWORK_SUPPORT",
    IncidentCategory.POWER: "INFRASTRUCTURE_SUPPORT",
    IncidentCategory.PHYSICAL_DAMAGE: "HARDWARE_SUPPORT",
    IncidentCategory.OTHER: "GENERAL_SUPPORT",
}

@dataclass
class ClassificationResult:
    category: IncidentCategory
    queue: str
    confidence: float
    reasoning: str

@dataclass
class TechnicianRecommendation:
    user_id: int
    full_name: str
    email: str
    role: UserRole
    total_score: float
    skill_score: float
    workload_score: float
    sla_score: float
    active_workload: int
    reasons: List[str]

class SmartRoutingService:
    @staticmethod
    def get_queue_for_category(category: IncidentCategory) -> str:
        return QUEUE_MAPPING.get(category, "GENERAL_SUPPORT")

    @staticmethod
    def classify_incident_text(title: str, description: str, current_category: Optional[IncidentCategory] = None) -> ClassificationResult:
        text = f"{title} {description}".lower()

        # Rule-based Keyword Sets
        hardware_kw = ["laptop", "màn hình", "bàn phím", "quạt", "chuột", "mainboard", "ram", "ssd", "ổ cứng", "hỏng phím", "không lên nguồn", "phần cứng", "cpu", "pc", "desktop"]
        software_kw = ["excel", "windows", "phần mềm", "lỗi ứng dụng", "không mở được", "cập nhật", "driver", "software", "office", "app", "cài đặt", "virus"]
        network_kw = ["wifi", "mạng", "internet", "cisco", "switch", "router", "lan", "ip", "kết nối", "ping", "mất mạng"]
        power_kw = ["nguồn", "sạc", "pin", "mất điện", "ổ cắm", "power", "battery", "sụt áp", "cháy nổ"]
        physical_kw = ["vỡ", "nứt", "rơi", "gãy", "va đập", "biến dạng", "physical", "hỏng vỏ", "ngấm nước", "bị ướt"]

        matched_scores = {
            IncidentCategory.HARDWARE: sum(1 for kw in hardware_kw if kw in text),
            IncidentCategory.SOFTWARE: sum(1 for kw in software_kw if kw in text),
            IncidentCategory.NETWORK: sum(1 for kw in network_kw if kw in text),
            IncidentCategory.POWER: sum(1 for kw in power_kw if kw in text),
            IncidentCategory.PHYSICAL_DAMAGE: sum(1 for kw in physical_kw if kw in text),
        }

        best_category = max(matched_scores, key=matched_scores.get)
        best_count = matched_scores[best_category]

        if best_count > 0:
            confidence = min(0.95, 0.75 + (best_count * 0.05))
            reasoning = f"Phân loại dựa trên từ khóa kỹ thuật nhận diện được ({best_category.value})"
            category = best_category
        elif current_category:
            category = current_category
            confidence = 0.80
            reasoning = f"Sử dụng phân loại hiện có của phiếu ({category.value})"
        else:
            category = IncidentCategory.OTHER
            confidence = 0.65
            reasoning = "Không tìm thấy từ khóa đặc trưng, tự động xếp vào nhóm Khác (OTHER)"

        queue = QUEUE_MAPPING.get(category, "GENERAL_SUPPORT")
        return ClassificationResult(
            category=category,
            queue=queue,
            confidence=round(confidence, 2),
            reasoning=reasoning,
        )

    @staticmethod
    def calculate_technician_workload(db: Session, user_id: int) -> Tuple[int, int, int]:
        """Calculates active workload (active incidents, active maintenance, total active tasks)."""
        active_incidents = db.query(func.count(Incident.id)).filter(
            Incident.assigned_it_id == user_id,
            Incident.status.in_([
                IncidentStatus.OPEN,
                IncidentStatus.IN_REVIEW,
                IncidentStatus.IN_PROGRESS,
                IncidentStatus.WAITING_FOR_INFO
            ])
        ).scalar() or 0

        active_maintenances = db.query(func.count(Maintenance.id)).filter(
            Maintenance.technician_id == user_id,
            Maintenance.status.in_([
                MaintenanceStatus.SCHEDULED,
                MaintenanceStatus.IN_PROGRESS
            ])
        ).scalar() or 0

        total_workload = active_incidents + active_maintenances
        return active_incidents, active_maintenances, total_workload

    @staticmethod
    def get_recommendations(
        db: Session,
        category: IncidentCategory,
        priority: IncidentPriority,
    ) -> List[TechnicianRecommendation]:
        """
        Generates transparent, 100-point MVP score for candidate technicians:
        - Skill Score: Max 40 points
        - Workload Score: Max 40 points
        - SLA Suitability Score: Max 20 points
        """
        tech_users = db.query(User).filter(
            User.role.in_([UserRole.ADMIN, UserRole.IT_ASSET_MANAGER]),
            User.is_active == True
        ).all()

        recommendations: List[TechnicianRecommendation] = []

        for user in tech_users:
            # 1. Skill Score (Max 40 pts)
            skill = db.query(TechnicianSkill).filter(
                TechnicianSkill.user_id == user.id,
                TechnicianSkill.category == category
            ).first()

            skill_level = skill.skill_level if skill else 3
            skill_score = (skill_level / 5.0) * 40.0

            # 2. Workload Score (Max 40 pts)
            _, _, total_workload = SmartRoutingService.calculate_technician_workload(db, user.id)
            workload_score = max(0.0, 40.0 - (total_workload * 8.0))

            # 3. SLA Suitability Score (Max 20 pts)
            is_high_priority = priority in (IncidentPriority.CRITICAL, IncidentPriority.HIGH)
            if is_high_priority:
                if skill_level >= 4 and total_workload <= 2:
                    sla_score = 20.0
                    sla_reason = f"Đạt tiêu chuẩn đáp ứng SLA ưu tiên cao ({priority.value})"
                else:
                    sla_score = 10.0
                    sla_reason = f"Đáp ứng SLA tiêu chuẩn ưu tiên cao ({priority.value})"
            else:
                if total_workload <= 3:
                    sla_score = 15.0
                    sla_reason = "Phù hợp tiến độ xử lý thông thường"
                else:
                    sla_score = 10.0
                    sla_reason = "Đang gánh khối lượng công việc vừa phải"

            total_score = skill_score + workload_score + sla_score

            reasons = [
                f"✓ Skill {category.value}: {skill_level}/5 (+{int(skill_score)} điểm)",
                f"✓ Workload hiện tại: {total_workload} công việc active (+{int(workload_score)} điểm)",
                f"✓ SLA suitability: {sla_reason} (+{int(sla_score)} điểm)",
            ]

            recommendations.append(TechnicianRecommendation(
                user_id=user.id,
                full_name=user.full_name,
                email=user.email,
                role=user.role,
                total_score=round(total_score, 1),
                skill_score=round(skill_score, 1),
                workload_score=round(workload_score, 1),
                sla_score=round(sla_score, 1),
                active_workload=total_workload,
                reasons=reasons,
            ))

        # Rank by total score descending
        recommendations.sort(key=lambda r: r.total_score, reverse=True)
        return recommendations
