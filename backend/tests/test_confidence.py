import asyncio

from app.core.config import settings
from app.decision import engine, gemini_engine, rules
from app.schemas import PlayerProfile
from app.services import confidence

FULL = PlayerProfile(age=64, sex="male", score_bucket=5, carry_yd=115,
                     characteristics=["forgiveness", "distance", "more offset"], flight="high",
                     tempo="smooth", height_cm=178, wrist_to_floor_cm=86, glove="L")


def test_levels():
    assert confidence.level(FULL) == "full"
    assert confidence.level(FULL.model_copy(update={"glove": None})) == "partial"
    assert confidence.level(FULL.model_copy(update={"carry_yd": None})) == "sparse"
    assert confidence.level(PlayerProfile()) == "sparse"


def test_table_is_monotone_probabilities():
    t = confidence.table()
    for lvl in ("full", "partial", "sparse"):
        for field in confidence.FIELDS:
            acc = t["accuracy"][lvl][field]
            assert len(acc) == len(t["bins"]) - 1
            assert all(0 <= a <= 1 for a in acc)
            assert acc == sorted(acc)
    # held-out check: the table predicts dev accuracy within a few points
    for by_field in t["held_out_check"].values():
        assert all(v["ece"] < 0.08 for v in by_field.values())


def test_rules_reports_calibrated_field_confidence():
    rec = rules.decide(FULL)
    assert set(rec.field_confidence) == set(confidence.FIELDS)
    assert rec.confidence == confidence.overall(rec.field_confidence)
    sparse = rules.decide(PlayerProfile(score_bucket=5))
    assert sparse.field_confidence["head"] < rec.field_confidence["head"]
    assert sparse.confidence < rec.confidence


def test_gemini_confidence_is_calibrated_not_self_reported(monkeypatch):
    monkeypatch.setattr(settings, "decision_engine", "gemini")

    async def fake(prompt, system, schema, temperature=0.6):
        return schema(head="301-mb", shaft="kbs-tour-stiff-301", runner_up="301-cb", grip="standard",
                      length_in=0, lie_deg=0, adjustments=[], reasons=["r"], confidence=0.99)

    monkeypatch.setattr(gemini_engine, "generate_json", fake)
    rec = asyncio.run(engine.decide(FULL))  # a beginner's neighbours never chose a blade
    assert rec.engine == "gemini"
    assert rec.field_confidence["head"] < 0.5 and rec.confidence < 0.99
