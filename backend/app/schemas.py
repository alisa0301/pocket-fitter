from typing import Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatIn(BaseModel):
    messages: list[Message]
    fitting_id: str | None = None
    recommended: bool = False  # a recommendation was already given in this conversation


class ChatOut(BaseModel):
    reply: str
    suggestions: list[str] = []
    step: int = 0
    total_steps: int = 0
    fitting_id: str | None = None  # set when the fitting is saved to MongoDB
    profile: "GolferProfile | None" = None  # answers collected so far (Gemini mode)
    similar: "SimilarGolfers | None" = None  # with the recommendation


class GolferProfile(BaseModel):
    """Questionnaire answers (Takomo's 12 questions). Everything optional: the chat fills it in."""

    age: int | None = None
    sex: Literal["male", "female"] | None = None
    handedness: Literal["right", "left"] | None = None
    score_bucket: int | None = Field(None, ge=1, le=5)  # 1 Under 71 ... 5 Over 92
    speed_mph: float | None = None  # 7-iron club speed, if the golfer knows it
    carry_yd: float | None = None  # 7-iron carry otherwise
    characteristics: list[str] = []  # up to 3 of forgiveness, distance, forged feel, ...
    flight: Literal["low", "mid", "high"] | None = None
    tempo: Literal["smooth", "moderate", "quick"] | None = None
    height_cm: float | None = None
    wrist_to_floor_cm: float | None = None
    glove: Literal["XS", "S", "M", "M/L", "L", "XL"] | None = None


class SpecShare(BaseModel):
    value: str
    share: float  # 0-1 of the similar golfers
    label: str | None = None  # display name for heads and shafts


class SimilarGolfers(BaseModel):
    count: int
    source: Literal["atlas_vector_search", "in_memory"]
    head: list[SpecShare]
    shaft: list[SpecShare]
    flex: list[SpecShare]
    material: list[SpecShare]
    length_in: list[SpecShare]
    lie_deg: list[SpecShare]
    grip: list[SpecShare]
    purchase: list[SpecShare]
    expected_carry_yd: float | None = None


ChatOut.model_rebuild()
