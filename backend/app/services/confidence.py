"""Calibrated confidence: how often a pick like this one is right, measured on Takomo's data.

For every spec field the "golfers like you" search gives the share of neighbours fitted with the
chosen value. scripts/calibrate_confidence.py measured, on Takomo's dev split, how often a value with
that share matches the reference fit, separately for full, partial (no body measurements) and
sparse (no swing speed / score) interviews. Here we look the share up in that table.

The overall confidence is the expected share of the spec that is right, weighted like Takomo's
Spec Agreement Score.
"""
from __future__ import annotations

import json
from bisect import bisect_right
from functools import lru_cache
from pathlib import Path

from app.schemas import PlayerProfile, SimilarGolfers

CALIBRATION_PATH = Path(__file__).resolve().parent.parent / "data" / "confidence_calibration.json"

# field -> SimilarGolfers attribute; weights from Takomo's scorer (takomo_fit/score.py)
FIELDS = {"head": "head", "flex": "flex", "material": "material", "shaft": "shaft",
          "length": "length_in", "lie": "lie_deg", "grip": "grip"}
WEIGHTS = {"head": 20, "flex": 20, "material": 10, "shaft": 5, "length": 12, "lie": 15, "grip": 8}
BODY = ("height_cm", "wrist_to_floor_cm", "glove")


def level(p: PlayerProfile) -> str:
    """How complete the interview is: full, partial (no body measurements) or sparse."""
    if not (p.speed_mph or p.carry_yd) or p.score_bucket is None:
        return "sparse"
    if any(getattr(p, f) is None for f in BODY):
        return "partial"
    return "full"


@lru_cache(maxsize=1)
def table() -> dict:
    with open(CALIBRATION_PATH, encoding="utf-8") as f:
        return json.load(f)


def share_of(found: SimilarGolfers, field: str, value: str) -> float:
    items = getattr(found, FIELDS[field])
    return next((s.share for s in items if s.value == value), 0.0)


def calibrated(field: str, share: float, lvl: str) -> float:
    t = table()
    i = min(bisect_right(t["bins"], share) - 1, len(t["bins"]) - 2)
    return t["accuracy"][lvl][field][max(i, 0)]


def per_field(found: SimilarGolfers, chosen: dict[str, str], p: PlayerProfile) -> dict[str, float]:
    """chosen: field -> picked value (as the strings SimilarGolfers uses)."""
    lvl = level(p)
    return {f: round(calibrated(f, share_of(found, f, v), lvl), 3) for f, v in chosen.items()}


def overall(fields: dict[str, float]) -> float:
    w = {f: WEIGHTS[f] for f in fields}
    return round(sum(fields[f] * w[f] for f in fields) / sum(w.values()), 2)
