from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


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
