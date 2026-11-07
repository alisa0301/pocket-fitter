import pytest
from takomo_fit import baseline as BL, products as PR


def A(**kw):
    base = dict(age=45, sex="male", score_bucket=4, swing_bucket=3, characteristics=["forgiveness", "distance"],
                flight="mid", tempo="moderate", height_cm=176, wrist_to_floor_cm=87.0, glove="M")
    base.update(kw)
    return BL.Answers(**base)


@pytest.mark.parametrize("h,w,lie", [(152, 86, 1), (173, 86, 0), (188, 94, 2), (196, 100, 3), (193, 76, -2)])
def test_lie_plane_reproduces_pack_examples(h, w, lie):
    assert BL.lie_for(A(height_cm=h, wrist_to_floor_cm=w), []) == lie


@pytest.mark.parametrize("h,L", [(150, -1.5), (155.4, -1.5), (155.5, -1.0), (160.4, -1.0), (160.5, -0.5),
                                 (168.4, -0.5), (168.5, 0.0), (183.4, 0.0), (183.5, 0.5), (191.4, 0.5),
                                 (191.5, 1.0), (196.4, 1.0), (196.5, 1.5)])
def test_length_by_height_table(h, L):
    for w in (0.4855 * h - 6, 0.4855 * h + 2, 0.4855 * h + 10):     # length depends on height only (PING)
        assert BL.length_for(A(height_cm=h, wrist_to_floor_cm=w), "regular", []) == L


@pytest.mark.parametrize("speed,b", [(59.9, 1), (60, 2), (70, 2), (70.1, 3), (80, 3), (80.1, 4), (90, 4), (90.1, 5)])
def test_speed_buckets(speed, b):
    assert BL.swing_bucket_from_speed(speed) == b


@pytest.mark.parametrize("carry,b", [(119, 1), (120, 2), (135, 2), (136, 3), (155, 3), (156, 4), (175, 4), (176, 5)])
def test_carry_buckets(carry, b):
    assert BL.swing_bucket_from_carry(carry) == b


@pytest.mark.parametrize("sb,sex,flex", [(1, "female", "lady"), (1, "male", "senior"), (2, "male", "senior"),
                                        (3, "male", "regular"), (4, "male", "stiff"), (5, "male", "x-stiff")])
def test_flex_table(sb, sex, flex):
    assert BL.flex_for(A(swing_bucket=sb, sex=sex)) == flex


def test_material_rules():
    assert BL.material_for(A(), "regular") == "steel"
    assert BL.material_for(A(age=70), "regular") == "graphite"
    assert BL.material_for(A(sex="female"), "regular") == "graphite"
    assert BL.material_for(A(), "senior") == "graphite"


@pytest.mark.parametrize("glove,grip", [("XS", "standard"), ("M", "standard"), ("M/L", "midsize"), ("L", "midsize"), ("XL", "oversize")])
def test_grip_by_glove(glove, grip):
    assert BL.grip_for(A(glove=glove), []) == grip


def test_every_recommendation_is_buildable():
    import itertools
    for sb, sc, sex, fl, tp in itertools.product(range(1, 6), range(1, 6), ["male", "female"], ["low", "mid", "high"],
                                                 ["smooth", "moderate", "quick"]):
        for r in BL.recommend(A(swing_bucket=sb, score_bucket=sc, sex=sex, flight=fl, tempo=tp)):
            sh = PR.shaft(r.shaft)
            assert r.head in sh["heads"]
            assert r.length_in in PR.load()["length_options_in"] and r.lie_deg in PR.load()["lie_options_deg"]
            assert r.grip in PR.GRIP_ORDER


def test_stock_rule():
    r = BL.recommend(A(height_cm=172, wrist_to_floor_cm=85.0, glove="M"))[0]
    assert r.length_in == 0 and r.lie_deg == 0 and r.grip == "standard" and r.material == "steel"
    assert r.purchase == "stock"
    r = BL.recommend(A(height_cm=172, wrist_to_floor_cm=85.0, glove="L"))[0]      # midsize is stock too
    assert r.grip == "midsize" and r.purchase == "stock"
    r = BL.recommend(A(height_cm=172, wrist_to_floor_cm=85.0, glove="XL"))[0]     # oversize forces custom
    assert r.grip == "oversize" and r.purchase == "custom"


@pytest.mark.parametrize("bucket,expected", [
    (1, [7, 5, 3, 1, 1]), (2, [4, 5, 3, 1, 1]), (3, [3, 4, 5, 3, 3]), (4, [2, 3, 4, 5, 5]), (5, [1, 2, 3, 5, 5])])
def test_speed_points_table(bucket, expected):
    parts = {s: p for s, _, p in BL.score_heads(A(swing_bucket=bucket, score_bucket=3, characteristics=[]))}
    assert [parts[h]["speed"] for h in PR.HEAD_ORDER] == expected


def test_over92_cap_only_for_buckets_4_and_5():
    capped = {s: p["speed"] for s, _, p in BL.score_heads(A(score_bucket=5, swing_bucket=5, characteristics=[]))}
    assert capped == {"101-mkii": 1, "201-mkii": 2, "201t-mkii": 3, "301-cb": 3, "301-mb": 3}
    slow = {s: p["speed"] for s, _, p in BL.score_heads(A(score_bucket=5, swing_bucket=1, characteristics=[]))}
    assert slow["101-mkii"] == 7


def test_forgiveness_penalty_hits_only_301_heads():
    parts = {s: p for s, _, p in BL.score_heads(A(characteristics=["forgiveness"]))}
    assert parts["301-cb"]["forgiveness_penalty"] == -1 and parts["301-mb"]["forgiveness_penalty"] == -1
    assert parts["201t-mkii"]["forgiveness_penalty"] == 0
    parts = {s: p for s, _, p in BL.score_heads(A(characteristics=["distance"]))}
    assert parts["301-cb"]["forgiveness_penalty"] == 0


@pytest.mark.parametrize("h,w,lie", [(175.3, 83.8, 0), (175.3, 86.4, 0), (172.7, 83.8, 0), (180.3, 87.6, 1),
                                     (182.9, 88.9, 1), (177.8, 86.4, 0)])
def test_lie_plane_agrees_with_published_ping_examples(h, w, lie):
    assert BL.lie_for(A(height_cm=h, wrist_to_floor_cm=w), []) == lie


def test_over92_speed_cap_keeps_players_heads_out():
    r = BL.recommend(A(score_bucket=5, swing_bucket=5, characteristics=["forgiveness", "distance"]))
    assert r[0].head in ("101-mkii", "201-mkii")
