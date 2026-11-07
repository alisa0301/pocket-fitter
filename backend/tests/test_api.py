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
