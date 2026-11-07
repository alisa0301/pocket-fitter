"""Compare the golfer's current 7-iron with the recommended Takomo head.

Both clubs hit the same simulated shots (same swing, same strike pattern) through the calibrated
ball-flight model from the Takomo Fitting Lab pack, so the difference comes only from the heads:
static loft and Takomo's forgiveness rating. Face and path are held square on purpose: we compare
equipment, not swing faults. Numbers are model estimates, not measurements.
"""

from __future__ import annotations

import numpy as np

from app import physics as PH
from app.schemas import ClubComparison, ClubSpec, ComparisonMetric, PlayerProfile
from app.services import catalog

N_SHOTS = 400
DEFAULT_LOFT = 31.0  # pack: own 7-iron loft 31 +/- 1.8 deg
DEFAULT_FORGIVENESS = 3

# Delivery by score bucket, measured on the pack's train launch-monitor shots (non home-radar):
# dynamic loft minus static loft, attack angle, strike offset sd (toe/heel) and height mean/sd (mm).
DELIVERY = {
    1: dict(delta=-11.2, attack=-3.8, off_sd=6.4, hgt_mean=-0.9, hgt_sd=3.2, speed=84.0),
    2: dict(delta=-10.0, attack=-3.4, off_sd=7.9, hgt_mean=-1.8, hgt_sd=3.7, speed=79.1),
    3: dict(delta=-8.4, attack=-2.8, off_sd=9.8, hgt_mean=-2.4, hgt_sd=4.4, speed=75.9),
    4: dict(delta=-6.8, attack=-2.1, off_sd=11.9, hgt_mean=-3.1, hgt_sd=5.1, speed=72.3),
    5: dict(delta=-4.4, attack=-1.2, off_sd=15.4, hgt_mean=-3.9, hgt_sd=6.2, speed=66.5),
}


def _speed_from_carry(carry_yd: float, d: dict) -> float:
    """Club speed whose centre strike with a 31 deg 7-iron carries `carry_yd`."""
    speeds = np.arange(45.0, 110.0, 0.5)
    r = PH.shot(speeds, DEFAULT_LOFT + d["delta"], np.full_like(speeds, d["attack"]))
    return float(np.interp(carry_yd, r["carry_yd"], speeds))


def _simulate(speed: float, loft: float, forgiveness: float, d: dict, rng_seed: int) -> dict:
    rng = np.random.default_rng(rng_seed)
    n = N_SHOTS
    off = rng.normal(0.0, d["off_sd"], n)
    hgt = rng.normal(d["hgt_mean"], d["hgt_sd"], n)
    spd = rng.normal(speed, 1.0, n)
    r = PH.shot(spd, np.full(n, loft + d["delta"]), np.full(n, d["attack"]),
                offset_mm=off, height_mm=hgt, forgiveness=np.full(n, float(forgiveness)))
    carry = r["carry_yd"]
    return dict(
        carry=float(np.median(carry)),
        carry_p10=float(np.percentile(carry, 10)),
        carry_spread=float(np.percentile(carry, 90) - np.percentile(carry, 10)),
        side_spread=float(np.percentile(np.abs(r["side_yd"]), 80)),
        apex=float(np.median(r["apex_yd"])),
        land=float(np.median(r["land_angle_deg"])),
        spin=float(np.median(r["spin_rpm"])),
    )


def _metric(name, unit, cur, new, higher_is_better, decimals=0, tol=1.0) -> ComparisonMetric:
    diff = new - cur
    if abs(diff) < tol:
        better = "same"
    else:
        better = "takomo" if (diff > 0) == higher_is_better else "current"
    return ComparisonMetric(name=name, unit=unit, current=round(cur, decimals),
                            takomo=round(new, decimals), difference=round(diff, decimals),
                            better=better)


