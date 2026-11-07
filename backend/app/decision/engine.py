import logging

from app.core.config import settings
from app.decision import gemini_engine, jeff, rules
from app.schemas import PlayerProfile, Recommendation

log = logging.getLogger(__name__)


def engine_name() -> str:
    name = settings.decision_engine
    if name == "auto":
        return "gemini" if settings.gemini_api_key else "rules"
    return name


async def decide(profile: PlayerProfile) -> Recommendation:
    """Pick the final clubs. Any engine failure falls back to the rule-based baseline."""
    name = engine_name()
    if name == "rules":
        return rules.decide(profile)
    try:
        if name == "jeff":
            return await jeff.decide(profile)
        return await gemini_engine.decide(profile)
    except Exception:
        log.exception("Decision engine %s failed; using rules", name)
        return rules.decide(profile)
