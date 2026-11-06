from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_echo():
    r = client.post("/api/echo", json={"message": "hi"})
    assert r.status_code == 200
    assert "hi" in r.json()["reply"]
