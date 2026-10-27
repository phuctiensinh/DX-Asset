"""
AI report over Process Mining results (report only — nothing here writes to the database).

All metrics come from ProcessMiningService (summary, bottlenecks, rework, conformance). The backend
turns them into self-contained Vietnamese findings, each sentence carrying its own numbers, and the
local Ollama model only rewrites those findings into a report: a small model mixes up numbers when it
has to pair raw metrics with their meaning itself. When Ollama is off, slow or returns bad output, the
same findings are returned as a deterministic report.
"""
import logging
import re
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.labels import vi
from app.schemas.process_mining import (
    DurationStatistics,
    ProcessBottleneck,
    ProcessConformanceMetrics,
    ProcessMiningAIReportResponse,
    ProcessMiningFilters,
    ProcessMiningSummary,
    ProcessReworkMetrics,
)
from app.services.asset_ai import _format_date, _numbers_grounded
from app.services.ollama_client import ollama_chat_json
from app.services.process_mining import ProcessMiningService
from app.services.process_mining_assistant import _duration

logger = logging.getLogger(__name__)

TOP_BOTTLENECKS = 3
MAX_REPORT_CHARS = 2500
MAX_REPORT_SENTENCES = 8
MAX_RECOMMENDATION_CHARS = 300
MAX_RECOMMENDATIONS = 3
# Below this many cases a rate or median is reported but flagged as not enough to draw conclusions
MIN_CONCLUSIVE_CASES = 5

SOURCE_LABELS = {"LIVE": "ghi nhận trực tiếp", "BACKFILL": "tái dựng từ lịch sử"}

SYSTEM_PROMPT = (
    "Bạn là chuyên viên phân tích quy trình của hệ thống quản lý tài sản DX-Asset. "
    "Bạn nhận danh sách NHẬN ĐỊNH đã được hệ thống tính sẵn từ dữ liệu Process Mining (quy trình xử lý phiếu sự cố "
    "và bảo trì) và viết lại thành báo cáo cho quản lý.\n"
    "Quy tắc bắt buộc:\n"
    "1. Mỗi con số phải đi cùng đúng nhận định chứa nó. Không ghép số của nhận định này sang nhận định khác.\n"
    "2. Không thêm con số, bước quy trình, sự kiện hay nhận định nào không có trong danh sách. Không tự tính lại.\n"
    "3. Không đoán nguyên nhân (ví dụ do nhân viên, do đào tạo, do thiết bị) vì dữ liệu không chứng minh nguyên nhân.\n"
    "4. Giữ nguyên các câu cảnh báo 'chưa đủ để kết luận' và 'chưa đủ dữ liệu'.\n"
    "Chỉ trả về một đối tượng JSON với đúng 2 khóa:\n"
    '- "report": 5 đến 8 câu tiếng Việt, văn bản thuần (không Markdown), theo thứ tự: tổng quan, điểm nghẽn, '
    "làm lại, tuân thủ quy trình chuẩn, lưu ý chất lượng dữ liệu.\n"
    '- "recommendations": mảng tối đa 3 đề xuất, mỗi mục 1 câu tiếng Việt, chỉ nêu việc cần rà soát hoặc kiểm tra '
    "dựa trên các nhận định."
)


