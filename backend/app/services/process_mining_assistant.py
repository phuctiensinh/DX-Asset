"""Deterministic, read-only Process Mining intents for the assistant."""

import re
from enum import Enum
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.enums import UserRole
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
_CASE_ID = re.compile(r"\bCASE\s*[-#]?\s*(\d+)\b", re.IGNORECASE)
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


def _case_requested(lower_message: str) -> bool:
    return "case" in lower_message or "process case" in lower_message


class ProcessMiningAssistantService:
    """Classifies Process Mining questions and formats service results without inference."""

    @staticmethod
    def detect_intent(message: str) -> Optional[ProcessMiningAssistantIntent]:
        lower = message.lower()
        has_case_id = _CASE_ID.search(message) is not None
        case_requested = _case_requested(lower)

        if case_requested and any(term in lower for term in _DURATION_TERMS):
            return ProcessMiningAssistantIntent.CASE_DURATION
        if case_requested and (has_case_id or any(term in lower for term in _DETAIL_TERMS)):
            return ProcessMiningAssistantIntent.CASE_DETAIL

        if any(term in lower for term in (
            "bottleneck", "bottlenecks", "điểm nghẽn", "diem nghen",
            "bước nào đang chậm", "buoc nao dang cham", "đoạn nào chậm",
            "doan nao cham", "slowest", "process delay",
        )):
            return ProcessMiningAssistantIntent.BOTTLENECKS

        if any(term in lower for term in (
            "biến thể quy trình", "bien the quy trinh", "biến thể quy trình",
            "các biến thể", "cac bien the", "process variants", "process variant",
            "workflow variants", "event sequence variants",
        )):
            return ProcessMiningAssistantIntent.VARIANTS

        if any(term in lower for term in (
            "quy trình hiện tại", "quy trinh hien tai", "tình hình process mining",
            "tinh hinh process mining", "tổng quan quy trình", "tong quan quy trinh",
            "quy trình xử lý sự cố hiện tại", "quy trinh xu ly su co hien tai",
            "quy trình xử lý incident hiện tại", "quy trinh xu ly incident hien tai",
            "process mining summary", "process mining overview", "current process overview",
            "current incident workflow", "process mining status", "process mining",
            "process-mining",
        )):
            return ProcessMiningAssistantIntent.SUMMARY

        # A request for case detail/duration without an ID is still recognized so
        # the assistant asks for an exact ID instead of falling through elsewhere.
        if case_requested and any(term in lower for term in _DURATION_TERMS):
            return ProcessMiningAssistantIntent.CASE_DURATION
        if case_requested and any(term in lower for term in _DETAIL_TERMS):
            return ProcessMiningAssistantIntent.CASE_DETAIL
        return None

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
                detail="Nhân viên không có quyền truy cập dữ liệu Process Mining toàn hệ thống.",
            )

        if intent == ProcessMiningAssistantIntent.SUMMARY:
            return ProcessMiningAssistantService._summary(db)
        if intent == ProcessMiningAssistantIntent.VARIANTS:
            return ProcessMiningAssistantService._variants(db)
        if intent == ProcessMiningAssistantIntent.BOTTLENECKS:
            return ProcessMiningAssistantService._bottlenecks(db)

        match = _CASE_ID.search(message)
        if match is None:
            subject = "thời gian xử lý" if intent == ProcessMiningAssistantIntent.CASE_DURATION else "chi tiết case"
            return ProcessMiningAssistantService._response(
                f"Vui lòng cung cấp Case ID chính xác để tra cứu {subject} (ví dụ: CASE-023).",
                intent,
            )

        case_id = int(match.group(1))
        detail = ProcessMiningService.get_case_detail(db, case_id)
        if detail is None:
            code = ProcessMiningAssistantService._case_code(case_id)
            return ProcessMiningAssistantService._response(
                f"Không tìm thấy {code} trong Process Mining.",
                intent,
                ProcessMiningAssistantService._case_source(case_id),
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
    def _summary(db: Session) -> AssistantChatResponse:
        result = ProcessMiningService.get_summary(db)
        answer = (
            f"Process Mining ghi nhận **{result.total_cases} case** và **{result.total_events} event**. "
            f"Theo định nghĩa hoàn thành hiện tại của service: **{result.completed_cases} case hoàn thành**, "
            f"**{result.incomplete_cases} chưa hoàn thành**. Nguồn event gồm **{result.live_events} LIVE** "
            f"và **{result.backfill_events} BACKFILL**."
        )
        if result.total_cases == 0 or result.total_events == 0:
            answer += "\nDữ liệu hiện tại chưa đủ để mô tả các bước của quy trình."
        if result.observed_flow:
            answer += "\n\nObserved flow có ghi nhận:"
            for edge in result.observed_flow[:5]:
                duration = (
                    f"median {edge.median_duration:g} giây"
                    if edge.median_duration is not None
                    else "chưa có median thời gian"
                )
                answer += f"\n- {edge.from_event.value} → {edge.to_event.value}: {edge.count} observations, {duration}."
        else:
            answer += "\nChưa có observed-flow transition trong tập dữ liệu này."
        notes = [result.cohort.coverage_note]
        if result.data_quality.ambiguous_timestamp_events:
            notes.append(
                f"Có {result.data_quality.ambiguous_timestamp_events} event có timestamp mơ hồ; "
                "các khoảng thời gian liên quan không được dùng để kết luận."
            )
        answer += "\n\nLưu ý dữ liệu: " + " ".join(notes)
        return ProcessMiningAssistantService._response(
            answer,
            ProcessMiningAssistantIntent.SUMMARY,
            AssistantSource(
                type="process_mining",
                name="Process Mining Summary",
                details="/intelligence/process-mining",
            ),
        )

    @staticmethod
    def _variants(db: Session) -> AssistantChatResponse:
        result = ProcessMiningService.get_variants(db)
        if result.variants:
            rows = [
                f"- {' → '.join(event.value for event in variant.event_sequence)}: "
                f"{variant.case_count} case ({variant.percentage:.1f}%)."
                for variant in result.variants[:10]
            ]
            answer = (
                f"Có {len(result.variants)} biến thể trong tập dữ liệu có event "
                f"(mẫu số {result.denominator_cases} case):\n" + "\n".join(rows)
            )
        else:
            answer = "Chưa có event trong tập dữ liệu này để xác định biến thể quy trình."
        answer += f"\n\nLưu ý dữ liệu: {result.cohort.coverage_note}"
        return ProcessMiningAssistantService._response(
            answer,
            ProcessMiningAssistantIntent.VARIANTS,
            AssistantSource(
                type="process_mining",
                name="Process Mining Variants",
                details="/intelligence/process-mining",
            ),
        )

    @staticmethod
    def _bottlenecks(db: Session) -> AssistantChatResponse:
        min_sample = 5  # ProcessMiningService/API current default threshold.
        result = ProcessMiningService.get_bottlenecks(db, min_sample=min_sample)
        if result:
            lines = [
                f"- {item.from_event.value} → {item.to_event.value}: {item.count} observations, "
                f"median {item.median_duration:g} giây."
                for item in result[:10]
            ]
            answer = "Process Mining ghi nhận các bottleneck đạt ngưỡng phân tích:\n" + "\n".join(lines)
        else:
            answer = (
                "Hiện chưa có đủ dữ liệu để xác định bottleneck: không có transition nào đạt "
                f"ngưỡng tối thiểu {min_sample} observations của service."
            )
        return ProcessMiningAssistantService._response(
            answer,
            ProcessMiningAssistantIntent.BOTTLENECKS,
            AssistantSource(
                type="process_mining",
                name="Process Mining Bottlenecks",
                details="/intelligence/process-mining",
            ),
        )

    @staticmethod
    def _case_code(case_id: int) -> str:
        return f"CASE-{case_id:03d}"

    @staticmethod
    def _case_source(case_id: int) -> AssistantSource:
        return AssistantSource(
            type="process_mining",
            id=case_id,
            code=ProcessMiningAssistantService._case_code(case_id),
            name="Process Mining Case",
            details="/intelligence/process-mining",
        )

    @staticmethod
    def _case_duration(detail: ProcessCaseDetail) -> AssistantChatResponse:
        code = ProcessMiningAssistantService._case_code(detail.case_id)
        if detail.processing_time is None:
            answer = (
                f"{code} hiện chưa có processing time hoàn chỉnh theo Process Mining "
                "(service trả về null), nên dữ liệu hiện tại chưa đủ để kết luận thời gian xử lý. "
                "Incident chỉ được tính hoàn thành khi có event CLOSED; Maintenance khi có event COMPLETED."
            )
        else:
            answer = f"Processing time của {code} theo Process Mining là **{detail.processing_time:g} giây**."
        return ProcessMiningAssistantService._response(
            answer,
            ProcessMiningAssistantIntent.CASE_DURATION,
            ProcessMiningAssistantService._case_source(detail.case_id),
        )

    @staticmethod
    def _case_detail(detail: ProcessCaseDetail) -> AssistantChatResponse:
        code = ProcessMiningAssistantService._case_code(detail.case_id)
        answer = f"Timeline đã được ghi nhận của {code} ({detail.case_type.value}):"
        if detail.events:
            for event in detail.events:
                if event.from_status is not None and event.to_status is not None:
                    status = f" ({event.from_status} → {event.to_status})"
                elif event.to_status is not None:
                    status = f" (recorded status: {event.to_status})"
                elif event.from_status is not None:
                    status = f" (from status: {event.from_status})"
                else:
                    status = ""
                answer += (
                    f"\n{event.sequence}. {event.event_type.value}{status} "
                    f"[{event.source.value}]"
                )
        else:
            answer += "\nChưa có event nào được ghi nhận cho case này."
        if detail.processing_time is None:
            answer += "\nProcessing time: chưa có giá trị hoàn chỉnh từ Process Mining."
        else:
            answer += f"\nProcessing time: {detail.processing_time:g} giây."
        answer += "\nNguồn LIVE/BACKFILL được hiển thị theo từng event; BACKFILL không được xem là LIVE."
        return ProcessMiningAssistantService._response(
            answer,
            ProcessMiningAssistantIntent.CASE_DETAIL,
            ProcessMiningAssistantService._case_source(detail.case_id),
        )
