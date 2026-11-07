"""Takomo iron catalog (unmodified copy of Takomo's takomo_products.json)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

PRODUCTS_PATH = Path(__file__).resolve().parent.parent / "data" / "takomo_products.json"


@lru_cache(maxsize=1)
def load() -> dict:
    with open(PRODUCTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def heads() -> list[dict]:
    return load()["heads"]


def shafts(head_slug: str | None = None) -> list[dict]:
    items = load()["shafts"]
    return [s for s in items if head_slug in s["heads"]] if head_slug else items


def _join(v: list[str] | None) -> str:
    return "/".join(v) if v else "any"


@lru_cache(maxsize=1)
def prompt_text() -> str:
    """Compact catalog + Takomo's lookup rules for the LLM system prompt."""
    d = load()
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
