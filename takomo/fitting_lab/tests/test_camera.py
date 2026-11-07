import sys
from pathlib import Path
import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "camera"))
import sheet as SH  # noqa: E402
import measure as M  # noqa: E402
import tempo as T  # noqa: E402
import ball_line as BLT  # noqa: E402


def _photo(tmp_path, angle=0.0, persp=0.08, seed=0):
    rng = np.random.default_rng(seed)
    src = SH.render_sheet_png(tmp_path / "sheet.png", dpi=150)
    sheet = cv2.cvtColor(src, cv2.COLOR_GRAY2BGR)
    h, w = sheet.shape[:2]
    W, H = 1600, 2000
    dst = np.float32([[300, 250], [1300, 300], [1350, 1700], [250, 1650]])
    dst += rng.normal(0, 25, dst.shape).astype(np.float32)
    Hm = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]), dst)
    canvas = np.full((H, W, 3), 90, np.uint8)
    warped = cv2.warpPerspective(sheet, Hm, (W, H), dst=canvas, borderMode=cv2.BORDER_TRANSPARENT)
    px_per_mm = w / SH.A4_W
    to_img = lambda mm: (Hm @ np.array([mm[0] * px_per_mm, mm[1] * px_per_mm, 1.0]))[:2] / (Hm @ np.array([mm[0] * px_per_mm, mm[1] * px_per_mm, 1.0]))[2]
    return warped, to_img


def test_sheet_measures_known_distance(tmp_path):
    img, to_img = _photo(tmp_path)
    plane = SH.SheetPlane(img)
    assert len(plane.ids) == 4 and plane.reprojection_mm < 1.0
    a, b = to_img((60, 70)), to_img((60, 260))          # 190 mm apart on the sheet
    assert abs(M.hand_length_mm(plane, a, b) - 190.0) < 1.5


def test_body_measures_vertical_in_plane(tmp_path):
    img, to_img = _photo(tmp_path, seed=1)
    plane = SH.SheetPlane(img)
    h, w = M.body_measures_cm(plane, to_img((100, 20)), to_img((100, 150)), to_img((100, 280)))
    assert abs(h - 26.0) < 0.3 and abs(w - 13.0) < 0.3


def test_tempo_on_synthetic_wrist_track():
    fps, back, down = 240, 0.90, 0.30
    t = np.arange(0, 0.3 + back + down + 0.3, 1 / fps)
    y = np.full_like(t, 800.0)
    t0, t1, t2 = 0.3, 0.3 + back, 0.3 + back + down
    s = (t >= t0) & (t < t1)
    y[s] = 800 - 500 * np.sin(np.pi / 2 * (t[s] - t0) / back) ** 2
    s = (t >= t1) & (t < t2)
    y[s] = 300 + 500 * ((t[s] - t1) / down) ** 2
    r = T.tempo_from_wrist_y(y, fps)
    assert abs(r["backswing_s"] - back) < 0.08 and abs(r["downswing_s"] - down) < 0.03
    assert 2.6 < r["ratio"] < 3.4


def _track(fps, back, down, finish_px=0.0, impact_px=0.0):
    t = np.arange(0, 0.3 + back + down + 0.8, 1 / fps)
    y = np.full_like(t, 800.0)
    t0, t1, t2 = 0.3, 0.3 + back, 0.3 + back + down
    s = (t >= t0) & (t < t1)
    y[s] = 800 - 500 * np.sin(np.pi / 2 * (t[s] - t0) / back) ** 2
    s = (t >= t1) & (t < t2)
    y[s] = 300 + (500 - impact_px) * ((t[s] - t1) / down) ** 2
    s = t >= t2                                   # follow-through to a high finish
    y[s] = (800 - impact_px) - (500 + finish_px) * np.sin(np.pi / 2 * np.clip((t[s] - t2) / 0.5, 0, 1))
    return y


@pytest.mark.parametrize("finish_px,impact_px", [(0, 0), (80, 0), (0, 20), (80, 20)])
def test_tempo_with_high_finish_and_high_impact(finish_px, impact_px):
    r = T.tempo_from_wrist_y(_track(240, 0.9, 0.3, finish_px, impact_px), 240)
    assert abs(r["downswing_s"] - 0.3) < 0.03 and 2.6 < r["ratio"] < 3.4


def test_ball_line_tilt_sign():
    heel, toe = (100, 500), (400, 500)
    assert BLT.tilt_deg((250, 500), (250, 400), heel, toe) == 0
    assert BLT.tilt_deg((250, 500), (270, 400), heel, toe) > 0      # leans toward toe
    assert BLT.tilt_deg((250, 500), (230, 400), heel, toe) < 0
    assert BLT.tilt_deg((270, 400), (250, 500), heel, toe) > 0      # points in either order
