import re
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.core.config import settings
from app.models.user import User
from app.models.asset import Asset
from app.models.assignment import AssetAssignment
from app.models.incident import Incident
from app.models.department import Department
from app.models.history import AssetHistory
from app.models.enums import AssetStatus, AssignmentStatus, IncidentStatus
from app.schemas.assistant import AssistantChatResponse, AssistantSource

logger = logging.getLogger(__name__)

class AIAssistantService:
    @staticmethod
    def process_chat(db: Session, current_user: User, user_message: str) -> AssistantChatResponse:
        clean_msg = user_message.strip()
        lower_msg = clean_msg.lower()

        # 1. Read-Only Guard & Intent Safety Logic
        # Explicit mutation action triggers
        mutation_action_triggers = [
            "xóa", "delete", "destroy", "drop",
            "tạo mới", "thêm mới", "tạo tài sản", "thêm tài sản", "tạo phiếu", "create", "insert",
            "update", "modify", "sửa thông tin", "sửa phiếu", "thay đổi trạng thái", "sửa trạng thái", "sửa tài sản",
            "cấp phát cho", "cấp phát laptop", "cấp phát tài sản này", "hãy cấp phát", "thực hiện cấp phát",
            "thực hiện thu hồi", "hãy thu hồi", "thu hồi tài sản này",
            "chuyển giao cho", "thực hiện chuyển giao", "thanh lý tài sản", "hủy bỏ"
        ]

        # Phrases that represent Read Queries (even if they contain keywords like "cấp phát")
        read_inquiry_exceptions = [
            "đang được cấp phát", "đang cấp phát", "đã cấp phát", "chưa cấp phát", "chưa được cấp phát",
            "các tài sản cấp phát", "danh sách cấp phát"
        ]

        is_explicit_mutation = any(kw in lower_msg for kw in mutation_action_triggers)
        is_read_exception = any(phrase in lower_msg for phrase in read_inquiry_exceptions)

        if is_explicit_mutation and not is_read_exception:
            return AssistantChatResponse(
                answer=(
                    "Hệ thống Trợ lý AI ở Phase 9 được thiết kế ở chế độ chỉ đọc (Read-Only) để đảm bảo an toàn dữ liệu. "
                    "Tôi chỉ có thể giúp bạn tra cứu, tìm kiếm và tổng hợp thông tin tài sản, không thực hiện các thao tác thay đổi hay xóa dữ liệu trong hệ thống."
                ),
                intent="MUTATION_REJECTED",
                sources=[],
                is_fallback=True,
            )

        # Try Optional AI API Provider if API Key is configured
        if settings.AI_ENABLED and settings.AI_API_KEY:
            try:
                llm_response = AIAssistantService._call_external_llm(db, current_user, clean_msg)
                if llm_response:
                    return llm_response
            except Exception as e:
                logger.warning(f"External AI Provider failed, falling back to rule-based engine: {e}")

        # 2. Rule-Based Intent Processing Engine (100% PostgreSQL real data query)
        return AIAssistantService._process_rule_based_query(db, current_user, clean_msg, lower_msg)

    @staticmethod
    def _process_rule_based_query(db: Session, current_user: User, clean_msg: str, lower_msg: str) -> AssistantChatResponse:
        sources: List[AssistantSource] = []

        # A. Check for specific Asset Code lookup by scanning all word tokens in user message
        tokens = re.findall(r"([a-zA-Z0-9\-_]{3,50})", clean_msg)
        excluded_words = {
            "TÀI", "SẢN", "LAPTOP", "MÁY", "TÍNH", "CHO", "BÁO", "SỰ", "CỐ", "NÀO",
            "BẢO", "TRÌ", "PHÒNG", "BAN", "KHÔNG", "ĐANG", "Ở", "ĐÂU", "VÀ", "TRẠNG", "THÁI", "GÌ", "XEM"
        }
        for token in tokens:
            code_upper = token.upper()
            if code_upper not in excluded_words:
                asset = db.query(Asset).filter(func.upper(Asset.asset_code) == code_upper).first()
                if asset:
                    sources.append(AssistantSource(
                        type="asset", id=asset.id, code=asset.asset_code, name=asset.name, details=f"Status: {asset.status}"
                    ))
                    
                    holder_name = "Chưa có người giữ (Trong kho)"
                    if asset.current_user:
                        holder_name = f"{asset.current_user.full_name} ({asset.current_user.email})"

                    dept_name = asset.department.name if asset.department else "Chưa gán phòng ban"

                    answer = (
                        f"Thông tin tài sản **{asset.name}** (`{asset.asset_code}`):\n"
                        f"- Trạng thái: **{asset.status}**\n"
                        f"- Danh mục: {asset.category}\n"
                        f"- Người đang giữ: **{holder_name}**\n"
                        f"- Phòng ban: {dept_name}\n"
                        f"- Vị trí: {asset.location or 'Chưa xác định'}"
                    )
                    return AssistantChatResponse(answer=answer, intent="ASSET_DETAIL", sources=sources, is_fallback=True)

        # B. Check for Incident Ticket Code lookup (e.g. INC-20260919-0001, INC-001)
        inc_match = re.search(r"(INC-[a-zA-Z0-9\-_]+)", clean_msg, re.IGNORECASE)
        if inc_match:
            ticket_code = inc_match.group(1).upper()
            incident = db.query(Incident).filter(func.upper(Incident.ticket_code) == ticket_code).first()
            if incident:
                sources.append(AssistantSource(
                    type="incident", id=incident.id, code=incident.ticket_code, name=incident.title, details=f"Status: {incident.status}"
                ))
                reporter_name = incident.reporter.full_name if incident.reporter else "N/A"
                it_name = incident.assigned_it.full_name if incident.assigned_it else "Chưa phân công"
                answer = (
                    f"Phiếu sự cố **{incident.ticket_code}** - {incident.title}:\n"
                    f"- Trạng thái: **{incident.status}**\n"
                    f"- Mức độ ưu tiên: {incident.priority}\n"
                    f"- Người báo cáo: {reporter_name}\n"
                    f"- IT xử lý: {it_name}\n"
                    f"- Chi phí sửa chữa: {incident.repair_cost:,.0f} VNĐ\n"
                    f"- Mô tả: {incident.description}"
                )
                return AssistantChatResponse(answer=answer, intent="INCIDENT_DETAIL", sources=sources, is_fallback=True)

        # C. Intent: Assigned Assets Query ("các tài sản đang được cấp phát", "danh sách cấp phát")
        if "đang được cấp phát" in lower_msg or "đang cấp phát" in lower_msg or "đã cấp phát" in lower_msg:
            assigned_assets = db.query(Asset).filter(Asset.status == AssetStatus.ASSIGNED).limit(10).all()
            total_assigned = db.query(func.count(Asset.id)).filter(Asset.status == AssetStatus.ASSIGNED).scalar() or 0
            if assigned_assets:
                asset_list_str = "\n".join([
                    f"- **{a.name}** (`{a.asset_code}`) - Người giữ: **{a.current_user.full_name if a.current_user else 'N/A'}**"
                    for a in assigned_assets
                ])
                for a in assigned_assets:
                    sources.append(AssistantSource(type="asset", id=a.id, code=a.asset_code, name=a.name))
                answer = f"Hệ thống hiện có **{total_assigned}** tài sản đang ở trạng thái cấp phát (ASSIGNED). Dưới đây là các tài sản mới nhất:\n{asset_list_str}"
            else:
                answer = "Hiện tại không có tài sản nào đang ở trạng thái cấp phát."
            return AssistantChatResponse(answer=answer, intent="ASSIGNED_ASSETS_QUERY", sources=sources, is_fallback=True)

        # D. Intent: User's held assets ("Nguyễn Văn A đang giữ tài sản nào", "ai đang giữ tài sản")
        if "đang giữ" in lower_msg or "đang sử dụng" in lower_msg or "ai giữ" in lower_msg:
            users = db.query(User).all()
            target_user = None
            for u in users:
                if u.full_name.lower() in lower_msg or u.email.lower() in lower_msg:
                    target_user = u
                    break
            
            if target_user:
                held_assets = db.query(Asset).filter(Asset.current_user_id == target_user.id).all()
                if held_assets:
                    asset_list_str = "\n".join([f"- **{a.name}** (`{a.asset_code}`) - {a.status}" for a in held_assets])
                    for a in held_assets:
                        sources.append(AssistantSource(type="asset", id=a.id, code=a.asset_code, name=a.name))
                    answer = f"Nhân viên **{target_user.full_name}** ({target_user.email}) hiện đang giữ {len(held_assets)} tài sản:\n{asset_list_str}"
                else:
                    answer = f"Nhân viên **{target_user.full_name}** ({target_user.email}) hiện không giữ tài sản nào."
                return AssistantChatResponse(answer=answer, intent="USER_HELD_ASSETS", sources=sources, is_fallback=True)

        # E. Intent: Unassigned Assets ("tài sản nào chưa cấp phát", "chưa được cấp phát", "đang trong kho")
        if "chưa được cấp phát" in lower_msg or "chưa cấp phát" in lower_msg or "trong kho" in lower_msg or "có sẵn" in lower_msg:
            in_stock_assets = db.query(Asset).filter(Asset.status == AssetStatus.IN_STOCK).limit(10).all()
            total_in_stock = db.query(func.count(Asset.id)).filter(Asset.status == AssetStatus.IN_STOCK).scalar() or 0
            if in_stock_assets:
                asset_list_str = "\n".join([f"- **{a.name}** (`{a.asset_code}`) - Danh mục: {a.category}" for a in in_stock_assets])
                for a in in_stock_assets:
                    sources.append(AssistantSource(type="asset", id=a.id, code=a.asset_code, name=a.name))
                answer = f"Hệ thống hiện có **{total_in_stock}** tài sản đang có sẵn (IN_STOCK) chưa cấp phát. Dưới đây là các tài sản mới nhất:\n{asset_list_str}"
            else:
                answer = "Hiện tại không có tài sản nào ở trạng thái có sẵn (IN_STOCK)."
            return AssistantChatResponse(answer=answer, intent="UNASSIGNED_ASSETS", sources=sources, is_fallback=True)

        # F. Intent: Maintenance & Damaged Assets ("tài sản hỏng", "đang bảo trì", "hư hỏng")
        if "bảo trì" in lower_msg or "hỏng" in lower_msg or "hư hỏng" in lower_msg or "damaged" in lower_msg:
            maint_assets = db.query(Asset).filter(Asset.status.in_([AssetStatus.IN_MAINTENANCE, AssetStatus.DAMAGED])).all()
            if maint_assets:
                list_str = "\n".join([f"- **{a.name}** (`{a.asset_code}`) - Trạng thái: **{a.status}**" for a in maint_assets])
                for a in maint_assets:
                    sources.append(AssistantSource(type="asset", id=a.id, code=a.asset_code, name=a.name))
                answer = f"Có **{len(maint_assets)}** tài sản đang gặp sự cố hỏng hóc hoặc bảo trì:\n{list_str}"
            else:
                answer = "Hiện tại hệ thống không có tài sản nào đang bị hỏng hoặc trong quá trình bảo trì."
            return AssistantChatResponse(answer=answer, intent="MAINTENANCE_ASSETS", sources=sources, is_fallback=True)

        # G. Intent: Active / Pending Incidents ("sự cố nào đang xử lý", "sự cố kỹ thuật", "phiếu sự cố")
        if "sự cố" in lower_msg or "incident" in lower_msg:
            pending_incidents = db.query(Incident).filter(
                Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.IN_REVIEW, IncidentStatus.IN_PROGRESS, IncidentStatus.WAITING_FOR_INFO])
            ).all()
            if pending_incidents:
                list_str = "\n".join([f"- **{inc.ticket_code}**: {inc.title} (Ưu tiên: {inc.priority}, Trạng thái: **{inc.status}**)" for inc in pending_incidents])
                for inc in pending_incidents:
                    sources.append(AssistantSource(type="incident", id=inc.id, code=inc.ticket_code, name=inc.title))
                answer = f"Hiện có **{len(pending_incidents)}** sự cố đang trong quá trình tiếp nhận và xử lý:\n{list_str}"
            else:
                answer = "Hiện tại không có sự cố nào đang trong quá trình xử lý (tất cả đã được giải quyết hoặc đóng)."
            return AssistantChatResponse(answer=answer, intent="PENDING_INCIDENTS", sources=sources, is_fallback=True)

        # H. Intent: Asset Count / Summary ("có bao nhiêu tài sản", "tổng số tài sản", "bao nhiêu laptop")
        if "bao nhiêu" in lower_msg or "tổng số" in lower_msg or "thống kê" in lower_msg:
            total_assets = db.query(func.count(Asset.id)).scalar() or 0
            assigned_count = db.query(func.count(Asset.id)).filter(Asset.status == AssetStatus.ASSIGNED).scalar() or 0
            in_stock_count = db.query(func.count(Asset.id)).filter(Asset.status == AssetStatus.IN_STOCK).scalar() or 0
            maint_count = db.query(func.count(Asset.id)).filter(Asset.status.in_([AssetStatus.IN_MAINTENANCE, AssetStatus.DAMAGED])).scalar() or 0

            answer = (
                f"Thống kê tổng quan tài sản DX-Asset:\n"
                f"- **Tổng số tài sản**: {total_assets}\n"
                f"- **Đang cấp phát**: {assigned_count}\n"
                f"- **Đang có sẵn trong kho**: {in_stock_count}\n"
                f"- **Đang bảo trì/Hỏng**: {maint_count}"
            )
            return AssistantChatResponse(answer=answer, intent="ASSET_SUMMARY_COUNT", sources=sources, is_fallback=True)

        # I. Intent: Asset History ("lịch sử tài sản", "nhật ký gần đây")
        if "lịch sử" in lower_msg or "nhật ký" in lower_msg or "history" in lower_msg:
            histories = db.query(AssetHistory).order_by(AssetHistory.created_at.desc()).limit(5).all()
            if histories:
                history_items = []
                for h in histories:
                    asset = db.query(Asset).filter(Asset.id == h.asset_id).first()
                    asset_info = f"{asset.name} (`{asset.asset_code}`)" if asset else f"Asset #{h.asset_id}"
                    history_items.append(f"- [{h.action_type}] **{asset_info}**: {h.details or 'Không có chi tiết'}")
                    if asset:
                        sources.append(AssistantSource(type="asset", id=asset.id, code=asset.asset_code, name=asset.name))
                answer = "Nhật ký lịch sử biến động tài sản gần đây nhất:\n" + "\n".join(history_items)
            else:
                answer = "Chưa có dữ liệu lịch sử biến động tài sản trong hệ thống."
            return AssistantChatResponse(answer=answer, intent="RECENT_HISTORY", sources=sources, is_fallback=True)

        # J. Check if search query matches any Asset by Name (e.g., "laptop dell", "macbook", "máy in")
        matched_assets = db.query(Asset).filter(
            or_(Asset.name.ilike(f"%{clean_msg}%"), Asset.category.ilike(f"%{clean_msg}%"))
        ).limit(5).all()

        if matched_assets:
            list_str = "\n".join([f"- **{a.name}** (`{a.asset_code}`) - {a.status} ({a.category})" for a in matched_assets])
            for a in matched_assets:
                sources.append(AssistantSource(type="asset", id=a.id, code=a.asset_code, name=a.name))
            answer = f"Tìm thấy **{len(matched_assets)}** tài sản phù hợp với từ khóa **'{clean_msg}'**:\n{list_str}"
            return AssistantChatResponse(answer=answer, intent="SEARCH_ASSETS", sources=sources, is_fallback=True)

        # Default Help Response for unknown queries
        answer = (
            f"Tôi chưa hiểu rõ yêu cầu **'{clean_msg}'**. Bạn có thể thử đặt câu hỏi như:\n"
            f"- *'Có bao nhiêu tài sản đang được cấp phát?'*\n"
            f"- *'Laptop [mã tài sản] đang do ai giữ?'*\n"
            f"- *'Tài sản nào chưa được cấp phát?'*\n"
            f"- *'Tài sản nào đang bị hỏng hoặc bảo trì?'*\n"
            f"- *'Có những sự cố nào đang xử lý?'*\n"
            f"- *'Lịch sử tài sản gần đây?'*"
        )
        return AssistantChatResponse(answer=answer, intent="UNKNOWN_HELP", sources=[], is_fallback=True)

    @staticmethod
    def _call_external_llm(db: Session, current_user: User, user_message: str) -> Optional[AssistantChatResponse]:
        return None
