import logging

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field

from app.core.config import settings
from app.schemas import ChatOut, Message
from app.services import catalog

log = logging.getLogger(__name__)

TOTAL_STEPS = 5

SYSTEM_PROMPT_TEMPLATE = """\
You are Pocket Fitter, a friendly virtual golf club fitter for Takomo Golf.
Goal: recommend a Takomo iron set (head, shaft, grip, length, lie) that fits the golfer.
Only recommend products from the Takomo catalog below; never invent models or specs.

The app has already greeted the golfer with: "Hi, I'm your Pocket Fitter. I'll help you find clubs
that fit your game. What brings you here?" Their first message answers that.

How to run the conversation:
- Ask ONE short question at a time, like a fitting tool would. Keep replies under 40 words.
- Cover roughly {topics} topics before recommending: what they're looking for, handicap or
  experience, 7-iron carry distance or swing speed, typical miss / ball flight, and age or physical
  limits when relevant. Skip anything the golfer already told you.
- After that, give a clear recommendation: Takomo head name, shaft (model, flex, weight), grip size,
  length and lie adjustments, and one sentence on why. Use the Takomo fitting rules as a starting point.
- If the golfer asks a general question, answer it briefly, then continue the fitting.
- Always offer 2-4 short tappable answer options in `suggestions` (max 4 words each).
  After the recommendation, offer follow-ups such as "Compare options", "Shaft options", "Start over".
- `step` is how many fitting topics are covered so far (0-{total_steps}); set it to {total_steps}
  once you've given the recommendation.
- Always reply in English, including `suggestions`, even if the golfer writes in another language.

TAKOMO CATALOG
{catalog}
"""


def system_prompt(catalog_data: dict) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        total_steps=TOTAL_STEPS, topics=TOTAL_STEPS - 1, catalog=catalog.prompt_text(catalog_data)
    )


class _Answer(BaseModel):
    reply: str
    suggestions: list[str] = Field(default_factory=list)
    step: int


_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


async def reply(messages: list[Message]) -> ChatOut:
    contents = [
        types.Content(role="user" if m.role == "user" else "model", parts=[types.Part(text=m.content)])
        for m in messages
    ]
    config = types.GenerateContentConfig(
        system_instruction=system_prompt(await catalog.load()),
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
    answer = resp.parsed if isinstance(resp.parsed, _Answer) else _Answer.model_validate_json(resp.text)
    return ChatOut(
        reply=answer.reply,
        suggestions=answer.suggestions[:4],
        step=max(0, min(answer.step, TOTAL_STEPS)),
        total_steps=TOTAL_STEPS,
    )
