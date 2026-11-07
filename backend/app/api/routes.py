from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatIn(BaseModel):
    messages: list[Message]


class ChatOut(BaseModel):
    reply: str
    suggestions: list[str] = []
    step: int = 0
    total_steps: int = 0


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Placeholder fitting flow. Replace with an LLM call.
QUESTIONS = [
    ("What's your current handicap?", ["0-9", "10-18", "19-28", "Just starting"]),
    ("How far do you carry your 7-iron?", ["Under 120 m", "120-140 m", "140-160 m", "160 m+"]),
    ("What's your typical miss?", ["Slice / right", "Hook / left", "Thin or fat", "Pretty straight"]),
]


@router.post("/chat", response_model=ChatOut)
def chat(body: ChatIn) -> ChatOut:
    answered = sum(1 for m in body.messages if m.role == "user")
    total = len(QUESTIONS) + 1
    step = min(answered, total)
    if answered <= len(QUESTIONS):
        q, opts = QUESTIONS[answered - 1] if answered else QUESTIONS[0]
        prefix = "Great, let's find your fit. " if answered == 1 else "Got it. "
        return ChatOut(reply=prefix + q, suggestions=opts, step=step, total_steps=total)
    return ChatOut(
        step=total,
        total_steps=total,
        reply=(
            "Thanks! Based on your answers, a forgiving cavity-back iron with a "
            "mid-launch shaft looks like a good starting point. Want me to compare options?"
        ),
        suggestions=["Compare irons", "Shaft options", "Start over"],
    )
