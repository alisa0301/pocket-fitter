"""LLM decision engine: Gemini chooses from Takomo's catalog; output is validated against it."""

import json
import logging

from pydantic import BaseModel

from app.decision import rules
from app.schemas import PlayerProfile, Recommendation, SimilarGolfers
from app.services import catalog, similar
from app.services.gemini import generate_json

log = logging.getLogger(__name__)

SYSTEM = """\
You are an expert Takomo Golf club fitter making the FINAL iron decision.
Pick one head and one shaft from the Takomo catalog (use their slugs; the shaft must list the head),
a runner-up head, grip, length and lie from the allowed options, 2-4 concrete adjustments and
2-4 short reasons tied to the player's answers. Confidence is 0..1: lower it when key answers
(score, 7-iron speed or carry, priorities, height) are missing (the app replaces it with a
calibrated value).
You get the spec that fitted the most similar golfers in Takomo's data and a baseline built from it;
agree with the baseline unless the player's answers clearly say otherwise, and mention the
similar golfers in one reason.

TAKOMO CATALOG
{catalog}
"""


class _Decision(BaseModel):
    head: str
    shaft: str
    runner_up: str
    grip: str
    length_in: float
    lie_deg: int
    adjustments: list[str]
    reasons: list[str]
    confidence: float


async def decide(profile: PlayerProfile, found: SimilarGolfers | None = None) -> Recommendation:
    found = found or await similar.find(profile)
    baseline = rules.decide(profile, found)
    prompt = json.dumps(
        {
            "player": profile.model_dump(exclude_none=True),
            "similar_golfers": similar.prompt_text(found),
            "baseline": {"head": baseline.iron_set.id, "shaft": baseline.shaft.id,
                         "grip": baseline.grip, "length_in": baseline.length_in,
                         "lie_deg": baseline.lie_deg},
        }
    )
    system = SYSTEM.format(catalog=catalog.prompt_text(await catalog.load()))
    d: _Decision = await generate_json(prompt, system, _Decision, temperature=0.2)
    if not catalog.is_buildable(d.head, d.shaft, d.length_in, d.lie_deg, d.grip):
        log.warning("Gemini picked an unbuildable spec %s; using rules", d.model_dump())
        return baseline
    runner_up = d.runner_up if catalog.head(d.runner_up) and d.runner_up != d.head else None
    # Calibrated from how many similar golfers share each pick, not the model's self-report.
    conf, fields = rules.calibrated_confidence(profile, found, d.head, d.shaft, d.length_in,
                                               d.lie_deg, d.grip)
    return Recommendation(
        iron_set=rules.head_option(d.head),
        shaft=rules.shaft_option(d.shaft),
        runner_up=rules.head_option(runner_up) if runner_up else baseline.runner_up,
        grip=d.grip,
        length_in=d.length_in,
        lie_deg=d.lie_deg,
        purchase=catalog.purchase_for(d.head, d.shaft, d.length_in, d.lie_deg, d.grip),
        adjustments=d.adjustments[:4],
        reasons=d.reasons[:4],
        confidence=conf,
        field_confidence=fields,
        engine="gemini",
        similar=found,
    )
