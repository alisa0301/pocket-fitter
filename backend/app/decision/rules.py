"""Deterministic baseline decision engine. Used without an LLM, in tests, and as a safety net."""

from app.catalog import IRON_SETS, SHAFTS, IronSet, Shaft
from app.schemas import Option, PlayerProfile, Recommendation


def _iron_score(iron: IronSet, p: PlayerProfile) -> float:
    hcp = p.handicap if p.handicap is not None else 20
    if iron.handicap_min <= hcp <= iron.handicap_max:
        score = 10.0
    else:
        gap = min(abs(hcp - iron.handicap_min), abs(hcp - iron.handicap_max))
        score = 10.0 - gap * 0.8
    if p.typical_miss == "slice":
        score += {"low": -1, "medium": 0.5, "high": 1.5}[iron.offset]
        score += (iron.forgiveness - 3) * 0.3
    if p.typical_miss == "hook":
        score += {"low": 1, "medium": 0, "high": -1.5}[iron.offset]
    if p.typical_miss == "thin_fat":
        score += (iron.forgiveness - 3) * 0.7
    if p.age is not None and p.age >= 60:
        score += (iron.forgiveness - 3) * 0.5
    if p.seven_iron_carry_m is not None and p.seven_iron_carry_m < 125 and iron.launch == "high":
        score += 1
    return score


def _pick_shaft(p: PlayerProfile) -> Shaft:
    carry = p.seven_iron_carry_m
    if carry is None:
        hcp = p.handicap if p.handicap is not None else 20
        carry = 165 if hcp < 8 else 145 if hcp < 18 else 125
    if p.age is not None and p.age >= 65:
        carry -= 10  # favour lighter shafts for older players
    for shaft in SHAFTS:
        if shaft.carry_min_m <= carry < shaft.carry_max_m:
            return shaft
    return SHAFTS[0] if carry >= SHAFTS[0].carry_min_m else SHAFTS[-1]


def _set_makeup(p: PlayerProfile) -> str:
    hcp = p.handicap if p.handicap is not None else 20
    carry = p.seven_iron_carry_m or 140
    if hcp > 18 or carry < 135:
        return "6-PW + GW; replace 4-5 irons with hybrids"
    if hcp <= 8 and carry >= 155:
        return "4-PW"
    return "5-PW + GW"


def _adjustments(p: PlayerProfile) -> list[str]:
    out = []
    if p.typical_miss == "slice":
        out.append("Consider 1° upright lie and a draw-biased setup to help square the face.")
    if p.typical_miss == "hook":
        out.append("Consider 1° flat lie; avoid heavy offset.")
    if p.typical_miss == "thin_fat":
        out.append("Wider sole will be more forgiving on thin and fat contact.")
    out.append("Confirm lie angle and length with a static measurement or lie board.")
    return out


def to_option(item: IronSet | Shaft) -> Option:
    return Option(id=item.id, name=item.name, description=item.description)


def _confidence(p: PlayerProfile) -> float:
    known = sum(x is not None for x in (p.handicap, p.seven_iron_carry_m, p.age))
    known += p.typical_miss != "unknown"
    return round(0.45 + 0.1 * known, 2)


def decide(p: PlayerProfile) -> Recommendation:
    iron = max(IRON_SETS, key=lambda i: _iron_score(i, p))
    shaft = _pick_shaft(p)
    reasons = [f"{iron.category} matches a handicap of {p.handicap:g}." if p.handicap is not None
               else f"{iron.category} is a safe default without a handicap."]
    if p.seven_iron_carry_m is not None:
        reasons.append(f"{shaft.name} suits a {p.seven_iron_carry_m:g} m 7-iron carry.")
    if p.typical_miss == "slice" and iron.offset != "low":
        reasons.append("Extra offset helps reduce a slice.")
    return Recommendation(
        iron_set=to_option(iron),
        shaft=to_option(shaft),
        set_makeup=_set_makeup(p),
        adjustments=_adjustments(p),
        reasons=reasons,
        confidence=_confidence(p),
        engine="rules",
    )

