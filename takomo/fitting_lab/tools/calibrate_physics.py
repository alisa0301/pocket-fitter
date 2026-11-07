"""Fit the aerodynamic coefficients in takomo_fit.physics to TrackMan tour iron averages.

Targets (TrackMan tour averages as published by Golf Magic / Golf Digest):
  PGA Tour 3i-9i and LPGA Tour 4i-9i: ball speed, launch, spin -> carry.
  7-iron apex and landing angle: PGA 32 yd / 50 deg; LPGA about 8 yd lower and
  4 deg shallower (Golf Digest Hot List 2025 summary of TrackMan data).
Run:  python tools/calibrate_physics.py   (prints fitted values; physics.py holds the frozen ones)
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
from scipy.optimize import least_squares
from takomo_fit import physics as P

PGA = [  # club, ball mph, launch, spin, carry
    ("3i", 142, 10.4, 4630, 212), ("4i", 137, 11.0, 4836, 203), ("5i", 132, 12.1, 5361, 194),
    ("6i", 127, 14.1, 6231, 183), ("7i", 120, 16.3, 7097, 172), ("8i", 115, 18.1, 7998, 160),
    ("9i", 109, 20.4, 8647, 148)]
LPGA = [("4i", 116, 14.3, 4801, 169), ("5i", 112, 14.8, 5081, 161), ("6i", 109, 17.1, 5943, 152),
        ("7i", 104, 19.0, 6699, 141), ("8i", 100, 20.8, 7494, 130), ("9i", 93, 23.9, 7589, 119)]
ROWS = PGA + LPGA
B = np.array([r[1] for r in ROWS], float); L = np.array([r[2] for r in ROWS], float)
S = np.array([r[3] for r in ROWS], float); C = np.array([r[4] for r in ROWS], float)
I7P, I7L = 4, len(PGA) + 3


def resid(x):
    aero = dict(cd0=x[0], cd1=x[1], cl1=x[2], cl_pow=x[3], spin_tau_s=25.0)
    f = P.fly(B, L, S, aero=aero)
    r = list((f["carry_yd"] - C) / 2.0)
    r += [(f["apex_yd"][I7P] - 32) / 1.5, (f["land_angle_deg"][I7P] - 50) / 1.5,
          (f["apex_yd"][I7L] - 24) / 1.5, (f["land_angle_deg"][I7L] - 46) / 1.5]
    return np.array(r)


def main():
    x0 = [0.22, 0.25, 0.45, 0.4]
    fit = least_squares(resid, x0, bounds=([0.12, 0.0, 0.1, 0.30], [0.35, 1.0, 1.5, 1.2]))
    aero = dict(cd0=fit.x[0], cd1=fit.x[1], cl1=fit.x[2], cl_pow=fit.x[3], spin_tau_s=25.0)
    print("fitted aero:", {k: round(v, 4) for k, v in aero.items()})
    f = P.fly(B, L, S, aero=aero)
    for (club, *_ , carry), c, ap, la in zip(ROWS, f["carry_yd"], f["apex_yd"], f["land_angle_deg"]):
        print(f"{club:3s} target {carry:5.0f}  model {c:6.1f}  apex {ap:5.1f}  land {la:5.1f}")
    err = f["carry_yd"] - C
    print("carry MAE %.2f yd, max %.2f" % (np.abs(err).mean(), np.abs(err).max()))

    # impact calibration check with PGA delivery: dynamic loft implied from launch
    aoa = np.array([-3.1, -3.4, -3.7, -4.1, -4.3, -4.5, -4.7])
    cs = np.array([98, 96, 94, 92, 90, 87, 85.])
    L7 = L[:7]
    dl = (L7 - P.IMPACT["launch_aoa"] * aoa) / P.IMPACT["launch_dl"]
    sl = dl - aoa
    k_fit = np.exp(np.mean(np.log(S[:7] / (cs * sl ** P.IMPACT["spin_pow"]))))
    print("implied spin_k %.3f (frozen %.3f)" % (k_fit, P.IMPACT["spin_k"]))
    im = P.impact(cs, dl, aoa)
    for i, r in enumerate(PGA):
        print(f"{r[0]} ball target {r[1]} model {im['ball_speed_mph'][i]:.1f}  spin target {r[3]} model {im['spin_rpm'][i]:.0f}")


if __name__ == "__main__":
    main()
