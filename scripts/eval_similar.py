"""Score "golfers like you" fits on Takomo's dev split with Takomo's own scorer.

    cd backend && uv run --with pandas --with numpy python ../scripts/eval_similar.py \
        ../takomo/fitting_lab [k]

Prints the Spec Agreement Score (0-100) of today's rules (Takomo baseline B1, questionnaire only)
and of the nearest-neighbour fit, both from the same questionnaire answers.
"""
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

import pandas as pd
from build_golfers import profile_from_row

from app.services import catalog, similar

STOCK_GRIPS = {"standard", "midsize"}  # Takomo, 5 Nov 2026: midsize is stock too


def purchase(head: str, shaft: dict, length: float, lie: int, grip: str) -> str:
    stock = next(h for h in catalog.load_file()["heads"] if h["slug"] == head)["stock_shafts"]
    ok = (shaft["material"] == "steel" and shaft["model"] in stock and length == 0 and lie == 0
          and grip in STOCK_GRIPS)
    return "stock" if ok else "custom"


def knn_fit(profile, k: int) -> dict:
    neighbours = similar._search_memory(similar.embed(profile), k)
    fits = [n["fit"] for n in neighbours]
    mode = lambda key, rows=fits: Counter(r[key] for r in rows).most_common(1)[0][0]
    head = mode("head")
    shaft_slug = mode("shaft", [f for f in fits if f["head"] == head])
    shaft = next(s for s in catalog.load_file()["shafts"] if s["slug"] == shaft_slug)
    length, lie, grip = mode("length_in"), mode("lie_deg"), mode("grip")
    return {"head": head, "shaft": shaft_slug, "length_in": length, "lie_deg": lie, "grip": grip,
                "purchase": purchase(head, shaft, length, lie, grip),
                "handedness": profile.handedness or "right"}


def main(takomo_dir: str, k: int = 50) -> None:
    sys.path.insert(0, takomo_dir)
    from takomo_fit import baseline as BL
    from takomo_fit import score as S

    dev = Path(takomo_dir) / "data" / "dev"
    with open(dev / "questionnaire.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    labels = pd.read_csv(dev / "labels.csv")
    q = pd.read_csv(dev / "questionnaire.csv")

    base = []
    for _, r in q.iterrows():
        rec = BL.recommend(BL.answers_from_row(r))[0]
        base.append({"golfer_id": r.golfer_id, "head": rec.head, "shaft": rec.shaft,
                         "length_in": rec.length_in, "lie_deg": rec.lie_deg, "grip": rec.grip,
                         "purchase": rec.purchase, "handedness": rec.handedness})
    knn = [dict(golfer_id=r["golfer_id"], **knn_fit(profile_from_row(r), k)) for r in rows]

    for name, pred in (("Takomo rules (B1)", base), (f"golfers like you (k={k})", knn)):
        res = S.summary(pd.DataFrame(pred), labels)
        print(f"{name:28s} score {res['spec_agreement_score']:6.2f}  "
              f"exact {res['full_spec_exact_pct']:5.1f}%  {res.get('components', '')}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 50)
