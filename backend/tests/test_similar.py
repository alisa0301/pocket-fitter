import asyncio

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import PlayerProfile
from app.seed import seed_golfers
from app.services import similar

client = TestClient(app)

BEGINNER = {"age": 62, "sex": "male", "score_bucket": 5, "carry_yd": 115,
            "characteristics": ["forgiveness", "distance", "more offset"], "flight": "high",
            "tempo": "smooth", "height_cm": 178, "wrist_to_floor_cm": 86, "glove": "L"}
SCRATCH = {"age": 28, "sex": "male", "score_bucket": 1, "speed_mph": 95,
           "characteristics": ["workability", "forged feel", "less offset"], "flight": "low",
           "tempo": "quick", "height_cm": 185, "wrist_to_floor_cm": 89, "glove": "L"}


def test_embedding_shape_and_defaults():
    assert len(similar.embed(PlayerProfile(**BEGINNER))) == similar.DIM
    assert len(similar.embed(PlayerProfile())) == similar.DIM  # empty profile still embeds


def test_bundled_golfers_match_embedding():
    golfers = similar.load_file()
    assert len(golfers) == 20000
    g = golfers[0]
    assert g["embedding"] == similar.embed(PlayerProfile(**g["profile"]))


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
