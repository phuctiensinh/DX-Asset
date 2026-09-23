from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.assistant import AssistantChatRequest, AssistantChatResponse
from app.services.ai_assistant import AIAssistantService
from app.models.enums import UserRole

router = APIRouter()

@router.post("/chat", response_model=AssistantChatResponse)
def assistant_chat(
    payload: AssistantChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Process natural language queries regarding enterprise assets, assignments, incidents,
    and history. Returns structured answers backed by real PostgreSQL data.
    Enforces read-only policy and JWT authentication.
    """
    if not payload.message or not payload.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nội dung câu hỏi không được để trống"
        )

    global_query_terms = ("tổng số", "thống kê", "chi phí", "tài sản nào", "thay thế", "ưu tiên", "sla", "kỹ thuật viên", "workload", "khấu hao", "bao nhiêu laptop", "còn đủ", "phòng ban")
    if current_user.role == UserRole.EMPLOYEE and any(term in payload.message.lower() for term in global_query_terms):
        raise HTTPException(status_code=403, detail="Employees cannot access global analytics or optimization queries")

    return AIAssistantService.process_chat(db, current_user, payload.message)
