"""Deterministic decision engine: "golfers like you" over Takomo's fitting data.

Takes the spec that fitted most of the golfer's nearest neighbours among Takomo's 20,000 train
golfers (see app.services.similar). Used without an LLM, in tests, and as the safety net when
another engine fails. On Takomo's dev split it scores 80.2 vs 77.1 for Takomo's current rules
(scripts/eval_similar.py).
"""

from app.schemas import Option, PlayerProfile, Recommendation, SimilarGolfers
from app.services import catalog, confidence, similar


def head_option(slug: str) -> Option:
    h = catalog.head(slug)
    return Option(id=slug, name=h["name"], description=h["description"], **catalog.media(slug))


def shaft_option(slug: str) -> Option:
    s = catalog.shaft(slug)
    tempo = "/".join(s["tempo_profile"]) if s["tempo_profile"] else "any"
    return Option(id=slug, name=catalog.shaft_name(s),
                  description=f"{s['material'].capitalize()}, {'/'.join(s['flight_profile'])} flight, "
                              f"{tempo} tempo.")


def chosen_values(head: str, shaft: str, length: float, lie: int, grip: str) -> dict[str, str]:
    """The picked spec as the strings SimilarGolfers uses, per confidence field."""
    s = catalog.shaft(shaft)
    return {"head": head, "flex": s["flex"], "material": s["material"], "shaft": shaft,
            "length": str(float(length)), "lie": str(int(lie)), "grip": grip}


def calibrated_confidence(p: PlayerProfile, found: SimilarGolfers, head: str, shaft: str,
                          length: float, lie: int, grip: str) -> tuple[float, dict[str, float]]:
    fields = confidence.per_field(found, chosen_values(head, shaft, length, lie, grip), p)
    return confidence.overall(fields), fields


def adjustments(length_in: float, lie_deg: int, grip: str) -> list[str]:
    out = []
    if length_in:
        out.append(f"Length {length_in:+g}\" vs standard.")
    if lie_deg:
        out.append(f"Lie {abs(lie_deg)}° {'upright' if lie_deg > 0 else 'flat'}.")
    if grip != "standard":
        out.append(f"{grip.capitalize()} grip.")
    out.append("Confirm length and lie with a static measurement or a ball-line test.")
    return out


def decide(p: PlayerProfile, found: SimilarGolfers | None = None) -> Recommendation:
    found = found or similar.find_local(p)
    head = found.head[0].value
    shaft = found.shaft[0].value  # most common shaft among neighbours fitted into that head
    length = float(found.length_in[0].value)
    lie = int(found.lie_deg[0].value)
    grip = found.grip[0].value
    if not catalog.is_buildable(head, shaft, length, lie, grip):  # defensive: data is consistent
        shaft = catalog.head(head)["default_shaft"]
    n = found.count
    reasons = [
        (f"{round(found.head[0].share * n)} of the {n} most similar golfers in Takomo's data were "
        f"fitted into the {catalog.head(head)['name']}."),
        (f"{found.flex[0].value.capitalize()} {found.material[0].value} shafts fitted "
        f"{round(found.flex[0].share * 100)}% of them."),
    ]
    if found.expected_carry_yd:
        reasons.append(f"Expected 7-iron carry with this head: about {round(found.expected_carry_yd)} yd.")
    if len(found.head) > 1 and found.head[0].share - found.head[1].share < 0.15:
        reasons.append(f"Close call: {round(found.head[1].share * 100)}% of similar golfers went with "
                       f"the {catalog.head(found.head[1].value)['name']}; worth trying both.")
    conf, fields = calibrated_confidence(p, found, head, shaft, length, lie, grip)
    return Recommendation(
        iron_set=head_option(head),
        shaft=shaft_option(shaft),
        runner_up=head_option(found.head[1].value) if len(found.head) > 1 else None,
        grip=grip,
        length_in=length,
        lie_deg=lie,
        purchase=catalog.purchase_for(head, shaft, length, lie, grip),
        adjustments=adjustments(length, lie, grip),
        reasons=reasons,
        confidence=conf,
        field_confidence=fields,
        engine="rules",
        similar=found,
    )
