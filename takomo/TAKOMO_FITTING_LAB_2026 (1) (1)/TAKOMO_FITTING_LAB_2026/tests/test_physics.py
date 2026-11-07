import numpy as np
from takomo_fit import physics as P


def test_tour_7iron_matches_trackman_average():
    r = P.shot(90, 20.9, -4.3)
    assert abs(float(r["ball_speed_mph"]) - 120) < 2
    assert abs(float(r["launch_deg"]) - 16.3) < 0.5
    assert abs(float(r["spin_rpm"]) - 7097) < 300
    assert abs(float(r["carry_yd"][0]) - 172) < 6


def test_more_speed_more_carry():
    c = P.shot(np.array([60, 70, 80, 90]), 24, -2.5)["carry_yd"]
    assert np.all(np.diff(c) > 0)


def test_more_loft_launches_higher_and_spins_more():
    r = P.shot(75, np.array([20, 25, 30]), -2.5)
    assert np.all(np.diff(r["launch_deg"]) > 0) and np.all(np.diff(r["spin_rpm"]) > 0)


def test_off_centre_strike_loses_ball_speed_less_with_forgiving_head():
    c = P.impact(75, 25, -2.5, offset_mm=np.array([0, 15, 15]), forgiveness=np.array([3, 5, 1]))
    assert c["ball_speed_mph"][0] > c["ball_speed_mph"][1] > c["ball_speed_mph"][2]


def test_open_face_to_path_curves_right_for_right_hander():
    r = P.shot(np.array([75, 75]), 25, -2.5, face_deg=np.array([0, 3]), path_deg=np.array([0, 0]))
    assert r["spin_axis_deg"][1] > 0 and r["side_yd"][1] > r["side_yd"][0] + 3


def test_toe_up_lie_points_face_left():
    assert P.lie_face_effect_deg(2, 25) < 0 and P.lie_face_effect_deg(-2, 25) > 0


def test_integrator_step_independent():
    a = P.fly(100, 20, 6500, dt=0.01)["carry_yd"][0]
    b = P.fly(100, 20, 6500, dt=0.02)["carry_yd"][0]
    assert abs(a - b) < 0.05
