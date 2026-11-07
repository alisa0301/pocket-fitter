"""Write takomo_fit/data/static_fit_chart.csv: the static chart as implemented."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np, pandas as pd
from takomo_fit import baseline as BL

rows = []
for h in np.arange(145, 206, 1.0):
    for w in np.arange(70, 106, 0.5):
        a = BL.Answers(age=40, sex="male", score_bucket=3, swing_bucket=3, characteristics=[], flight="mid",
                       tempo="moderate", height_cm=h, wrist_to_floor_cm=w, glove="M")
        rows.append(dict(height_cm=h, height_ft_in=f"{int(h / 2.54 // 12)}'{h / 2.54 % 12:.1f}\"",
                         wrist_to_floor_cm=w, wrist_to_floor_in=round(w / 2.54, 2),
                         length_in=BL.length_for(a, "regular", []), lie_deg=BL.lie_for(a, [])))
out = Path(__file__).resolve().parents[1] / "takomo_fit" / "data" / "static_fit_chart.csv"
pd.DataFrame(rows).to_csv(out, index=False)
print(out, len(rows))
