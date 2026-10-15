"""Deterministic, read-only Process Mining intents for the assistant."""

import re
from enum import Enum
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.labels import vi
from app.models.enums import UserRole
from app.models.incident import Incident
from app.models.maintenance import Maintenance
from app.models.process_case import ProcessCase
from app.models.user import User
from app.schemas.assistant import AssistantChatResponse, AssistantSource
from app.schemas.process_mining import ProcessCaseDetail
from app.services.process_mining import ProcessMiningService


class ProcessMiningAssistantIntent(str, Enum):
    SUMMARY = "PROCESS_MINING_SUMMARY"
    VARIANTS = "PROCESS_MINING_VARIANTS"
    BOTTLENECKS = "PROCESS_MINING_BOTTLENECKS"
    CASE_DURATION = "PROCESS_MINING_CASE_DURATION"
    CASE_DETAIL = "PROCESS_MINING_CASE_DETAIL"


_ANALYTICS_ROLES = {
    UserRole.ADMIN,
    UserRole.IT_ASSET_MANAGER,
    UserRole.MANAGER,
}
# Legacy internal reference ("CASE-023"), still accepted as input
_CASE_ID = re.compile(r"\bCASE\s*[-#]?\s*(\d+)\b", re.IGNORECASE)
# Business ticket codes shown to users: INC-2026-001, MNT-T-006B29, ...
_TICKET_CODE = re.compile(r"\b((?:INC|MNT)-[A-Z0-9][A-Z0-9.\-]*)", re.IGNORECASE)
_DURATION_TERMS = (
    "mất bao lâu", "mat bao lau", "bao lâu để xử lý", "bao lau de xu ly",
    "thời gian xử lý", "thoi gian xu ly", "mất thời gian", "mat thoi gian",
    "processing time", "case duration", "how long", "duration of",
)
_DETAIL_TERMS = (
    "chi tiết", "chi tiet", "đã trải qua", "da trai qua", "đi qua những bước",
    "di qua nhung buoc", "đã đi qua", "da di qua", "timeline", "case detail",
    "case history", "what steps", "which steps", "steps in",
)
# For ticket codes "chi tiết" alone is not enough: "chi tiết phiếu INC-..." is the ticket-detail intent
_JOURNEY_TERMS = (
    "đã trải qua", "da trai qua", "đi qua những bước", "di qua nhung buoc", "đã đi qua",
    "da di qua", "những bước nào", "nhung buoc nao", "hành trình", "hanh trinh", "timeline",
)


def _case_requested(lower_message: str) -> bool:
    return "case" in lower_message or "process case" in lower_message


