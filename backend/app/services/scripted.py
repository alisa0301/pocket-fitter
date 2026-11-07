"""Scripted fallback used when no Gemini key is configured (and in tests)."""

from app.schemas import ChatOut, Message, PlayerProfile

# (question, {answer option: profile fields})
QUESTIONS = [
    ("What's your typical 18-hole score?",
     {"Under 78": {"score_bucket": 2}, "78-84": {"score_bucket": 3}, "85-92": {"score_bucket": 4},
      "Over 92": {"score_bucket": 5}}),
    ("How far do you carry your 7-iron?",
     {"Under 120 yd": {"carry_yd": 110}, "120-140 yd": {"carry_yd": 130},
      "140-160 yd": {"carry_yd": 150}, "160 yd+": {"carry_yd": 170}}),
    ("What matters most in your irons?",
     {"Forgiveness": {"characteristics": ["forgiveness", "distance", "more offset"]},
      "Distance": {"characteristics": ["distance", "forgiveness", "distance control"]},
      "Control": {"characteristics": ["distance control", "workability", "less offset"]},
      "Forged feel": {"characteristics": ["forged feel", "workability", "distance control"]}}),
    ("Which ball flight do you want?",
     {"Low": {"flight": "low"}, "Mid": {"flight": "mid"}, "High": {"flight": "high"}}),
    ("What kind of irons do you play now?",
     {"Blades": {"current_irons": "Your blades", "current_7i_loft_estimate_deg": 34,
                 "current_forgiveness_estimate": 1},
      "Players cavity": {"current_irons": "Your players cavity backs",
                         "current_7i_loft_estimate_deg": 33, "current_forgiveness_estimate": 2},
      "Game improvement": {"current_irons": "Your game-improvement irons",
                           "current_7i_loft_estimate_deg": 30, "current_forgiveness_estimate": 4},
      "Not sure": {}}),
]


def _profile(answers: list[str]) -> PlayerProfile:
    fields: dict = {}
    for (_, opts), answer in zip(QUESTIONS, answers[1:], strict=False):
        fields |= opts.get(answer, {})
    return PlayerProfile(**fields)


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
