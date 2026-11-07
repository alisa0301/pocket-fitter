"""Scripted fallback used when no Gemini key is configured (and in tests)."""

from app.schemas import ChatOut, Message, PlayerProfile

QUESTIONS = [
    ("What's your current handicap?", {"0-9": 5, "10-18": 14, "19-28": 24, "Just starting": 36}),
    ("How far do you carry your 7-iron?",
     {"Under 120 m": 110, "120-140 m": 130, "140-160 m": 150, "160 m+": 170}),
    ("What's your typical miss?",
     {"Slice / right": "slice", "Hook / left": "hook", "Thin or fat": "thin_fat",
      "Pretty straight": "straight"}),
]


def _profile(answers: list[str]) -> PlayerProfile:
    hcp, carry, miss = (QUESTIONS[i][1].get(answers[i + 1]) for i in range(3))
    return PlayerProfile(
        handicap=hcp, seven_iron_carry_m=carry, typical_miss=miss or "unknown",
        looking_for=answers[0],
    )


def reply(messages: list[Message]) -> ChatOut:
    answers = [m.content for m in messages if m.role == "user"]
    total = len(QUESTIONS) + 1
    if len(answers) <= len(QUESTIONS):
        q, opts = QUESTIONS[max(len(answers) - 1, 0)]
        prefix = "Great, let's find your fit. " if len(answers) == 1 else "Got it. "
        return ChatOut(reply=prefix + q, suggestions=list(opts), step=len(answers),
                       total_steps=total)
    if len(answers) == len(QUESTIONS) + 1:
        return ChatOut(
            reply="Thanks! Here's the setup I'd pick for you.",
            suggestions=["Start over"], step=total, total_steps=total,
            profile=_profile(answers),
        )
    return ChatOut(reply="Tap Start over to run a new fitting.", suggestions=["Start over"],
                   step=total, total_steps=total)
