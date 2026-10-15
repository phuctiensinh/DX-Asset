import json
import logging
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def ollama_chat(system_prompt: str, user_content: str, json_mode: bool = False) -> Optional[str]:
    """
    Send one chat request to the local Ollama server.
    Returns the answer text, or None when Ollama is disabled, unreachable, slow or returns an error,
    so callers can always fall back to their rule-based result.
    """
    if not settings.OLLAMA_ENABLED or not settings.OLLAMA_BASE_URL:
        return None

    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    payload: Dict[str, Any] = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
        "options": {"temperature": 0.2},
    }
    if json_mode:
        payload["format"] = "json"

    try:
        timeout_config = httpx.Timeout(float(settings.OLLAMA_TIMEOUT_SECONDS), connect=3.0)
        with httpx.Client(timeout=timeout_config) as client:
            res = client.post(url, json=payload)
        if res.status_code != 200:
            logger.warning(f"Ollama API returned HTTP status {res.status_code}: {res.text}")
            return None
        answer = res.json().get("message", {}).get("content", "").strip()
        return answer or None
    except Exception as e:
        logger.warning(f"Ollama call failed, using rule-based fallback: {e}")
        return None


def ollama_chat_json(system_prompt: str, user_content: str) -> Optional[Dict[str, Any]]:
    """Like ollama_chat, but asks for a JSON object and parses it. Returns None if the output is not valid JSON."""
    answer = ollama_chat(system_prompt, user_content, json_mode=True)
    if not answer:
        return None
    try:
        data = json.loads(answer)
    except json.JSONDecodeError:
        logger.warning(f"Ollama returned invalid JSON: {answer[:200]}")
        return None
    return data if isinstance(data, dict) else None
