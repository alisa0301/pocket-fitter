"""DEMO catalog. Replace with the real product data (e.g. Takomo's line-up) before a real launch."""

from pydantic import BaseModel


class IronSet(BaseModel):
    id: str
    name: str
    category: str
    handicap_min: float
    handicap_max: float
    forgiveness: int  # 1 (least) .. 5 (most)
    launch: str  # low | mid | high
    offset: str  # low | medium | high
    description: str


class Shaft(BaseModel):
    id: str
    name: str
    material: str
    weight_g: int
    flex: str
    carry_min_m: float  # typical 7-iron carry range this shaft suits
    carry_max_m: float
    description: str


IRON_SETS: list[IronSet] = [
    IronSet(id="players-blade", name="Players Blade", category="Blade", handicap_min=0,
            handicap_max=5, forgiveness=1, launch="low", offset="low",
            description="Compact forged blade for maximum feel and shot shaping."),
    IronSet(id="players-cavity", name="Players Cavity", category="Players cavity back",
            handicap_min=0, handicap_max=12, forgiveness=3, launch="mid", offset="low",
            description="Clean players' look with a cavity for extra stability on mishits."),
    IronSet(id="players-distance", name="Players Distance", category="Hollow-body players distance",
            handicap_min=5, handicap_max=18, forgiveness=3, launch="mid", offset="medium",
            description="Hollow body with a fast face: compact look, extra ball speed."),
    IronSet(id="game-improvement", name="Game Improvement", category="Game improvement cavity back",
            handicap_min=12, handicap_max=28, forgiveness=4, launch="high", offset="medium",
            description="Wide sole, low CG and perimeter weighting for easy launch and forgiveness."),
    IronSet(id="max-forgiveness", name="Max Forgiveness", category="Super game improvement",
            handicap_min=20, handicap_max=54, forgiveness=5, launch="high", offset="high",
            description="Maximum forgiveness and offset to fight a slice and get the ball airborne."),
]

SHAFTS: list[Shaft] = [
    Shaft(id="steel-130-x", name="Steel 130 g X-Stiff", material="steel", weight_g=130, flex="X",
          carry_min_m=170, carry_max_m=250, description="Heavy, low-launch, for very fast swings."),
    Shaft(id="steel-120-s", name="Steel 120 g Stiff", material="steel", weight_g=120, flex="S",
          carry_min_m=155, carry_max_m=170, description="Classic stiff steel for strong players."),
    Shaft(id="steel-105-r", name="Light Steel 105 g Regular", material="steel", weight_g=105,
          flex="R", carry_min_m=130, carry_max_m=155, description="Lighter steel, mid launch."),
    Shaft(id="graphite-75-r", name="Graphite 75 g Regular", material="graphite", weight_g=75,
          flex="R", carry_min_m=120, carry_max_m=130,
          description="Light graphite for more speed and softer feel."),
    Shaft(id="graphite-60-a", name="Graphite 60 g Senior (A)", material="graphite", weight_g=60,
          flex="A", carry_min_m=0, carry_max_m=120,
          description="Very light, high launch, easy on the joints."),
]

IRON_BY_ID = {i.id: i for i in IRON_SETS}
SHAFT_BY_ID = {s.id: s for s in SHAFTS}
