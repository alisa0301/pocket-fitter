"""Build backend/app/data/confidence_calibration.json on Takomo's dev split.

    cd backend && uv run --with numpy python ../scripts/calibrate_confidence.py ../takomo/fitting_lab

For each dev golfer (three times: full answers, without body measurements, without speed/carry and
score) we run the "golfers like you" search over the train golfers and, for every value the
neighbours chose per spec field (top 3, plus a not-chosen value at share 0), record its neighbour
share and whether it equals the reference fit. So the table answers "how often is a value that
this share of similar golfers got right?", for the engine's top pick and for any other pick. Accuracy per share bin,
smoothed and made monotone, is the calibration table. Half of dev is held out to report how well
the table predicts accuracy (expected calibration error).
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np
from build_golfers import profile_from_row

from app.services import similar
from app.services.confidence import CALIBRATION_PATH, FIELDS

K = 50
BINS = [0.0, 0.05, 0.15, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0001]
PRIOR = 20  # pseudo-counts pulling sparse bins toward the field's overall accuracy
FIT_KEY = {"head": "head", "flex": "flex", "material": "material", "shaft": "shaft",
           "length": "length_in", "lie": "lie_deg", "grip": "grip"}
REF_KEY = {"head": "ref_head", "flex": "ref_flex", "material": "ref_material", "shaft": "ref_shaft",
           "length": "ref_length_in", "lie": "ref_lie_deg", "grip": "ref_grip"}
MASKS = {
    "full": (),
    "partial": ("height_cm", "wrist_to_floor_cm", "glove"),
    "sparse": ("height_cm", "wrist_to_floor_cm", "glove", "speed_mph", "carry_yd", "score_bucket"),
}


def read(path: Path) -> dict[str, dict]:
    with open(path, encoding="utf-8") as f:
        return {r["golfer_id"]: r for r in csv.DictReader(f)}


def pava(y: list[float], w: list[float]) -> list[float]:
    """Pool-adjacent-violators: non-decreasing fit."""
    blocks = [[v, wt, 1] for v, wt in zip(y, w, strict=True)]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][0] > blocks[i + 1][0]:
            a, b = blocks[i], blocks[i + 1]
            wt = a[1] + b[1]
            blocks[i] = [(a[0] * a[1] + b[0] * b[1]) / wt, wt, a[2] + b[2]]
            del blocks[i + 1]
            i = max(i - 1, 0)
        else:
            i += 1
    return [v for v, _, n in blocks for _ in range(n)]


def observations(rows, golfers, labels, train_vecs, fits):
    """-> {level: {field: (shares, correct)}} for the given dev rows."""
    out = {lvl: {f: ([], []) for f in FIELDS} for lvl in MASKS}
    for lvl, drop in MASKS.items():
        profiles = []
        for r in rows:
            p = profile_from_row(r, golfers[r["golfer_id"]]["own_7i_loft_deg"])
            profiles.append(p.model_copy(update=dict.fromkeys(drop)))
        vecs = np.array([similar.embed(p) for p in profiles])
        for i in range(0, len(vecs), 500):
            d = ((vecs[i : i + 500, None, :] - train_vecs[None]) ** 2).sum(-1)
            idx = np.argsort(d, axis=1)[:, :K]
            for j, nb in enumerate(idx):
                lab = labels[rows[i + j]["golfer_id"]]
                nf = [fits[t] for t in nb]
                head = Counter(f["head"] for f in nf).most_common(1)[0][0]
                for field in FIELDS:
                    pool = [f for f in nf if f["head"] == head] if field == "shaft" else nf
                    counts = Counter(f[FIT_KEY[field]] for f in pool).most_common(3)
                    ref = lab[REF_KEY[field]]

                    def same(v, ref=ref, field=field):
                        return float(v) == float(ref) if field in ("length", "lie") else v == ref

                    for value, count in counts:
                        out[lvl][field][0].append(count / len(pool))
                        out[lvl][field][1].append(1.0 if same(value) else 0.0)
                    if len(counts) < 3:  # a value none of the neighbours got: is the reference it?
                        out[lvl][field][0].append(0.0)
                        out[lvl][field][1].append(0.0 if any(same(v) for v, _ in counts) else 1.0)
    return out


def fit_table(obs):
    acc = {}
    for lvl, by_field in obs.items():
        acc[lvl] = {}
        for field, (shares, correct) in by_field.items():
            shares, correct = np.array(shares), np.array(correct)
            base = correct.mean()
            b = np.clip(np.digitize(shares, BINS) - 1, 0, len(BINS) - 2)
            n = np.bincount(b, minlength=len(BINS) - 1)
            hits = np.bincount(b, weights=correct, minlength=len(BINS) - 1)
            smoothed = (hits + PRIOR * base) / (n + PRIOR)
            acc[lvl][field] = [round(v, 3) for v in pava(list(smoothed), list(n + PRIOR))]
    return acc


def ece(obs, acc):
    """Expected calibration error: |predicted - observed| averaged over bins, weighted by count."""
    res = {}
    for lvl, by_field in obs.items():
        res[lvl] = {}
        for field, (shares, correct) in by_field.items():
            shares, correct = np.array(shares), np.array(correct)
            b = np.clip(np.digitize(shares, BINS) - 1, 0, len(BINS) - 2)
            pred = np.array(acc[lvl][field])[b]
            err = sum(abs(pred[b == i].mean() - correct[b == i].mean()) * (b == i).sum()
                      for i in range(len(BINS) - 1) if (b == i).any())
            res[lvl][field] = {"ece": round(err / len(b), 3), "accuracy": round(correct.mean(), 3),
                               "predicted": round(pred.mean(), 3)}
    return res


def main(takomo_dir: str) -> None:
    dev = Path(takomo_dir) / "data" / "dev"
    questions = list(read(dev / "questionnaire.csv").values())
    golfers, labels = read(dev / "golfers.csv"), read(dev / "labels.csv")
    train = similar.load_file()
    train_vecs = np.array([g["embedding"] for g in train])
    fits = [g["fit"] for g in train]

    half = len(questions) // 2
    fit_obs = observations(questions[:half], golfers, labels, train_vecs, fits)
    check = ece(observations(questions[half:], golfers, labels, train_vecs, fits), fit_table(fit_obs))
    table = fit_table(observations(questions, golfers, labels, train_vecs, fits))  # all of dev

    out = {"source": "Takomo dev split, golfers-like-you top pick vs reference fit (exact match)",
           "k": K, "bins": BINS, "accuracy": table, "held_out_check": check}
    with open(CALIBRATION_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"Wrote {CALIBRATION_PATH}")
    for lvl, by_field in check.items():
        print(lvl, {f: (v["accuracy"], v["predicted"], v["ece"]) for f, v in by_field.items()})


if __name__ == "__main__":
    main(sys.argv[1])
