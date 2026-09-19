from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.assistant import AssistantChatRequest, AssistantChatResponse
from app.services.ai_assistant import AIAssistantService

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

    return AIAssistantService.process_chat(db, current_user, payload.message)