def _limit_sentences(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
    return " ".join(sentences[:MAX_REPORT_SENTENCES])


def _pct(rate: Optional[float]) -> str:
    return f"{rate * 100:.1f}%" if rate is not None else "không xác định"


def _step(bottleneck: ProcessBottleneck) -> str:
    return f"{vi(bottleneck.from_event, 'ProcessEventType')} → {vi(bottleneck.to_event, 'ProcessEventType')}"


def _median_finding(label: str, stats: DurationStatistics) -> str:
    if not stats.count or stats.median is None:
        return f"Chưa đủ dữ liệu để tính {label}."
    return f"{label[0].upper()}{label[1:]} có trung vị {_duration(stats.median)}, tính trên {stats.count} phiếu."


class ProcessMiningReportData:
    """The four Process Mining results the report is built from, computed once by ProcessMiningService."""

    def __init__(self, db: Session, filters: ProcessMiningFilters, min_sample: int):
        self.filters = filters
        self.min_sample = min_sample
        self.summary: ProcessMiningSummary = ProcessMiningService.get_summary(db, filters)
        self.bottlenecks: List[ProcessBottleneck] = ProcessMiningService.get_bottlenecks(
            db, filters, min_sample=min_sample
        )[:TOP_BOTTLENECKS]
        self.rework: ProcessReworkMetrics = ProcessMiningService.get_rework(db, filters)
        self.conformance: ProcessConformanceMetrics = ProcessMiningService.get_conformance(db, filters)


def _scope(filters: ProcessMiningFilters) -> str:
    parts = [f"loại phiếu {vi(filters.case_type, 'ProcessCaseType').lower() if filters.case_type else 'tất cả'}"]
    if filters.source is not None:
        parts.append(f"nguồn dữ liệu {SOURCE_LABELS.get(filters.source.value, filters.source.value)}")
    if filters.date_from is not None:
        parts.append(f"từ ngày {_format_date(filters.date_from.date())}")
    if filters.date_to is not None:
        parts.append(f"đến trước ngày {_format_date(filters.date_to.date())}")
    return ", ".join(parts)


def build_findings(data: ProcessMiningReportData) -> List[str]:
    """Self-contained factual sentences, grouped in report order. Every number comes from ProcessMiningService."""
    s = data.summary
    q = s.data_quality
    findings = [
        f"Trong phạm vi đã chọn ({_scope(data.filters)}) có {s.total_cases} phiếu: "
        f"{s.completed_cases} phiếu đã hoàn tất và {s.incomplete_cases} phiếu chưa hoàn tất.",
        _median_finding("thời gian xử lý từ lúc tạo đến khi hoàn tất", s.processing_time),
        _median_finding("thời gian từ lúc tạo đến thao tác đầu tiên", s.first_action_time),
    ]
    if s.completed_cases < MIN_CONCLUSIVE_CASES:
        findings.append("Số phiếu đã hoàn tất còn ít nên thời gian xử lý chưa đủ để kết luận.")

    if data.bottlenecks:
        for rank, b in enumerate(data.bottlenecks, start=1):
            label = "Bước chậm nhất" if rank == 1 else "Bước chậm tiếp theo"
            findings.append(
                f"{label} là '{_step(b)}' với thời gian trung vị {_duration(b.median_duration)}, "
                f"lâu nhất {_duration(b.max_duration)}, quan sát {b.count} lần."
            )
    else:
        findings.append(f"Chưa có bước chuyển nào đủ {data.min_sample} lần quan sát nên chưa đủ dữ liệu để xác định điểm nghẽn.")

    r = data.rework
    if r.eligible_cases:
        findings.append(
            f"Có {r.total_rework_cases} trên {r.eligible_cases} phiếu sự cố bị mở xử lý lại sau khi đã giải quyết "
            f"(tỷ lệ làm lại {_pct(r.rework_rate)})."
        )
        if r.eligible_cases < MIN_CONCLUSIVE_CASES:
            findings.append("Số phiếu sự cố dùng để tính tỷ lệ làm lại còn ít nên chưa đủ để kết luận.")
    else:
        findings.append("Chưa đủ dữ liệu để đánh giá tình trạng làm lại.")

    c = data.conformance
    if c.eligible_cases:
        findings.append(
            f"Có {c.conforming_cases} trên {c.eligible_cases} phiếu sự cố đi đúng quy trình chuẩn "
            f"(tỷ lệ tuân thủ {_pct(c.conformance_rate)}) và {c.deviating_cases} phiếu có bước chuyển trạng thái sai quy trình."
        )
        deviation_steps = sorted({
            f"{vi(d.from_status, 'IncidentStatus')} → {vi(d.to_status, 'IncidentStatus')}" for d in c.deviations
        })
        if deviation_steps:
            findings.append(f"Các bước chuyển sai quy trình gặp phải: {'; '.join(deviation_steps[:5])}.")
        if c.eligible_cases < MIN_CONCLUSIVE_CASES:
            findings.append("Số phiếu sự cố dùng để đánh giá tuân thủ còn ít nên chưa đủ để kết luận.")
    else:
        findings.append("Chưa đủ dữ liệu để đánh giá mức tuân thủ quy trình chuẩn.")

    if q.backfill_events:
        findings.append(
            f"Có {q.backfill_events} trên {s.total_events} sự kiện được tái dựng từ lịch sử nên một số bước có thể bị thiếu."
        )
    return findings


def build_context(data: ProcessMiningReportData) -> str:
    return "CÁC NHẬN ĐỊNH ĐÃ TÍNH:\n" + "\n".join(f"- {finding}" for finding in build_findings(data))


def _fallback(data: ProcessMiningReportData) -> Tuple[str, List[str]]:
    if data.summary.total_cases == 0:
        return (
            "Không có phiếu nào trong phạm vi đã chọn nên chưa đủ dữ liệu để phân tích quy trình.",
            ["Mở rộng khoảng thời gian hoặc bỏ bớt bộ lọc để có đủ dữ liệu phân tích."],
        )

    recommendations: List[str] = []
    if data.bottlenecks:
        recommendations.append(f"Rà soát bước '{_step(data.bottlenecks[0])}' vì đây là bước chuyển có thời gian trung vị dài nhất.")
    if data.rework.total_rework_cases:
        recommendations.append(
            f"Xem lại {data.rework.total_rework_cases} phiếu bị mở xử lý lại sau khi đã giải quyết để kiểm tra chất lượng xử lý."
        )
    if data.conformance.deviating_cases:
        recommendations.append(f"Kiểm tra {data.conformance.deviating_cases} phiếu có bước chuyển trạng thái sai quy trình chuẩn.")
    if not recommendations:
        recommendations.append("Tiếp tục thu thập dữ liệu thao tác để có đủ cơ sở đánh giá quy trình.")

    return " ".join(build_findings(data)), recommendations[:MAX_RECOMMENDATIONS]


class ProcessMiningAIService:
    @staticmethod
    def generate_report(db: Session, filters: ProcessMiningFilters, min_sample: int = 5) -> ProcessMiningAIReportResponse:
        data = ProcessMiningReportData(db, filters, min_sample)

        def response(report: str, recommendations: List[str], source: str) -> ProcessMiningAIReportResponse:
            return ProcessMiningAIReportResponse(
                report=report,
                recommendations=recommendations,
                total_cases=data.summary.total_cases,
                source=source,
            )

        # Nothing to interpret: skip the model so it cannot invent a process from an empty context
        if data.summary.total_cases == 0:
            return response(*_fallback(data), "RULE_BASED")

        context = build_context(data)
        result = ollama_chat_json(SYSTEM_PROMPT, context)
        if result:
            raw_report = result.get("report") or ""
            # The small model sometimes returns the report as a list of paragraphs
            if isinstance(raw_report, list):
                raw_report = " ".join(str(part).strip() for part in raw_report if str(part).strip())
            report = _limit_sentences(str(raw_report))[:MAX_REPORT_CHARS]
            raw_recs = result.get("recommendations")
            recs = [str(r).strip()[:MAX_RECOMMENDATION_CHARS] for r in raw_recs if str(r).strip()] if isinstance(raw_recs, list) else []
            recs = recs[:MAX_RECOMMENDATIONS]
            if report and _numbers_grounded(" ".join([report, *recs]), context):
                return response(report, recs, "AI")
            logger.warning(f"Ollama process mining report rejected (empty or ungrounded numbers): {str(result)[:300]}")

        return response(*_fallback(data), "RULE_BASED")
