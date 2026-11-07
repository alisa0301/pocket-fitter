import logging

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field

from app.core.config import settings
from app.schemas import ChatOut, GolferProfile, Message, SimilarGolfers
from app.services import catalog, similar

log = logging.getLogger(__name__)

TOTAL_STEPS = 6

SYSTEM_PROMPT_TEMPLATE = """\
You are Pocket Fitter, a friendly virtual golf club fitter for Takomo Golf.
Goal: recommend a Takomo iron set (head, shaft, grip, length, lie) that fits the golfer.
Only recommend products from the Takomo catalog below; never invent models or specs.

The app has already greeted the golfer with: "Hi, I'm your Pocket Fitter. I'll help you find clubs
that fit your game. What brings you here?" Their first message answers that.

How to run the conversation:
- Ask ONE short question at a time, like a fitting tool would. Keep replies under 40 words.
- Cover these {topics} topics (Takomo's fitting questionnaire), skipping anything already answered:
  1. typical 18-hole score, plus age and sex
  2. 7-iron club speed (mph) or, if they don't know it, 7-iron carry (yards or metres)
  3. top 3 priorities: forgiveness, distance, forged feel, distance control, workability,
     less offset, more offset
  4. desired ball flight (low / mid / high) and swing tempo (smooth / moderate / quick)
  5. height, wrist-to-floor distance in golf shoes, glove size (XS-XL); right- or left-handed
- If the golfer asks a general question, answer it briefly, then continue the fitting.
- Always offer 2-4 short tappable answer options in `suggestions` (max 4 words each).
  After the recommendation, offer follow-ups such as "Compare options", "Shaft options", "Start over".
- `step` is how many topics are covered so far (0-{topics}); {total_steps} once you've recommended.
- `profile`: everything the golfer has told you so far, converted to its fields (score_bucket
  1 Under 71, 2 71-77, 3 78-84, 4 85-92, 5 Over 92; metres -> yards x1.094; feet/inches -> cm).
  Leave unknown fields empty; never guess.
- Set `ready_to_recommend` true once all five topics are covered (a golfer who doesn't know a body
  measurement can skip it) or the golfer asks for a recommendation right away. The app then looks up
  similar golfers in Takomo's data and you write the recommendation.
- Always reply in English, including `suggestions`, even if the golfer writes in another language.

TAKOMO CATALOG
{catalog}
"""

RECOMMEND_INSTRUCTION = """\

NOW RECOMMEND: your reply in this turn IS the recommendation (do not say you are checking or
looking anything up). Give the full Takomo spec: head (and a runner-up), shaft (model, flex, weight), grip,
length and lie, stock or custom. Base it on the golfer's answers, Takomo's rules and the similar-golfer
data below; mention the similar golfers in one sentence (e.g. "7 in 10 golfers like you were fitted
into ..."). Up to 90 words. Set `step` to {total_steps} and `ready_to_recommend` false.

{similar}"""


def system_prompt(catalog_data: dict) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        total_steps=TOTAL_STEPS, topics=TOTAL_STEPS - 1, catalog=catalog.prompt_text(catalog_data)
    )


class _Answer(BaseModel):
    reply: str
    suggestions: list[str] = Field(default_factory=list)
    step: int
    profile: GolferProfile = Field(default_factory=GolferProfile)
    ready_to_recommend: bool = False


_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


async def _generate(contents: list[types.Content], system: str) -> _Answer:
    config = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
        response_schema=_Answer,
        temperature=0.6,
    )
    try:
        resp = await _get_client().aio.models.generate_content(
            model=settings.gemini_model, contents=contents, config=config
        )
    except errors.APIError as exc:
        # Primary model overloaded (503), rate-limited (429) or retired (404) -> try the fallback.
        if exc.code not in (404, 429, 500, 502, 503) or not settings.gemini_fallback_model:
            raise
        log.warning("Gemini %s failed (%s), falling back to %s",
                    settings.gemini_model, exc.code, settings.gemini_fallback_model)
        resp = await _get_client().aio.models.generate_content(
            model=settings.gemini_fallback_model, contents=contents, config=config
        )
    return resp.parsed if isinstance(resp.parsed, _Answer) else _Answer.model_validate_json(resp.text)


def _should_recommend(answer: _Answer, recommended: bool) -> bool:
    """Once per fitting: when the model says it's ready or has covered every topic."""
    return not recommended and (answer.ready_to_recommend or answer.step >= TOTAL_STEPS - 1)


async def reply(messages: list[Message], recommended: bool = False) -> ChatOut:
    contents = [
        types.Content(role="user" if m.role == "user" else "model", parts=[types.Part(text=m.content)])
        for m in messages
    ]
    system = system_prompt(await catalog.load())
    answer = await _generate(contents, system)

    found: SimilarGolfers | None = None
    if _should_recommend(answer, recommended):
        found = await similar.find(answer.profile)
        prompt = system + RECOMMEND_INSTRUCTION.format(
            total_steps=TOTAL_STEPS, similar=similar.prompt_text(found)
        )
        final = await _generate(contents, prompt)
        final.profile = answer.profile
        final.step = TOTAL_STEPS
        answer = final

    return ChatOut(
        reply=answer.reply,
        suggestions=answer.suggestions[:4],
        step=max(0, min(answer.step, TOTAL_STEPS)),
        total_steps=TOTAL_STEPS,
        profile=answer.profile,
        similar=found,
    )
