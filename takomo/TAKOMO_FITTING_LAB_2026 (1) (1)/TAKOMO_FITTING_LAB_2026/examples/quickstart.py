"""Ten-minute tour of the Takomo Fitting Lab.

python examples/quickstart.py [--data data]
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from takomo_fit import baseline as BL, physics as PH, score as S

ap = argparse.ArgumentParser()
ap.add_argument("--data", default=str(Path(__file__).resolve().parents[1] / "data"))
d = Path(ap.parse_args().data)

# 1. Load the dev split ---------------------------------------------------------
q = pd.read_csv(d / "dev" / "questionnaire.csv")
labels = pd.read_csv(d / "dev" / "labels.csv")
shots = pd.read_csv(d / "dev" / "shots.csv")
print(f"dev: {len(q)} golfers, {len(shots)} shots")

# 2. Run today's tool on one golfer's own answers --------------------------------
row = q.iloc[0]
answers = BL.answers_from_row(row)
recs = BL.recommend(answers)
shown = ["score_label", "speed_or_carry", "reported_7i_carry_yd", "reported_7i_speed_mph", "height_cm",
         "wrist_to_floor_cm", "glove", "handedness"]
print("\nGolfer", row.golfer_id, "answered:", ", ".join(f"{k}={row[k]}" for k in shown if pd.notna(row[k])))
for r in recs:
    print(f"  #{r.rank} {r.head:10s} {r.shaft:28s} length {r.length_in:+.1f}  lie {r.lie_deg:+d}  {r.grip:8s} {r.purchase}")
print("  why:", *recs[0].trace, sep="\n    ")
truth = labels.set_index("golfer_id").loc[row.golfer_id]
print(f"  truth: 7-iron speed {truth.true_7i_speed_mph} mph, height {truth.true_height_cm} cm, "
      f"lie need {truth.true_lie_need_deg:+.1f} deg")
print(f"  reference: {truth.ref_head} {truth.ref_shaft} length {truth.ref_length_in:+.1f} lie {truth.ref_lie_deg:+d} "
      f"{truth.ref_grip} {truth.ref_purchase}")

# 3. Score today's tool on all dev golfers --------------------------------------
pred = []
for _, r in q.iterrows():
    x = BL.recommend(BL.answers_from_row(r))[0]
    pred.append(dict(golfer_id=r.golfer_id, head=x.head, shaft=x.shaft, length_in=x.length_in, lie_deg=x.lie_deg,
                     grip=x.grip, purchase=x.purchase, handedness=x.handedness))
res = S.summary(pd.DataFrame(pred), labels)
print("\nToday's tool on self-reports, dev split:", json.dumps({k: res[k] for k in
      ["spec_agreement_score", "full_spec_exact_pct", "component_pct"]}, indent=1))

# 4. Physics: what would this golfer carry with each Takomo 7-iron? ---------------
print("\nExpected carry (yd) for this golfer by head, from labels:",
      ", ".join(f"{h} {truth[f'exp_carry_yd_{h}']:.0f}" for h in ["101-mkii", "201-mkii", "201t-mkii", "301-cb", "301-mb"]))
r = PH.shot(club_speed_mph=75, dynamic_loft_deg=24, attack_deg=-3)
print(f"A 75 mph swing at 24 deg dynamic loft: ball {float(r['ball_speed_mph']):.0f} mph, launch "
      f"{float(r['launch_deg']):.1f} deg, spin {float(r['spin_rpm']):.0f} rpm, carry {r['carry_yd'][0]:.0f} yd")

# 5. A launch-monitor session ---------------------------------------------------
tm = shots[shots.session == "trackman_fitting"]
if len(tm):
    gid = tm.golfer_id.iloc[0]
    print(f"\nTrackMan session for {gid}, median by club:")
    print(tm[tm.golfer_id == gid].groupby("club")[["club_speed_mph", "ball_speed_mph", "launch_angle_deg",
          "spin_rate_rpm", "carry_yd", "impact_toe_up_deg"]].median().round(1).to_string())
