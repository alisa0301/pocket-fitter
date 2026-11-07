"""LLM decision engine: Gemini chooses from the catalog; output is validated against it."""

import json
import logging

from pydantic import BaseModel

from app.catalog import IRON_BY_ID, IRON_SETS, SHAFT_BY_ID, SHAFTS
from app.decision import rules
from app.schemas import PlayerProfile, Recommendation
from app.services.gemini import generate_json

log = logging.getLogger(__name__)

SYSTEM = """\
You are an expert golf club fitter making the FINAL equipment decision.
Pick exactly one iron set and one shaft from the catalog (use their ids), choose the set makeup,
list concrete adjustments (lie, length, grip) and 2-4 short reasons tied to the player's data.
Confidence is 0..1: lower it when key data (handicap, 7-iron carry, miss) is missing.
A rule-based baseline pick is included; agree with it unless the data clearly says otherwise.
"""


class _Decision(BaseModel):
    iron_set_id: str
    shaft_id: str
    set_makeup: str
    adjustments: list[str]
    reasons: list[str]
    confidence: float


async def decide(profile: PlayerProfile) -> Recommendation:
    baseline = rules.decide(profile)
    prompt = json.dumps(
        {
            "player": profile.model_dump(),
            "catalog": {
                "iron_sets": [i.model_dump() for i in IRON_SETS],
                "shafts": [s.model_dump() for s in SHAFTS],
            },
            "baseline": {"iron_set_id": baseline.iron_set.id, "shaft_id": baseline.shaft.id},
        }
    )
    d: _Decision = await generate_json(prompt, SYSTEM, _Decision, temperature=0.2)
    if d.iron_set_id not in IRON_BY_ID or d.shaft_id not in SHAFT_BY_ID:
        log.warning("Gemini picked unknown ids %s / %s; using rules", d.iron_set_id, d.shaft_id)
        return baseline
    return Recommendation(
        iron_set=rules.to_option(IRON_BY_ID[d.iron_set_id]),
        shaft=rules.to_option(SHAFT_BY_ID[d.shaft_id]),
        set_makeup=d.set_makeup,
        adjustments=d.adjustments[:4],
        reasons=d.reasons[:4],
        confidence=max(0.0, min(1.0, d.confidence)),
        engine="gemini",
    )
