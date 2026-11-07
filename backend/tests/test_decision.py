import pytest
from fastapi.testclient import TestClient

from app.decision import rules
from app.main import app
from app.schemas import PlayerProfile

client = TestClient(app)


@pytest.mark.parametrize(
    ("profile", "iron", "shaft"),
    [
        (PlayerProfile(handicap=2, seven_iron_carry_m=172, typical_miss="straight"),
         "players-blade", "steel-130-x"),
        (PlayerProfile(handicap=14, seven_iron_carry_m=145, typical_miss="slice"),
         "game-improvement", "steel-105-r"),
        (PlayerProfile(handicap=30, seven_iron_carry_m=105, typical_miss="slice", age=68),
         "max-forgiveness", "graphite-60-a"),
    ],
)
def test_rules_engine(profile, iron, shaft):
    rec = rules.decide(profile)
    assert (rec.iron_set.id, rec.shaft.id) == (iron, shaft)
    assert rec.engine == "rules"
    assert 0 <= rec.confidence <= 1


def test_rules_handles_empty_profile():
    rec = rules.decide(PlayerProfile())
    assert rec.iron_set.id and rec.shaft.id
    assert rec.confidence < 0.5


def test_decide_endpoint():
    r = client.post("/api/decide", json={"handicap": 14, "seven_iron_carry_m": 145})
    assert r.status_code == 200
    assert r.json()["engine"] == "rules"


def test_scripted_chat_ends_with_recommendation():
    msgs = []
    for text in ["New irons", "10-18", "140-160 m", "Slice / right"]:
        msgs.append({"role": "user", "content": text})
        r = client.post("/api/chat", json={"messages": msgs}).json()
        msgs.append({"role": "assistant", "content": r["reply"]})
    assert r["step"] == r["total_steps"]
    assert r["profile"]["handicap"] == 14
    assert r["recommendation"]["iron_set"]["id"] == "game-improvement"


def test_shaft_ranges_do_not_overlap():
    from itertools import pairwise

    from app.catalog import SHAFTS

    ranges = sorted((s.carry_min_m, s.carry_max_m) for s in SHAFTS)
    for (_, hi), (lo, _) in pairwise(ranges):
        assert hi <= lo
