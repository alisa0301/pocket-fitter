import logging

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.schemas import ChatIn, ChatOut
from app.services import gemini, scripted

router = APIRouter()
log = logging.getLogger(__name__)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "llm": "gemini" if settings.gemini_api_key else "scripted"}


@router.post("/chat", response_model=ChatOut)
async def chat(body: ChatIn) -> ChatOut:
    if not settings.gemini_api_key:
        return scripted.reply(body.messages)
    try:
        return await gemini.reply(body.messages)
    except Exception as exc:  # surface a clean error to the UI
        log.exception("Gemini call failed")
        raise HTTPException(status_code=502, detail="LLM request failed") from exc
