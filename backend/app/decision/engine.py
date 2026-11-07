import logging

from app.core.config import settings
from app.decision import gemini_engine, jeff, rules
from app.schemas import PlayerProfile, Recommendation
from app.services import similar

log = logging.getLogger(__name__)


def engine_name() -> str:
    name = settings.decision_engine
    if name == "auto":
        return "gemini" if settings.gemini_api_key else "rules"
    return name


async def decide(profile: PlayerProfile) -> Recommendation:
    """Pick the final clubs. Any engine failure falls back to the rule-based baseline."""
    found = await similar.find(profile)  # Atlas Vector Search, shared by every engine
    name = engine_name()
    if name == "rules":
        return rules.decide(profile, found)
    try:
        if name == "jeff":
            rec = await jeff.decide(profile)
        else:
            rec = await gemini_engine.decide(profile, found)
    except Exception:
        log.exception("Decision engine %s failed; using rules", name)
        return rules.decide(profile, found)
    rec.similar = rec.similar or found
    return rec
