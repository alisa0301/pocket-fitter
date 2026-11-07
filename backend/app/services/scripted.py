"""Scripted fallback used when no Gemini key is configured, in the Demo tab and in tests."""

import re
from collections.abc import Callable

from app.schemas import ChatOut, Message, PlayerProfile

NOT_SURE = "Not sure"
# A standalone number (not part of "G425" or "2021"), optionally followed by a degree unit.
LOFT_RE = re.compile(r"(?<![\w.,])(\d{2}(?:[.,]\d)?)(?![\d.,]*\d)\s*(°|deg\b|degrees?\b)?",
                     re.IGNORECASE)


def _choice(options: dict[str, dict]) -> Callable[[str], dict]:
    return lambda answer: options.get(answer, {})


def _loft(text: str, need_unit: bool = False) -> float | None:
    """First number that looks like a 7-iron loft (20-40 degrees).

    With need_unit, only "30°" / "30 deg" count, so model names and years ("T200", "2021") don't.
    """
    for m in LOFT_RE.finditer(text):
        v = float(m.group(1).replace(",", "."))
        if 20 <= v <= 40 and (m.group(2) or not need_unit):
            return v
    return None


def _current_irons(answer: str) -> dict:
    text = answer.strip()
    if not text or text.lower() == NOT_SURE.lower():
        return {}
    fields: dict = {"current_irons": text[:80]}
    if (loft := _loft(text, need_unit=True)) is not None:
        fields["current_7i_loft_deg"] = loft
    return fields


def _loft_answer(answer: str) -> dict:
    loft = _loft(answer)
    return {"current_7i_loft_deg": loft} if loft is not None else {}


SCORE = {"Under 78": {"score_bucket": 2}, "78-84": {"score_bucket": 3},
         "85-92": {"score_bucket": 4}, "Over 92": {"score_bucket": 5}}
CARRY = {"Under 120 yd": {"carry_yd": 110}, "120-140 yd": {"carry_yd": 130},
         "140-160 yd": {"carry_yd": 150}, "160 yd+": {"carry_yd": 170}}
PRIORITY = {"Forgiveness": {"characteristics": ["forgiveness", "distance", "more offset"]},
            "Distance": {"characteristics": ["distance", "forgiveness", "distance control"]},
            "Control": {"characteristics": ["distance control", "workability", "less offset"]},
            "Forged feel": {"characteristics": ["forged feel", "workability", "distance control"]}}
FLIGHT = {"Low": {"flight": "low"}, "Mid": {"flight": "mid"}, "High": {"flight": "high"}}

# (question, tappable suggestions, answer -> profile fields). Free text is always allowed.
QUESTIONS: list[tuple[str, list[str], Callable[[str], dict]]] = [
    ("What's your typical 18-hole score?", list(SCORE), _choice(SCORE)),
    ("How far do you carry your 7-iron?", list(CARRY), _choice(CARRY)),
    ("What matters most in your irons?", list(PRIORITY), _choice(PRIORITY)),
    ("Which ball flight do you want?", list(FLIGHT), _choice(FLIGHT)),
    (("Which irons do you play now? Type the brand and model (and year if you know it), "
     "e.g. \"Titleist T200, 2021\"."), [NOT_SURE], _current_irons),
    ("Do you know your 7-iron's loft? Tap one or type it.",
     [NOT_SURE, "28°", "30°", "32°", "34°"], _loft_answer),
]


def _profile(answers: list[str]) -> PlayerProfile:
    fields: dict = {}
    for (_, _, parse), answer in zip(QUESTIONS, answers[1:], strict=False):
        fields |= {k: v for k, v in parse(answer).items() if v is not None}
    return PlayerProfile(**fields)


def reply(messages: list[Message]) -> ChatOut:
    answers = [m.content for m in messages if m.role == "user"]
    total = len(QUESTIONS) + 1
    if len(answers) <= len(QUESTIONS):
        q, suggestions, _ = QUESTIONS[max(len(answers) - 1, 0)]
        prefix = "Great, let's find your fit. " if len(answers) == 1 else "Got it. "
        return ChatOut(reply=prefix + q, suggestions=suggestions, step=len(answers),
                       total_steps=total)
    if len(answers) == len(QUESTIONS) + 1:
        return ChatOut(
            reply="Thanks! Here's the setup I'd pick for you.",
            suggestions=["Start over"], step=total, total_steps=total,
            profile=_profile(answers),
        )
    return ChatOut(reply="Tap Start over to run a new fitting.", suggestions=["Start over"],
                   step=total, total_steps=total)
