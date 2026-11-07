"""Build backend/app/data/golfers_train.jsonl.gz from Takomo's train split.

    cd backend && uv run python ../scripts/build_golfers.py "../takomo/TAKOMO_FITTING_LAB_2026 (1) (1)/TAKOMO_FITTING_LAB_2026/data/train"

One line per golfer: id, the questionnaire answers as a GolferProfile, its embedding and the
reference fit from labels.csv. Re-run after changing app.services.similar.embed().
"""
import csv
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.schemas import GolferProfile
from app.services.similar import GOLFERS_PATH, embed

HEADS = ["101-mkii", "201-mkii", "201t-mkii", "301-cb", "301-mb"]


def _f(v: str) -> float | None:
    return float(v) if v not in ("", None) else None


def profile_from_row(r: dict) -> GolferProfile:
    return GolferProfile(
        age=int(r["age"]),
        sex=r["sex"],
        handedness=r["handedness"],
        score_bucket=int(r["score_bucket"]),
        speed_mph=_f(r["reported_7i_speed_mph"]),
        carry_yd=_f(r["reported_7i_carry_yd"]),
        characteristics=[c for c in r["characteristics"].split("|") if c],
        flight=r["flight"],
        tempo=r["tempo"],
        height_cm=_f(r["height_cm"]),
        wrist_to_floor_cm=_f(r["wrist_to_floor_cm"]),
        glove=r["glove"],
    )


def fit_from_label(lab: dict) -> dict:
    return {
        "head": lab["ref_head"],
        "head_2": lab["ref_head_2"],
        "shaft": lab["ref_shaft"],
        "flex": lab["ref_flex"],
        "material": lab["ref_material"],
        "length_in": float(lab["ref_length_in"]),
        "lie_deg": int(lab["ref_lie_deg"]),
        "grip": lab["ref_grip"],
        "purchase": lab["ref_purchase"],
        "exp_carry_yd": {h: float(lab[f"exp_carry_yd_{h}"]) for h in HEADS},
    }


def read(path: Path) -> dict[str, dict]:
    with open(path, encoding="utf-8") as f:
        return {r["golfer_id"]: r for r in csv.DictReader(f)}


def main(split_dir: str) -> None:
    d = Path(split_dir)
    questions, labels = read(d / "questionnaire.csv"), read(d / "labels.csv")
    GOLFERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(GOLFERS_PATH, "wt", encoding="utf-8", compresslevel=9) as out:
        for gid, q in questions.items():
            profile = profile_from_row(q)
            doc = {
                "_id": gid,
                "profile": profile.model_dump(exclude_none=True),
                "embedding": embed(profile),
                "fit": fit_from_label(labels[gid]),
            }
            out.write(json.dumps(doc, separators=(",", ":")) + "\n")
    print(f"Wrote {len(questions)} golfers to {GOLFERS_PATH}")


if __name__ == "__main__":
    main(sys.argv[1])
