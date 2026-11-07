import logging

from fastapi import APIRouter, HTTPException
from google.genai import errors as genai_errors

from app.core.config import settings
from app.db import get_db
from app.schemas import ChatIn, ChatOut, GolferProfile, SimilarGolfers
from app.services import catalog, fittings, gemini, scripted, similar

router = APIRouter()
log = logging.getLogger(__name__)


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "llm": "gemini" if settings.gemini_api_key else "scripted",
        "db": "mongodb" if get_db() is not None else "none",
    }


@router.get("/products")
async def products() -> dict:
    """Takomo iron catalog: heads, shafts, grips, length/lie options and fitting rules."""
    return await catalog.load()


@router.post("/similar", response_model=SimilarGolfers)
async def similar_golfers(profile: GolferProfile, k: int = 50) -> SimilarGolfers:
    """What fitted the k most similar golfers in Takomo's data (Atlas Vector Search)."""
    return await similar.find(profile, k=max(5, min(k, 200)))


@router.get("/fittings/{fitting_id}")
async def get_fitting(fitting_id: str) -> dict:
    doc = await fittings.get(fitting_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Fitting not found")
    return doc


@router.post("/chat", response_model=ChatOut)
async def chat(body: ChatIn) -> ChatOut:
    out = await _reply(body)
    out.fitting_id = await fittings.save(body.fitting_id, body.messages, out)
    return out


async def _reply(body: ChatIn) -> ChatOut:
    if not settings.gemini_api_key:
        return scripted.reply(body.messages)
    try:
        return await gemini.reply(body.messages, recommended=body.recommended)
    except genai_errors.APIError as exc:
        log.exception("Gemini call failed")
        raise HTTPException(status_code=502, detail=f"Gemini {exc.code}: {exc.message}") from exc
    except Exception as exc:
        log.exception("Gemini call failed")
        raise HTTPException(status_code=502, detail=f"LLM error: {type(exc).__name__}") from exc
