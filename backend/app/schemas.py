from typing import Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class PlayerProfile(BaseModel):
    """What the chat collects (Takomo's fitting questionnaire); input to the decision engine.

    Everything is optional: engines fall back to population defaults for missing answers.
    """

    age: int | None = None
    sex: Literal["male", "female"] | None = None
    handedness: Literal["right", "left"] | None = None
    score_bucket: int | None = Field(
        None, ge=1, le=5, description="Typical 18-hole score: 1 Under 71, 2 71-77, 3 78-84, 4 85-92, 5 Over 92"
    )
    speed_mph: float | None = Field(None, description="7-iron club speed, if the golfer knows it")
    carry_yd: float | None = Field(None, description="7-iron carry in yards otherwise")
    characteristics: list[str] = Field(
        default_factory=list,
        description="Up to 3 of: forgiveness, distance, forged feel, distance control, workability, "
        "less offset, more offset",
    )
    flight: Literal["low", "mid", "high"] | None = None
    tempo: Literal["smooth", "moderate", "quick"] | None = None
    height_cm: float | None = None
    wrist_to_floor_cm: float | None = Field(None, description="Wrist crease to floor in golf shoes")
    glove: Literal["XS", "S", "M", "M/L", "L", "XL"] | None = None
    # Current irons, for the "your clubs vs Takomo" comparison
    current_irons: str | None = Field(None, description="Brand, model and rough age of current irons")
    current_7i_loft_deg: float | None = Field(None, description="Current 7-iron loft, if the golfer knows it")
    current_7i_loft_estimate_deg: float | None = Field(
        None, description="Best estimate of that model's 7-iron loft when the golfer doesn't know it"
    )
    current_forgiveness_estimate: int | None = Field(
        None, ge=1, le=5,
        description="Current irons' forgiveness on Takomo's 1-5 scale (1 blade ... 5 max game improvement)",
    )


class SpecShare(BaseModel):
    value: str
    share: float  # 0-1 of the similar golfers
    label: str | None = None  # display name for heads and shafts


class SimilarGolfers(BaseModel):
    """What fitted the most similar golfers in Takomo's data."""

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


class Option(BaseModel):
    id: str
    name: str
    description: str
    image_url: str | None = None
    url: str | None = None
    price_eur: float | None = None


class ClubSpec(BaseModel):
    label: str
    loft_deg: float
    loft_source: Literal["you", "estimate", "default", "takomo"]
    forgiveness: int
    forgiveness_source: Literal["estimate", "default", "takomo"]


class ComparisonMetric(BaseModel):
    name: str
    unit: str
    current: float
    takomo: float
    difference: float
    better: Literal["takomo", "current", "same"]


class ClubComparison(BaseModel):
    """Current 7-iron vs the recommended Takomo head, same simulated swing through the pack's
    ball-flight model."""

    current: ClubSpec
    takomo: ClubSpec
    swing_speed_mph: float
    metrics: list[ComparisonMetric]
    highlights: list[str]
    assumptions: list[str]


class Recommendation(BaseModel):
    iron_set: Option  # Takomo head
    shaft: Option
    runner_up: Option | None = None  # second head, as Takomo's tool shows two
    grip: str = "standard"
    length_in: float = 0  # vs standard
    lie_deg: int = 0  # + upright, - flat
    purchase: Literal["stock", "custom"] = "custom"
    set_makeup: str = ""
    adjustments: list[str] = []
    reasons: list[str] = []
    confidence: float = Field(ge=0, le=1)
    engine: str
    comparison: ClubComparison | None = None
    similar: SimilarGolfers | None = None


class ChatIn(BaseModel):
    messages: list[Message]
    fitting_id: str | None = None


class ChatOut(BaseModel):
    reply: str
    suggestions: list[str] = []
    step: int = 0
    total_steps: int = 0
    profile: PlayerProfile | None = None
    recommendation: Recommendation | None = None
    fitting_id: str | None = None  # set when the fitting is saved to MongoDB
