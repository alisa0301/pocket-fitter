"""Golfers like you: nearest neighbours among Takomo's 20,000 train golfers.

Each train golfer is a vector built from the same questionnaire answers our fitter collects, plus the
reference fitting Takomo's data gives for them (labels.csv). For a new golfer we embed their answers,
find the nearest train golfers and summarise what fitted them.

Search runs on MongoDB Atlas Vector Search (`golfers` collection, index `golfer_vector`) when Mongo is
configured and seeded, and on an in-memory scan of the bundled file otherwise. Both use the same
vectors and Euclidean distance, so they return the same neighbours.
"""
from __future__ import annotations

import gzip
import json
import logging
import math
from collections import Counter
from functools import lru_cache
from pathlib import Path

from app.db import get_db
from app.schemas import PlayerProfile, SimilarGolfers, SpecShare
from app.services import catalog

log = logging.getLogger(__name__)

GOLFERS_PATH = Path(__file__).resolve().parent.parent / "data" / "golfers_train.jsonl.gz"
INDEX_NAME = "golfer_vector"

CHARACTERISTICS = ["forgiveness", "distance", "forged feel", "distance control", "workability",
                   "less offset", "more offset"]
GLOVES = ["XS", "S", "M", "M/L", "L", "XL"]
TEMPO = {"smooth": 0, "moderate": 1, "quick": 2}
FLIGHT = {"low": 0, "mid": 1, "high": 2}

# Self-reported numbers -> true 7-iron speed, least squares on the train split
# (people overstate speed; carry is rounded to 5 yd).
SPEED_FROM_REPORTED = (0.841, 10.17)
SPEED_FROM_CARRY = (0.3376, 26.65)
# With the golfer's own 7-iron loft: speed = a*carry + b*loft + c (train, golfers who know their loft).
# A stronger (lower) loft carries further for the same speed. MAE 3.55 -> 3.36 mph on train.
SPEED_FROM_CARRY_AND_LOFT = (0.3479, 0.8112, 0.133)
DEFAULT_SPEED_MPH = 72.0

# Feature scale: one unit of distance in the vector space. Smaller divisor = matters more.
# Tuned on the dev split with Takomo's scorer (scripts/eval_similar.py).
SCALES = {
    "speed": 4.0,          # mph
    "score": 0.6,          # bucket 1-5
    "height": 2.5,         # cm
    "wrist_to_floor": 4.0, # cm
    "glove": 0.8,          # size steps
    "age": 8.0,            # years
    "female": 0.3,
    "tempo": 1.0,
    "flight": 1.0,
    "characteristic": 0.6,
}
DIM = 9 + len(CHARACTERISTICS)


def estimate_speed(p: PlayerProfile) -> float:
    if p.speed_mph:
        a, b = SPEED_FROM_REPORTED
        return a * p.speed_mph + b
    if p.carry_yd:
        loft = p.current_7i_loft_deg or p.current_7i_loft_estimate_deg
        if loft:
            a, b, c = SPEED_FROM_CARRY_AND_LOFT
            return a * p.carry_yd + b * loft + c
        a, b = SPEED_FROM_CARRY
        return a * p.carry_yd + b
    return DEFAULT_SPEED_MPH


def embed(p: PlayerProfile) -> list[float]:
    s = SCALES
    female = 1.0 if p.sex == "female" else 0.0
    # Missing body measurements fall back to population means for the golfer's sex.
    height = p.height_cm or (165.0 if female else 179.0)
    wtf = p.wrist_to_floor_cm or (80.0 if female else 87.0)
    glove = GLOVES.index(p.glove) if p.glove in GLOVES else (1 if female else 3)
    vec = [
        estimate_speed(p) / s["speed"],
        (p.score_bucket or 4) / s["score"],
        height / s["height"],
        wtf / s["wrist_to_floor"],
        glove / s["glove"],
        (p.age or 50) / s["age"],
        female / s["female"],
        TEMPO.get(p.tempo or "moderate", 1) / s["tempo"],
        FLIGHT.get(p.flight or "mid", 1) / s["flight"],
    ]
    chars = set(p.characteristics[:3])
    vec += [(1.0 if c in chars else 0.0) / s["characteristic"] for c in CHARACTERISTICS]
    return [round(v, 4) for v in vec]


