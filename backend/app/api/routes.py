import logging

from fastapi import APIRouter, HTTPException
from google.genai import errors as genai_errors

from app.core.config import settings
from app.decision import engine
from app.schemas import ChatIn, ChatOut, PlayerProfile, Recommendation
from app.services import gemini, scripted

router = APIRouter()
log = logging.getLogger(__name__)


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "llm": "gemini" if settings.gemini_api_key else "scripted",
        "decision_engine": engine.engine_name(),
    }


@router.post("/chat", response_model=ChatOut)
async def chat(body: ChatIn) -> ChatOut:
    try:
        out = await gemini.reply(body.messages) if settings.gemini_api_key else scripted.reply(
            body.messages
        )
    except genai_errors.APIError as exc:
        log.exception("Gemini call failed")
        raise HTTPException(status_code=502, detail=f"Gemini {exc.code}: {exc.message}") from exc
    except Exception as exc:
        log.exception("Gemini call failed")
        raise HTTPException(status_code=502, detail=f"LLM error: {type(exc).__name__}") from exc
    if out.profile is not None:
        out.recommendation = await engine.decide(out.profile)
    return out


@router.post("/decide", response_model=Recommendation)
async def decide(profile: PlayerProfile) -> Recommendation:
    """Run the decision engine directly on a profile (handy for testing / comparing engines)."""
    return await engine.decide(profile)
