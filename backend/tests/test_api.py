from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_chat_asks_first_question():
    r = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Find my irons"}]})
    assert r.status_code == 200
    data = r.json()
    assert "score" in data["reply"]
    assert data["suggestions"]



def test_products_catalog():
    r = client.get("/api/products")
    assert r.status_code == 200
    data = r.json()
    assert [h["slug"] for h in data["heads"]] == ["101-mkii", "201-mkii", "201t-mkii", "301-cb", "301-mb"]
    assert len(data["shafts"]) == 35
    assert len(data["grips"]) == 3


def test_catalog_in_system_prompt():
    from app.services import catalog, gemini

    prompt = gemini.system_prompt(catalog.load_file())
    assert "Iron 301 MB" in prompt
    assert "Takomo Obsidian" in prompt
    assert "{total_steps}" not in prompt and "{catalog}" not in prompt


def test_chat_without_mongo_has_no_fitting_id():
    r = client.post("/api/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert r.json()["fitting_id"] is None
    assert client.get("/api/health").json()["db"] == "none"
