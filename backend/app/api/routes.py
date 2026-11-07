import logging

from fastapi import APIRouter, HTTPException
from google.genai import errors as genai_errors

from app.core.config import settings
from app.db import get_db
from app.decision import engine
from app.schemas import ChatIn, ChatOut, PlayerProfile, Recommendation, SimilarGolfers
from app.services import catalog, fittings, gemini, scripted, similar

router = APIRouter()
log = logging.getLogger(__name__)


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "llm": "gemini" if settings.gemini_api_key else "scripted",
        "decision_engine": engine.engine_name(),
        "db": "mongodb" if get_db() is not None else "none",
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
    out.fitting_id = await fittings.save(body.fitting_id, body.messages, out)
    return out


@router.post("/decide", response_model=Recommendation)
async def decide(profile: PlayerProfile) -> Recommendation:
    """Run the decision engine directly on a profile (handy for testing / comparing engines)."""
    return await engine.decide(profile)


@router.post("/similar", response_model=SimilarGolfers)
async def similar_golfers(profile: PlayerProfile, k: int = 50) -> SimilarGolfers:
    """What fitted the k most similar golfers in Takomo's data (Atlas Vector Search)."""
    return await similar.find(profile, k=max(5, min(k, 200)))


@router.get("/products")
async def products() -> dict:
    """Takomo iron catalog: heads, shafts, grips, length/lie options and fitting rules."""
    return await catalog.load()


@router.get("/fittings/{fitting_id}")
async def get_fitting(fitting_id: str) -> dict:
    doc = await fittings.get(fitting_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Fitting not found")
    return doc
