"""Takomo iron catalog.

Source of truth is Takomo's takomo_products.json (bundled, unmodified). `python -m app.seed` loads it
into MongoDB: one document per head / shaft / grip in `products` (_id = slug, `kind` field) and the
options + fitting rules in `catalog_meta`. At runtime the catalog is read from Mongo when configured,
otherwise from the JSON file, and returned in the JSON file's shape either way.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from app.db import get_db

log = logging.getLogger(__name__)

PRODUCTS_PATH = Path(__file__).resolve().parent.parent / "data" / "takomo_products.json"
KINDS = {"heads": "head", "shafts": "shaft", "grips": "grip"}
META_ID = "takomo"

_cache: dict | None = None


@lru_cache(maxsize=1)
def load_file() -> dict:
    with open(PRODUCTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def to_documents(data: dict) -> tuple[list[dict], dict]:
    """Split the catalog into product documents and one meta document."""
    products = [
        {"_id": item["slug"], "kind": kind, "order": i, **item}
        for key, kind in KINDS.items()
        for i, item in enumerate(data[key])
    ]
    meta = {"_id": META_ID, **{k: v for k, v in data.items() if k not in KINDS}}
    return products, meta


def from_documents(products: list[dict], meta: dict) -> dict:
    data = {k: v for k, v in meta.items() if k != "_id"}
    for key, kind in KINDS.items():
        items = sorted((p for p in products if p["kind"] == kind), key=lambda p: p["order"])
        data[key] = [{k: v for k, v in p.items() if k not in ("_id", "kind", "order")} for p in items]
    return data


async def load() -> dict:
    """Catalog from Mongo (cached in memory), falling back to the bundled JSON."""
    global _cache
    if _cache is not None:
        return _cache
    db = get_db()
    if db is None:
        return load_file()
    try:
        products = await db.products.find({}).to_list(None)
        meta = await db.catalog_meta.find_one({"_id": META_ID})
    except Exception:
        log.exception("Reading catalog from MongoDB failed, using bundled JSON")
        return load_file()
    if not products or meta is None:
        log.warning("MongoDB catalog is empty (run `python -m app.seed`), using bundled JSON")
        return load_file()
    _cache = from_documents(products, meta)
    return _cache


def clear_cache() -> None:
    global _cache
    _cache = None


def _join(v: list[str] | None) -> str:
    return "/".join(v) if v else "any"


def prompt_text(d: dict) -> str:
    """Compact catalog + Takomo's lookup rules for the LLM system prompt."""
    lines = ["IRON HEADS (ratings 0-5, Takomo's relative scales):"]
    for h in d["heads"]:
        r = h["ratings"]
        lines.append(
            f"- {h['name']} [{h['slug']}]: {h['description']}. 7i loft {h['seven_iron_loft_deg']}°, "
            f"offset {h['seven_iron_offset_mm']} mm, target score {h['target_score_label']}. "
            f"distance {r['distance']}, forgiveness {r['forgiveness']}, workability {r['workability']}, "
            f"distance control {r['distance_control']}, feel {r['feel']}, offset {r['offset']}. "
            f"Stock steel shafts: {', '.join(h['stock_shafts'])}."
        )
    lines.append("SHAFTS (model build | material | flex | weight | tempo | flight | heads):")
    for s in d["shafts"]:
        build = f" {s['build']}" if s.get("build") else ""
        lines.append(
            f"- {s['model']}{build} | {s['material']} | {s['flex']} | {s['weight_g']} g | "
            f"tempo {_join(s['tempo_profile'])} | flight {_join(s['flight_profile'])} | "
            f"{', '.join(s['heads'])}"
        )
    lines.append("GRIPS: " + ", ".join(f"{g['manufacturer']} {g['name']}" for g in d["grips"]))
    lines.append(f"LENGTH options (in vs standard): {d['length_options_in']}")
    lines.append(f"LIE options (deg): {d['lie_options_deg']} ({d['lie_sign_convention']})")
    lines.append("Every head is available with every grip, length and lie option.")
    lines.append("TAKOMO FITTING RULES (starting point, not a spec):")
    lines.append(json.dumps(d["current_tool_rules"], ensure_ascii=False, separators=(",", ":")))
    return "\n".join(lines)
