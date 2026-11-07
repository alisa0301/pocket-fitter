import asyncio

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import GolferProfile
from app.seed import seed_golfers
from app.services import gemini, similar

client = TestClient(app)

BEGINNER = {"age": 62, "sex": "male", "score_bucket": 5, "carry_yd": 115,
            "characteristics": ["forgiveness", "distance", "more offset"], "flight": "high",
            "tempo": "smooth", "height_cm": 178, "wrist_to_floor_cm": 86, "glove": "L"}
SCRATCH = {"age": 28, "sex": "male", "score_bucket": 1, "speed_mph": 95,
           "characteristics": ["workability", "forged feel", "less offset"], "flight": "low",
           "tempo": "quick", "height_cm": 185, "wrist_to_floor_cm": 89, "glove": "L"}


def test_embedding_shape_and_defaults():
    assert len(similar.embed(GolferProfile(**BEGINNER))) == similar.DIM
    assert len(similar.embed(GolferProfile())) == similar.DIM  # empty profile still embeds


def test_bundled_golfers_match_embedding():
    golfers = similar.load_file()
    assert len(golfers) == 20000
    g = golfers[0]
    assert g["embedding"] == similar.embed(GolferProfile(**g["profile"]))


def test_similar_endpoint_in_memory():
    beginner = client.post("/api/similar", json=BEGINNER).json()
    scratch = client.post("/api/similar", json=SCRATCH).json()
    assert beginner["source"] == "in_memory" and beginner["count"] == 50
    assert beginner["head"][0]["value"] == "101-mkii"
    assert scratch["head"][0]["value"] in ("301-cb", "301-mb")
    assert beginner["material"][0]["value"] == "graphite"
    assert scratch["flex"][0]["value"] == "x-stiff" or scratch["flex"][0]["value"] == "stiff"
    assert 0 < sum(s["share"] for s in beginner["head"]) <= 1


def test_vector_search_used_when_atlas_answers(mongo, monkeypatch):
    docs = [{**g, "score": 0.9} for g in similar.load_file()[:10]]
    seen = {}

    class _Cursor:
        async def to_list(self, length=None):
            return docs

    async def aggregate(pipeline):
        seen["pipeline"] = pipeline
        return _Cursor()

    monkeypatch.setattr(type(mongo.golfers), "aggregate",
                        lambda self, p: aggregate(p) if self._coll.name == "golfers" else None)
    out = client.post("/api/similar?k=10", json=BEGINNER).json()
    assert out["source"] == "atlas_vector_search" and out["count"] == 10
    stage = seen["pipeline"][0]["$vectorSearch"]
    assert stage["index"] == similar.INDEX_NAME and stage["limit"] == 10
    assert len(stage["queryVector"]) == similar.DIM


def test_falls_back_when_vector_search_unavailable(mongo):
    # mongomock has no $vectorSearch -> error -> in-memory search
    assert client.post("/api/similar", json=BEGINNER).json()["source"] == "in_memory"


def test_seed_golfers(mongo):
    asyncio.run(seed_golfers(mongo))
    assert mongo._db.golfers.count_documents({}) == 20000
    assert mongo._db.golfers.find_one({}, {"fit": 1})["fit"]["head"]


def test_gemini_recommends_with_similar_golfers(monkeypatch):
    calls = []

    async def fake_generate(contents, system):
        calls.append(system)
        if len(calls) == 1:
            return gemini._Answer(reply="Let me check golfers like you...", step=4,
                                  profile=GolferProfile(**BEGINNER), ready_to_recommend=True)
        return gemini._Answer(reply="Iron 101 MKII with KBS Tour Lite...", step=4)

    monkeypatch.setattr(gemini, "_generate", fake_generate)
    from app.schemas import Message

    out = asyncio.run(gemini.reply([Message(role="user", content="go")]))
    assert len(calls) == 2
    assert "MOST SIMILAR GOLFERS" in calls[1] and "MOST SIMILAR GOLFERS" not in calls[0]
    assert out.reply.startswith("Iron 101 MKII")
    assert out.step == out.total_steps == gemini.TOTAL_STEPS
    assert out.similar and out.similar.head[0].value == "101-mkii"
    assert out.profile.carry_yd == 115


def test_recommends_once_even_without_flag(monkeypatch):
    async def fake_generate(contents, system):
        # model covered all topics but forgot ready_to_recommend
        return gemini._Answer(reply="x", step=gemini.TOTAL_STEPS - 1, profile=GolferProfile(**BEGINNER))

    monkeypatch.setattr(gemini, "_generate", fake_generate)
    from app.schemas import Message

    msgs = [Message(role="user", content="go")]
    assert asyncio.run(gemini.reply(msgs)).similar is not None
    assert asyncio.run(gemini.reply(msgs, recommended=True)).similar is None
