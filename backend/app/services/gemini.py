from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field

from app.core.config import settings
from app.schemas import ChatOut, Message

TOTAL_STEPS = 5

SYSTEM_PROMPT = f"""\
You are Pocket Fitter, a friendly virtual golf club fitter.
Goal: recommend a club setup (irons, wedges, driver, shafts) that fits the golfer.

The app has already greeted the golfer with: "Hi, I'm your Pocket Fitter. I'll help you find clubs
that fit your game. What brings you here?" Their first message answers that.

How to run the conversation:
- Ask ONE short question at a time, like a fitting tool would. Keep replies under 40 words.
- Cover roughly {TOTAL_STEPS - 1} topics before recommending: what they're looking for, handicap or
  experience, 7-iron carry distance or swing speed, typical miss / ball flight, and age or physical
  limits when relevant. Skip anything the golfer already told you.
- After that, give a clear recommendation: club type (e.g. players' cavity back, game improvement),
  shaft flex and weight, loft / lie notes, and one sentence on why.
- If the golfer asks a general question, answer it briefly, then continue the fitting.
- Always offer 2-4 short tappable answer options in `suggestions` (max 4 words each).
  After the recommendation, offer follow-ups such as "Compare options", "Shaft options", "Start over".
- `step` is how many fitting topics are covered so far (0-{TOTAL_STEPS}); set it to {TOTAL_STEPS}
  once you've given the recommendation.
- Always reply in English, including `suggestions`, even if the golfer writes in another language.
"""


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
        system_instruction=SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=_Answer,
        temperature=0.6,
    )
    try:
        resp = await _get_client().aio.models.generate_content(
            model=settings.gemini_model, contents=contents, config=config
        )
    except errors.ServerError:
        # Primary model overloaded (503) -> try the fallback once.
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
