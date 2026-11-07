import asyncio

from fastapi.testclient import TestClient

from app.main import app
from app.seed import seed
from app.services import catalog

client = TestClient(app)


def test_documents_round_trip():
    data = catalog.load_file()
    products, meta = catalog.to_documents(data)
    assert len(products) == 5 + 35 + 3
    assert catalog.from_documents(products, meta) == data


def test_seed_and_read_catalog_from_mongo(mongo):
    asyncio.run(seed())
    asyncio.run(seed())  # idempotent
    assert mongo._db.products.count_documents({}) == 43
    assert mongo._db.products.count_documents({"kind": "shaft"}) == 35
    mongo._db.products.update_one({"_id": "101-mkii"}, {"$set": {"description": "From Mongo"}})
    r = client.get("/api/products")
    assert r.json()["heads"][0]["description"] == "From Mongo"
    assert client.get("/api/health").json()["db"] == "mongodb"


def test_empty_mongo_falls_back_to_json(mongo):
    assert client.get("/api/products").json() == catalog.load_file()


def test_fitting_is_saved_and_continued(mongo):
    msgs = [{"role": "user", "content": "Find my irons"}]
    first = client.post("/api/chat", json={"messages": msgs}).json()
    fid = first["fitting_id"]
    assert fid

    msgs += [{"role": "assistant", "content": first["reply"]}]
    for text in ["Over 92", "Under 120 yd", "Forgiveness", "High"]:
        msgs.append({"role": "user", "content": text})
        out = client.post("/api/chat", json={"messages": msgs, "fitting_id": fid}).json()
        assert out["fitting_id"] == fid
        msgs.append({"role": "assistant", "content": out["reply"]})

    assert mongo._db.fittings.count_documents({}) == 1
    saved = client.get(f"/api/fittings/{fid}").json()
    assert saved["id"] == fid
    assert saved["messages"] == msgs
    assert saved["step"] == saved["total_steps"]
    assert saved["recommendation"]["iron_set"]["id"] == "101-mkii"
    assert saved["profile"]["score_bucket"] == 5


def test_unknown_fitting_is_404(mongo):
    assert client.get("/api/fittings/nope").status_code == 404