@lru_cache(maxsize=1)
def load_file() -> list[dict]:
    with gzip.open(GOLFERS_PATH, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def _search_memory(vec: list[float], k: int) -> list[dict]:
    scored = [(math.dist(vec, g["embedding"]), g) for g in load_file()]
    scored.sort(key=lambda t: t[0])
    return [{**g, "score": 1 / (1 + d)} for d, g in scored[:k]]


def pipeline(vec: list[float], k: int) -> list[dict]:
    return [
        {"$vectorSearch": {"index": INDEX_NAME, "path": "embedding", "queryVector": vec,
                           "numCandidates": max(10 * k, 200), "limit": k}},
        {"$project": {"embedding": 0, "score": {"$meta": "vectorSearchScore"}}},
    ]


async def _search_mongo(vec: list[float], k: int) -> list[dict] | None:
    db = get_db()
    if db is None:
        return None
    try:
        cursor = await db.golfers.aggregate(pipeline(vec, k))
        docs = await cursor.to_list(None)
    except Exception:
        log.exception("Atlas Vector Search failed, using in-memory search")
        return None
    if not docs:
        log.warning("Vector search returned nothing (seeded? index ready?), using in-memory search")
        return None
    return docs


def _shares(values: list, top: int = 3, label=None) -> list[SpecShare]:
    n = len(values)
    return [
        SpecShare(value=str(v), share=round(c / n, 3), label=label(v) if label else None)
        for v, c in Counter(values).most_common(top)
    ]


@lru_cache(maxsize=1)
def _labels() -> dict[str, str]:
    data = catalog.load_file()
    return {h["slug"]: h["name"] for h in data["heads"]} | {
        s["slug"]: catalog.shaft_name(s) for s in data["shafts"]
    }


def summarise(neighbours: list[dict], source: str) -> SimilarGolfers:
    fits = [g["fit"] for g in neighbours]
    heads = _shares([f["head"] for f in fits], label=_labels().get)
    top_head = heads[0].value
    same_head = [f for f in fits if f["head"] == top_head]
    carries = [f["exp_carry_yd"][top_head] for f in fits if f.get("exp_carry_yd")]
    return SimilarGolfers(
        count=len(neighbours),
        source=source,
        head=heads,
        shaft=_shares([f["shaft"] for f in same_head], label=_labels().get),
        flex=_shares([f["flex"] for f in fits]),
        material=_shares([f["material"] for f in fits]),
        length_in=_shares([f["length_in"] for f in fits]),
        lie_deg=_shares([f["lie_deg"] for f in fits]),
        grip=_shares([f["grip"] for f in fits]),
        purchase=_shares([f["purchase"] for f in fits]),
        expected_carry_yd=round(sum(carries) / len(carries), 1) if carries else None,
    )


def find_local(profile: PlayerProfile, k: int = 50) -> SimilarGolfers:
    return summarise(_search_memory(embed(profile), k), "in_memory")


async def find(profile: PlayerProfile, k: int = 50) -> SimilarGolfers:
    """Atlas Vector Search when available, otherwise the same search in memory."""
    vec = embed(profile)
    docs = await _search_mongo(vec, k)
    if docs is not None:
        return summarise(docs, "atlas_vector_search")
    return summarise(_search_memory(vec, k), "in_memory")


def prompt_text(s: SimilarGolfers) -> str:
    def fmt(items: list[SpecShare]) -> str:
        return ", ".join(f"{i.label or i.value} {round(i.share * 100)}%" for i in items)

    return (
        f"DATA FROM {s.count} MOST SIMILAR GOLFERS in Takomo's fitting data (their reference fits):\n"
        f"- head: {fmt(s.head)}\n- shaft (for the top head): {fmt(s.shaft)}\n"
        f"- flex: {fmt(s.flex)}; material: {fmt(s.material)}\n"
        f"- length (in vs standard): {fmt(s.length_in)}; lie (deg): {fmt(s.lie_deg)}\n"
        f"- grip: {fmt(s.grip)}; purchase: {fmt(s.purchase)}\n"
        + (f"- expected 7-iron carry with the top head: {s.expected_carry_yd} yd\n"
           if s.expected_carry_yd else "")
    )
