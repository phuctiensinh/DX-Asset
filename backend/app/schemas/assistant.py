from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel

class ChatMessage(BaseModel):
    role: str
    content: str

class AssistantChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None

class AssistantSource(BaseModel):
    type: str
    id: Optional[int] = None
    code: Optional[str] = None
    name: Optional[str] = None
    details: Optional[str] = None

class AssistantChatResponse(BaseModel):
    answer: str
    intent: str
    sources: List[AssistantSource] = []
    is_fallback: bool = False
    # How the intent was recognised: keyword rules, or the local model choosing from the allowlist
    intent_source: Literal["RULE_BASED", "AI"] = "RULE_BASED"
