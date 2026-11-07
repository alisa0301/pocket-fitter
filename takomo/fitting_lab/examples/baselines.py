"""Two reference baselines, both scored on the dev split.

B1  questionnaire only: today's tool on the golfer's own answers.
B2  simple evidence substitution: the same rules, but every answer that has a
    phone or launch-monitor measurement is replaced by that measurement.
    No modelling, no uncertainty: a floor for what data capture alone buys.

python examples/baselines.py --data data/dev
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from takomo_fit import baseline as BL, score as S, products as PR

GLOVE_EDGES_CM = PR.GLOVE_EDGES_CM   # stated in docs/DATA_DICTIONARY.md


def predict(q, phone=None, shots=None, tests=None):
    ph = phone.set_index("golfer_id") if phone is not None else None
    speed = toe = None
    if shots is not None and len(shots):
        speed = shots[shots["club"] == "own_7i"].groupby("golfer_id")["club_speed_mph"].median()
        # Takomo test clubs are built at standard lie (0), so mean toe-up = standard - need
        tk = shots[shots["club"].str.startswith("takomo_")]
        toe = tk.groupby("golfer_id")["impact_toe_up_deg"].mean()
    tilt = None
    if tests is not None and len(tests):
        tilt = tests[tests["test"] == "ball_line_tilt"].groupby("golfer_id")["value"].mean()
    rows = []
    for _, r in q.iterrows():
        a = BL.answers_from_row(r)
        lie_from_evidence = None
        if ph is not None:
            p = ph.loc[r.golfer_id]
            if not np.isnan(p.height_photo_cm): a.height_cm = p.height_photo_cm
            if not np.isnan(p.wrist_to_floor_photo_cm): a.wrist_to_floor_cm = p.wrist_to_floor_photo_cm
            if not np.isnan(p.hand_length_photo_cm):
                a.glove = PR.GLOVE_ORDER[int(np.digitize(p.hand_length_photo_cm, GLOVE_EDGES_CM))]
            if not np.isnan(p.clubhead_speed_video_mph):
                a.swing_bucket = BL.swing_bucket_from_speed(p.clubhead_speed_video_mph)
            if not np.isnan(p.backswing_video_s):
                tot = p.backswing_video_s + p.downswing_video_s
                a.tempo = "quick" if tot < 1.05 else "smooth" if tot > 1.35 else "moderate"
        if speed is not None and r.golfer_id in speed.index:
            a.swing_bucket = BL.swing_bucket_from_speed(speed.loc[r.golfer_id])
        if toe is not None and r.golfer_id in toe.index:
            lie_from_evidence = -toe.loc[r.golfer_id]
        elif tilt is not None and r.golfer_id in tilt.index:
            # own club lie is unknown; assume standard. Tilt is exaggerated by face angle (noise).
            lie_from_evidence = -tilt.loc[r.golfer_id]
        rec = BL.recommend(a)[0]
        lie = rec.lie_deg if lie_from_evidence is None else int(np.clip(round(lie_from_evidence), -3, 3))
        buy = BL.purchase_for(rec.head, PR.shaft(rec.shaft), rec.length_in, lie, rec.grip)
        rows.append(dict(golfer_id=r.golfer_id, head=rec.head, shaft=rec.shaft, length_in=rec.length_in,
                         lie_deg=lie, grip=rec.grip, purchase=buy, handedness=rec.handedness))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/dev")
    ap.add_argument("--labels", default=None, help="labels.csv (default: <data>/labels.csv)")
    ap.add_argument("--out", default=None, help="folder to write predictions")
    a = ap.parse_args()
    d = Path(a.data)
    q = pd.read_csv(d / "questionnaire.csv")
    ph = pd.read_csv(d / "phone_measurements.csv")
    sh = pd.read_csv(d / "shots.csv")
    te = pd.read_csv(d / "home_tests.csv")
    b1 = predict(q)
    b2 = predict(q, ph, sh, te)
    res = {}
    lab = Path(a.labels) if a.labels else d / "labels.csv"
    if lab.exists():
        L = pd.read_csv(lab)
        res = {"B1_questionnaire_only": S.summary(b1, L), "B2_evidence_substitution": S.summary(b2, L)}
        print(json.dumps(res, indent=2))
    if a.out:
        Path(a.out).mkdir(parents=True, exist_ok=True)
        b1.to_csv(Path(a.out) / "B1_predictions.csv", index=False)
        b2.to_csv(Path(a.out) / "B2_predictions.csv", index=False)
    return res


if __name__ == "__main__":
    main()
