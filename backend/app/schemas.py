from typing import Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


Miss = Literal["slice", "hook", "thin_fat", "straight", "unknown"]


class PlayerProfile(BaseModel):
    """What the chat collects; input to the decision engine."""

    handicap: float | None = Field(None, description="Golf handicap; 36 for beginners")
    seven_iron_carry_m: float | None = Field(None, description="7-iron carry distance in metres")
    typical_miss: Miss = "unknown"
    age: int | None = None
    looking_for: str = Field("", description="What clubs / goal the golfer mentioned")
    notes: str = Field("", description="Anything else relevant (injuries, preferences)")


class Option(BaseModel):
    id: str
    name: str
    description: str


class Recommendation(BaseModel):
    iron_set: Option
    shaft: Option
    set_makeup: str
    adjustments: list[str] = []
    reasons: list[str] = []
    confidence: float = Field(ge=0, le=1)
    engine: str


class ChatIn(BaseModel):
    messages: list[Message]


class ChatOut(BaseModel):
    reply: str
    suggestions: list[str] = []
    step: int = 0
    total_steps: int = 0
    profile: PlayerProfile | None = None
    recommendation: Recommendation | None = None
