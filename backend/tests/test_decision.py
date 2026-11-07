import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.decision import engine, gemini_engine, rules
from app.main import app
from app.schemas import PlayerProfile
from app.services import catalog

client = TestClient(app)

BEGINNER = PlayerProfile(age=64, sex="male", score_bucket=5, carry_yd=115,
                         characteristics=["forgiveness", "distance", "more offset"], flight="high",
                         tempo="smooth", height_cm=178, wrist_to_floor_cm=86, glove="L")
SCRATCH = PlayerProfile(age=28, sex="male", score_bucket=1, speed_mph=95,
                        characteristics=["workability", "forged feel", "less offset"], flight="low",
                        tempo="quick", height_cm=185, wrist_to_floor_cm=89, glove="L")


@pytest.mark.parametrize(
    ("profile", "heads", "material"),
    [(BEGINNER, {"101-mkii"}, "graphite"), (SCRATCH, {"301-cb", "301-mb"}, "steel")],
)
def test_rules_engine(profile, heads, material):
    rec = rules.decide(profile)
    assert rec.iron_set.id in heads
    assert catalog.shaft(rec.shaft.id)["material"] == material
    assert catalog.is_buildable(rec.iron_set.id, rec.shaft.id, rec.length_in, rec.lie_deg, rec.grip)
    assert rec.purchase == catalog.purchase_for(rec.iron_set.id, rec.shaft.id, rec.length_in,
                                                rec.lie_deg, rec.grip)
    assert rec.engine == "rules" and rec.similar and rec.similar.count == 50
    assert 0 <= rec.confidence <= 1


def test_rules_handles_empty_profile():
    rec = rules.decide(PlayerProfile())
    assert rec.iron_set.id and rec.shaft.id
    assert rec.confidence < rules.decide(BEGINNER).confidence


def test_decide_endpoint():
    r = client.post("/api/decide", json={"score_bucket": 3, "speed_mph": 80})
    assert r.status_code == 200
    assert r.json()["engine"] == "rules"
    assert r.json()["similar"]["count"] == 50


def test_scripted_chat_ends_with_recommendation():
    msgs = []
    for text in ["New irons", "Over 92", "Under 120 yd", "Forgiveness", "High", "Not sure", "Not sure"]:
        msgs.append({"role": "user", "content": text})
        r = client.post("/api/chat", json={"messages": msgs}).json()
        msgs.append({"role": "assistant", "content": r["reply"]})
    assert r["step"] == r["total_steps"]
    assert r["profile"]["score_bucket"] == 5 and r["profile"]["carry_yd"] == 110
    assert r["recommendation"]["iron_set"]["id"] == "101-mkii"


def _fake_gemini(monkeypatch, **decision):
    monkeypatch.setattr(settings, "decision_engine", "gemini")
    seen = {}

    async def fake(prompt, system, schema, temperature=0.6):
        seen["prompt"], seen["system"] = prompt, system
        base = {"head": "201-mkii", "shaft": "kbs-tour-lite-regular", "runner_up": "101-mkii",
                    "grip": "midsize", "length_in": 0.5, "lie_deg": 1, "adjustments": ["a"], "reasons": ["r"],
                    "confidence": 0.8}
        return schema(**(base | decision))

    monkeypatch.setattr(gemini_engine, "generate_json", fake)
    return seen


def test_gemini_engine_uses_similar_golfers(monkeypatch):
    seen = _fake_gemini(monkeypatch)
    rec = asyncio.run(engine.decide(BEGINNER))
    assert rec.engine == "gemini" and rec.iron_set.id == "201-mkii"
    assert rec.runner_up.id == "101-mkii" and rec.purchase == "custom"
    assert "MOST SIMILAR GOLFERS" in seen["prompt"] and "Iron 301 MB" in seen["system"]
    assert rec.similar and rec.similar.count == 50


def test_gemini_engine_rejects_unbuildable_spec(monkeypatch):
    _fake_gemini(monkeypatch, shaft="obsidian-95-r")  # Obsidian is not offered on the 201 MKII
    rec = asyncio.run(engine.decide(BEGINNER))
    assert rec.engine == "rules"


def test_engine_failure_falls_back_to_rules(monkeypatch):
    monkeypatch.setattr(settings, "decision_engine", "jeff")  # placeholder raises
    assert asyncio.run(engine.decide(BEGINNER)).engine == "rules"


def test_every_head_has_media():
    from app.services import catalog

    for head in catalog.load_file()["heads"]:
        m = catalog.media(head["slug"])
        assert m["image_url"].startswith("https://cdn.shopify.com/"), head["slug"]
        assert m["url"].startswith("https://takomogolf.com/products/"), head["slug"]