def compare(profile: PlayerProfile, head_slug: str) -> ClubComparison:
    head = catalog.head(head_slug)
    d = DELIVERY[profile.score_bucket or 4]
    assumptions: list[str] = []

    if profile.speed_mph:
        speed = float(profile.speed_mph)
    elif profile.carry_yd:
        speed = _speed_from_carry(float(profile.carry_yd), d)
        assumptions.append(f"Swing speed {speed:.0f} mph estimated from your {profile.carry_yd:g} yd carry.")
    else:
        speed = d["speed"]
        assumptions.append(f"Swing speed {speed:.0f} mph: typical for your score.")

    if profile.current_7i_loft_deg:
        loft, loft_src = float(profile.current_7i_loft_deg), "you"
    elif profile.current_7i_loft_estimate_deg:
        loft, loft_src = float(profile.current_7i_loft_estimate_deg), "estimate"
        assumptions.append(f"Current 7-iron loft {loft:g}° is an estimate for that model; check the spec.")
    else:
        loft, loft_src = DEFAULT_LOFT, "default"
        assumptions.append(f"Current 7-iron loft unknown: assumed {DEFAULT_LOFT:g}° (typical).")

    if profile.current_forgiveness_estimate:
        fg, fg_src = int(profile.current_forgiveness_estimate), "estimate"
    else:
        fg, fg_src = DEFAULT_FORGIVENESS, "default"
    assumptions.append(f"Current irons' forgiveness rated {fg}/5 on Takomo's scale ({fg_src}).")
    assumptions.append("Same swing and strike pattern for both clubs; face and path kept square, "
                       f"{N_SHOTS} simulated shots each. Model estimates, not measurements.")

    new_loft = float(head["seven_iron_loft_deg"])
    new_fg = float(head["ratings"]["forgiveness"])
    cur = _simulate(speed, loft, fg, d, rng_seed=7)
    new = _simulate(speed, new_loft, new_fg, d, rng_seed=7)

    metrics = [
        _metric("Typical carry", "yd", cur["carry"], new["carry"], True, tol=2),
        _metric("Carry on your worst 10% of strikes", "yd", cur["carry_p10"], new["carry_p10"], True,
                tol=2),
        _metric("Carry window (10th-90th %)", "yd", cur["carry_spread"], new["carry_spread"], False,
                tol=2),
        _metric("Peak height", "yd", cur["apex"], new["apex"], True, tol=1.5),
        _metric("Landing angle", "°", cur["land"], new["land"], True, tol=1.0),
    ]

    highlights: list[str] = []
    gain_bad = new["carry_p10"] - cur["carry_p10"]
    if gain_bad >= 2:
        highlights.append(f"About {gain_bad:.0f} yd more carry on your poor strikes: mishits "
                          "still reach the green more often.")
    tighter = cur["carry_spread"] - new["carry_spread"]
    if tighter >= 2:
        highlights.append(f"Distance window about {tighter:.0f} yd tighter, so club selection "
                          "gets easier.")
    gain = new["carry"] - cur["carry"]
    loft_gap = loft - new_loft  # > 0: Takomo loft is stronger
    if gain >= 2:
        why = (f" Part of this comes from {loft_gap:g}° stronger loft, so check your wedge gaps."
               if loft_gap >= 1 else "")
        highlights.append(f"About {gain:.0f} yd more typical carry.{why}")
    elif gain <= -2:
        why = (f"its {-loft_gap:g}° weaker loft ({new_loft:g}° vs {loft:g}°)" if loft_gap <= -1
               else "its design")
        highlights.append(f"About {-gain:.0f} yd less carry: {head['name']} trades distance for "
                          f"control through {why}. Expect a higher, steeper flight.")
    steeper = new["land"] - cur["land"]
    if steeper >= 2:
        highlights.append(f"Lands about {steeper:.0f}° steeper, so the ball stops faster on greens.")
    if not highlights:
        highlights.append("Similar numbers to your current irons: the gain is fit (length, lie, "
                          "grip, shaft) rather than raw distance.")

    current_label = profile.current_irons or "Your current 7-iron"
    return ClubComparison(
        current=ClubSpec(label=current_label, loft_deg=loft, loft_source=loft_src,
                         forgiveness=fg, forgiveness_source=fg_src),
        takomo=ClubSpec(label=head["name"], loft_deg=new_loft, loft_source="takomo",
                        forgiveness=int(new_fg), forgiveness_source="takomo"),
        swing_speed_mph=round(speed, 1),
        metrics=metrics,
        highlights=highlights,
        assumptions=assumptions,
    )