def _duration(seconds: float) -> str:
    """Human readable Vietnamese duration, e.g. '2 ngày 3 giờ' or '40 giây'."""
    total = max(0, int(seconds))
    days, rest = divmod(total, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, secs = divmod(rest, 60)
    parts = []
    if days:
        parts.append(f"{days} ngày")
    if hours:
        parts.append(f"{hours} giờ")
    if minutes and len(parts) < 2:
        parts.append(f"{minutes} phút")
    return " ".join(parts) if parts else f"{secs} giây"


class ProcessMiningAssistantService:
    """Classifies Process Mining questions and formats service results without inference."""

    @staticmethod
    def detect_intent(message: str) -> Optional[ProcessMiningAssistantIntent]:
        lower = message.lower()
        has_case_id = _CASE_ID.search(message) is not None
        case_requested = _case_requested(lower)
        has_ticket = _TICKET_CODE.search(message) is not None

        if case_requested and any(term in lower for term in _DURATION_TERMS):
            return ProcessMiningAssistantIntent.CASE_DURATION
        if case_requested and (has_case_id or any(term in lower for term in _DETAIL_TERMS)):
            return ProcessMiningAssistantIntent.CASE_DETAIL
        if has_ticket and any(term in lower for term in _DURATION_TERMS):
            return ProcessMiningAssistantIntent.CASE_DURATION
        if has_ticket and any(term in lower for term in _JOURNEY_TERMS):
            return ProcessMiningAssistantIntent.CASE_DETAIL

        if any(term in lower for term in (
            "bottleneck", "bottlenecks", "điểm nghẽn", "diem nghen",
            "bước nào đang chậm", "buoc nao dang cham", "đoạn nào chậm",
            "doan nao cham", "chậm ở bước nào", "cham o buoc nao", "slowest", "process delay",
        )):
            return ProcessMiningAssistantIntent.BOTTLENECKS

        if any(term in lower for term in (
            "biến thể quy trình", "bien the quy trinh",
            "các biến thể", "cac bien the", "luồng xử lý nào", "luong xu ly nao",
            "process variants", "process variant", "workflow variants", "event sequence variants",
        )):
            return ProcessMiningAssistantIntent.VARIANTS

        if any(term in lower for term in (
            "quy trình hiện tại", "quy trinh hien tai", "tình hình process mining",
            "tinh hinh process mining", "tổng quan quy trình", "tong quan quy trinh",
            "quy trình xử lý sự cố hiện tại", "quy trinh xu ly su co hien tai",
            "quy trình xử lý incident hiện tại", "quy trinh xu ly incident hien tai",
            "phân tích quy trình", "phan tich quy trinh",
            "process mining summary", "process mining overview", "current process overview",
            "current incident workflow", "process mining status", "process mining",
            "process-mining",
        )):
            return ProcessMiningAssistantIntent.SUMMARY

        # A request for case detail/duration without an ID is still recognized so
        # the assistant asks for an exact code instead of falling through elsewhere.
        if case_requested and any(term in lower for term in _DURATION_TERMS):
            return ProcessMiningAssistantIntent.CASE_DURATION
        if case_requested and any(term in lower for term in _DETAIL_TERMS):
            return ProcessMiningAssistantIntent.CASE_DETAIL
        return None

    @staticmethod
    def _resolve_case_id(db: Session, message: str) -> tuple[Optional[int], Optional[str]]:
        """Return (process case id, code the user asked about). The id is None when nothing matches."""
        legacy = _CASE_ID.search(message)
        if legacy is not None:
            return int(legacy.group(1)), legacy.group(0).upper()
        ticket = _TICKET_CODE.search(message)
        if ticket is None:
            return None, None
        code = ticket.group(1).rstrip(".").upper()
        incident = db.query(Incident.id).filter(func.upper(Incident.ticket_code) == code).first()
        if incident is not None:
            case = db.query(ProcessCase.id).filter(ProcessCase.incident_id == incident.id).first()
            return (case.id if case else None), code
        maintenance = db.query(Maintenance.id).filter(func.upper(Maintenance.maintenance_code) == code).first()
        if maintenance is not None:
            case = db.query(ProcessCase.id).filter(ProcessCase.maintenance_id == maintenance.id).first()
            return (case.id if case else None), code
        return None, code

    @staticmethod
    def process_chat(
        db: Session,
        current_user: User,
        message: str,
    ) -> Optional[AssistantChatResponse]:
        intent = ProcessMiningAssistantService.detect_intent(message)
        if intent is None:
            return None

        if current_user.role not in _ANALYTICS_ROLES:
            raise HTTPException(
                status_code=403,
                detail="Nhân viên không có quyền xem số liệu phân tích quy trình toàn hệ thống.",
            )

        if intent == ProcessMiningAssistantIntent.SUMMARY:
            return ProcessMiningAssistantService._summary(db)
        if intent == ProcessMiningAssistantIntent.VARIANTS:
            return ProcessMiningAssistantService._variants(db)
        if intent == ProcessMiningAssistantIntent.BOTTLENECKS:
            return ProcessMiningAssistantService._bottlenecks(db)

        case_id, requested_code = ProcessMiningAssistantService._resolve_case_id(db, message)
        if requested_code is None:
            subject = "thời gian xử lý" if intent == ProcessMiningAssistantIntent.CASE_DURATION else "các bước đã diễn ra"
            return ProcessMiningAssistantService._response(
                f"Vui lòng cung cấp mã phiếu để tra cứu {subject} (ví dụ: INC-2026-001).",
                intent,
            )

        detail = ProcessMiningService.get_case_detail(db, case_id) if case_id is not None else None
        if detail is None:
            return ProcessMiningAssistantService._response(
                f"Không tìm thấy phiếu {requested_code} trong dữ liệu phân tích quy trình.",
                intent,
            )
        if intent == ProcessMiningAssistantIntent.CASE_DURATION:
            return ProcessMiningAssistantService._case_duration(detail)
        return ProcessMiningAssistantService._case_detail(detail)

    @staticmethod
    def _response(
        answer: str,
        intent: ProcessMiningAssistantIntent,
        source: Optional[AssistantSource] = None,
    ) -> AssistantChatResponse:
        return AssistantChatResponse(
            answer=answer,
            intent=intent.value,
            sources=[source] if source is not None else [],
            is_fallback=True,
        )

    @staticmethod
    def _page_source(name: str) -> AssistantSource:
        return AssistantSource(type="process_mining", name=name, details="/intelligence/process-mining")

    @staticmethod
    def _summary(db: Session) -> AssistantChatResponse:
        result = ProcessMiningService.get_summary(db)
        answer = (
            f"Hệ thống đang phân tích **{result.total_cases} phiếu** với **{result.total_events} bước thao tác** đã ghi nhận: "
            f"**{result.completed_cases} phiếu đã hoàn tất**, **{result.incomplete_cases} phiếu chưa hoàn tất**. "
            f"Trong đó **{result.live_events} bước được ghi nhận trực tiếp** và "
            f"**{result.backfill_events} bước được tái dựng từ dữ liệu cũ**."
        )
        if result.total_cases == 0 or result.total_events == 0:
            answer += "\nDữ liệu hiện tại chưa đủ để mô tả các bước của quy trình."
        if result.observed_flow:
            answer += "\n\nCác bước chuyển tiếp thường gặp:"
            for edge in result.observed_flow[:5]:
                duration = (
                    f"thường mất {_duration(edge.median_duration)}"
                    if edge.median_duration is not None
                    else "chưa đủ dữ liệu thời gian"
                )
                answer += f"\n- {vi(edge.from_event)} → {vi(edge.to_event)}: {edge.count} lượt, {duration}."
        else:
            answer += "\nChưa có bước chuyển tiếp nào trong dữ liệu hiện tại."
        notes = ["các bước tái dựng từ dữ liệu cũ có thể không đầy đủ."]
        if result.data_quality.ambiguous_timestamp_events:
            notes.append(
                f"Có {result.data_quality.ambiguous_timestamp_events} bước không rõ thời điểm chính xác "
                "nên không được dùng để tính thời gian."
            )
        answer += "\n\nLưu ý: " + " ".join(notes)
        return ProcessMiningAssistantService._response(
            answer, ProcessMiningAssistantIntent.SUMMARY, ProcessMiningAssistantService._page_source("Phân tích quy trình: tổng quan")
        )

    @staticmethod
    def _variants(db: Session) -> AssistantChatResponse:
        result = ProcessMiningService.get_variants(db)
        if result.variants:
            rows = [
                f"- Luồng {index}: {' → '.join(vi(event) for event in variant.event_sequence)} "
                f"({variant.case_count} phiếu, {variant.percentage:.1f}%)."
                for index, variant in enumerate(result.variants[:10], start=1)
            ]
            answer = (
                f"Có {len(result.variants)} luồng xử lý khác nhau trên tổng số {result.denominator_cases} phiếu:\n"
                + "\n".join(rows)
            )
        else:
            answer = "Chưa có dữ liệu để xác định các luồng xử lý."
        answer += "\n\nLưu ý: các bước tái dựng từ dữ liệu cũ có thể không đầy đủ."
        return ProcessMiningAssistantService._response(
            answer, ProcessMiningAssistantIntent.VARIANTS, ProcessMiningAssistantService._page_source("Phân tích quy trình: các luồng xử lý")
        )

    @staticmethod
    def _bottlenecks(db: Session) -> AssistantChatResponse:
        min_sample = 5  # ProcessMiningService/API current default threshold.
        result = ProcessMiningService.get_bottlenecks(db, min_sample=min_sample)
        if result:
            ranked = sorted(result, key=lambda item: item.median_duration, reverse=True)[:10]
            lines = [
                f"- {vi(item.from_event)} → {vi(item.to_event)}: {item.count} lượt, "
                f"thường mất {_duration(item.median_duration)}."
                for item in ranked
            ]
            answer = "Các bước chuyển tiếp mất nhiều thời gian nhất (xếp từ chậm nhất):\n" + "\n".join(lines)
        else:
            answer = (
                "Chưa đủ dữ liệu để xác định bước bị chậm: chưa có bước chuyển tiếp nào "
                f"đạt tối thiểu {min_sample} lượt."
            )
        return ProcessMiningAssistantService._response(
            answer, ProcessMiningAssistantIntent.BOTTLENECKS, ProcessMiningAssistantService._page_source("Phân tích quy trình: bước bị chậm")
        )

    @staticmethod
    def _case_label(detail: ProcessCaseDetail) -> str:
        return detail.reference_code or "phiếu này"

    @staticmethod
    def _case_source(detail: ProcessCaseDetail) -> AssistantSource:
        return AssistantSource(
            type="process_mining",
            id=detail.case_id,
            code=detail.reference_code,
            name=detail.title or "Hành trình xử lý phiếu",
            details="/intelligence/process-mining",
        )

    @staticmethod
    def _case_duration(detail: ProcessCaseDetail) -> AssistantChatResponse:
        label = ProcessMiningAssistantService._case_label(detail)
        if detail.processing_time is None:
            answer = (
                f"Phiếu {label} chưa hoàn tất nên chưa tính được tổng thời gian xử lý. "
                "Phiếu sự cố được tính hoàn tất khi được đóng; phiếu bảo trì khi được đánh dấu hoàn thành."
            )
        else:
            answer = f"Tổng thời gian xử lý phiếu {label} là **{_duration(detail.processing_time)}**."
        return ProcessMiningAssistantService._response(
            answer, ProcessMiningAssistantIntent.CASE_DURATION, ProcessMiningAssistantService._case_source(detail)
        )

    @staticmethod
    def _case_detail(detail: ProcessCaseDetail) -> AssistantChatResponse:
        label = ProcessMiningAssistantService._case_label(detail)
        answer = f"Các bước phiếu {label} ({vi(detail.case_type).lower()}) đã trải qua:"
        if detail.events:
            for index, event in enumerate(detail.events, start=1):
                # The same code (IN_PROGRESS, CANCELLED) means different things for incidents and maintenance
                kind = "MaintenanceStatus" if event.event_type.value.startswith("MAINTENANCE_") else "IncidentStatus"
                if event.from_status is not None and event.to_status is not None:
                    status = f" ({vi(event.from_status, kind)} → {vi(event.to_status, kind)})"
                elif event.to_status is not None:
                    status = f" (trạng thái: {vi(event.to_status, kind)})"
                elif event.from_status is not None:
                    status = f" (từ trạng thái: {vi(event.from_status, kind)})"
                else:
                    status = ""
                rebuilt = " — tái dựng từ dữ liệu cũ" if event.source.value == "BACKFILL" else ""
                answer += f"\n{index}. {vi(event.event_type)}{status}{rebuilt}"
        else:
            answer += "\nChưa có bước nào được ghi nhận cho phiếu này."
        if detail.processing_time is None:
            answer += "\nTổng thời gian xử lý: chưa hoàn tất."
        else:
            answer += f"\nTổng thời gian xử lý: {_duration(detail.processing_time)}."
        return ProcessMiningAssistantService._response(
            answer, ProcessMiningAssistantIntent.CASE_DETAIL, ProcessMiningAssistantService._case_source(detail)
        )
