import logging

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field

from app.core.config import settings
from app.schemas import ChatOut, Message, PlayerProfile
from app.services import catalog

log = logging.getLogger(__name__)

TOTAL_STEPS = 5

SYSTEM_PROMPT_TEMPLATE = """\
You are Pocket Fitter, a friendly virtual golf club fitter for Takomo Golf irons.
Your job in this chat is to INTERVIEW the golfer. A separate decision engine picks the final clubs
from Takomo's catalog (below, for answering questions; never invent models or specs).

The app has already greeted the golfer with: "Hi, I'm your Pocket Fitter. I'll help you find clubs
that fit your game. What brings you here?" Their first message answers that.

How to run the conversation:
- Ask ONE short question at a time, like a fitting tool would. Keep replies under 40 words.
- Cover these {total_steps} topics (Takomo's fitting questionnaire), skipping anything already answered:
  1. typical 18-hole score, plus age and sex
  2. 7-iron club speed (mph) or, if they don't know it, 7-iron carry
  3. top 3 priorities: forgiveness, distance, forged feel, distance control, workability,
     less offset, more offset
  4. desired ball flight (low / mid / high) and swing tempo (smooth / moderate / quick)
  5. height, wrist-to-floor distance in golf shoes, glove size (XS-XL); right- or left-handed
  Accept rough answers and ranges (use the midpoint); a golfer may skip a measurement they don't know.
- If the golfer asks a general question, answer it briefly, then continue.
- Always offer 2-4 short tappable answer options in `suggestions` (max 4 words each).
- `step` = how many of those {total_steps} topics are covered so far.
- Once all topics are covered (or the golfer asks for a recommendation right away), set `ready` to
  true, fill `profile`, set `step` to {total_steps}, and reply with ONE short line such as
  "Thanks! Here's the setup I'd pick for you." Do NOT name clubs yourself; the engine does that.
  Suggestions then: "Why this set?", "Other shaft options", "Start over".
- `profile` fields: score_bucket 1 Under 71, 2 71-77, 3 78-84, 4 85-92, 5 Over 92; carry in yards
  (metres x 1.094); height and wrist-to-floor in cm (inches x 2.54). Leave unknown fields empty.
- After the recommendation the golfer may ask follow-ups; answer briefly using the recommendation
  shown in the conversation. Keep `ready` false for those turns.
- Always reply in English, including `suggestions`, even if the golfer writes in another language.

TAKOMO CATALOG
{catalog}
"""


def system_prompt(catalog_data: dict) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        total_steps=TOTAL_STEPS, catalog=catalog.prompt_text(catalog_data)
    )


class _Answer(BaseModel):
    reply: str
    suggestions: list[str] = Field(default_factory=list)
    step: int
    ready: bool = False
    profile: PlayerProfile | None = None


_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


async def generate_json(contents, system: str, schema: type[BaseModel], temperature: float = 0.6):
    """Call Gemini with structured output; fall back to the secondary model on 404/429/5xx."""
    config = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
        response_schema=schema,
        temperature=temperature,
    )
    try:
        resp = await _get_client().aio.models.generate_content(
            model=settings.gemini_model, contents=contents, config=config
        )
    except errors.APIError as exc:
        if exc.code not in (404, 429, 500, 502, 503) or not settings.gemini_fallback_model:
            raise
        log.warning("Gemini %s failed (%s), falling back to %s",
                    settings.gemini_model, exc.code, settings.gemini_fallback_model)
        resp = await _get_client().aio.models.generate_content(
            model=settings.gemini_fallback_model, contents=contents, config=config
        )
    return resp.parsed if isinstance(resp.parsed, schema) else schema.model_validate_json(resp.text)


async def reply(messages: list[Message]) -> ChatOut:
    contents = [
        types.Content(role="user" if m.role == "user" else "model", parts=[types.Part(text=m.content)])
        for m in messages
    ]
    answer: _Answer = await generate_json(contents, system_prompt(await catalog.load()), _Answer)
    ready = answer.ready and answer.profile is not None
    return ChatOut(
        reply=answer.reply,
        suggestions=answer.suggestions[:4],
        step=TOTAL_STEPS if ready else max(0, min(answer.step, TOTAL_STEPS - 1)),
        total_steps=TOTAL_STEPS,
        profile=answer.profile if ready else None,
    )
