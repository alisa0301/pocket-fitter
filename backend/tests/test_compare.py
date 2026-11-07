from fastapi.testclient import TestClient

from app.main import app
from app.schemas import PlayerProfile
from app.services import compare

client = TestClient(app)


def test_forgiving_head_helps_mishits_for_high_scorer():
    p = PlayerProfile(score_bucket=5, carry_yd=120, current_irons="Old blades",
                      current_7i_loft_deg=34, current_forgiveness_estimate=1)
    c = compare.compare(p, "101-mkii")
    m = {x.name: x for x in c.metrics}
    assert m["Carry on your worst 10% of strikes"].better == "takomo"
    assert m["Carry window (10th-90th %)"].better == "takomo"
    assert c.current.loft_source == "you" and c.takomo.loft_deg == 29
    assert c.highlights


def test_same_head_specs_give_no_difference():
    p = PlayerProfile(score_bucket=3, speed_mph=78, current_7i_loft_deg=31,
                      current_forgiveness_estimate=4)
    c = compare.compare(p, "201-mkii")  # 31 deg, forgiveness 4
    assert all(x.better == "same" for x in c.metrics)


def test_defaults_are_flagged_as_assumptions():
    c = compare.compare(PlayerProfile(), "201-mkii")
    assert c.current.loft_source == "default" and c.current.forgiveness_source == "default"
    assert any("assumed" in a for a in c.assumptions)


def test_compare_endpoint():
    r = client.post("/api/compare", json={"profile": {"score_bucket": 4}, "head": "201t-mkii"})
    assert r.status_code == 200 and r.json()["takomo"]["label"] == "Iron 201T MKII"
    assert client.post("/api/compare", json={"profile": {}, "head": "nope"}).status_code == 404


def test_scripted_chat_includes_comparison():
    msgs = []
    for text in ["New irons", "Over 92", "120-140 yd", "Forgiveness", "High",
                 "Titleist T200, 2021", "30°"]:
        msgs.append({"role": "user", "content": text})
        r = client.post("/api/chat", json={"messages": msgs}).json()
        msgs.append({"role": "assistant", "content": r["reply"]})
    comp = r["recommendation"]["comparison"]
    assert comp["current"]["label"] == "Titleist T200, 2021"
    assert comp["current"]["loft_deg"] == 30 and comp["current"]["loft_source"] == "you"
    assert len(comp["metrics"]) == 5


def test_scripted_current_irons_is_free_text():
    from app.services import scripted

    p = scripted._profile(["hi", "Over 92", "120-140 yd", "Forgiveness", "High",
                           "Ping G425 from 2020, 7-iron is 29.5 deg", "Not sure"])
    assert p.current_irons.startswith("Ping G425") and p.current_7i_loft_deg == 29.5  # year ignored
    p = scripted._profile(["hi", "Over 92", "120-140 yd", "Forgiveness", "High", "Not sure", "33"])
    assert p.current_irons is None and p.current_7i_loft_deg == 33
