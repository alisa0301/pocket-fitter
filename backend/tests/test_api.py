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
    assert "handicap" in data["reply"]
    assert data["suggestions"]


def test_chat_gives_recommendation_at_end():
    msgs = []
    for text in ["hi", "10-18", "140-160 m", "Slice / right"]:
        msgs.append({"role": "user", "content": text})
        msgs.append({"role": "assistant", "content": "..."})
    r = client.post("/api/chat", json={"messages": msgs[:-1]})
    assert "iron" in r.json()["reply"]


def test_products_catalog():
    r = client.get("/api/products")
    assert r.status_code == 200
    data = r.json()
    assert [h["slug"] for h in data["heads"]] == ["101-mkii", "201-mkii", "201t-mkii", "301-cb", "301-mb"]
    assert len(data["shafts"]) == 35
    assert len(data["grips"]) == 3


def test_catalog_in_system_prompt():
    from app.services import gemini

    assert "Iron 301 MB" in gemini.SYSTEM_PROMPT
    assert "Takomo Obsidian" in gemini.SYSTEM_PROMPT
