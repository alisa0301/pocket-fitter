import importlib

from fastapi.testclient import TestClient


def test_serves_spa(tmp_path, monkeypatch):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)")
    (tmp_path / "index.html").write_text("<div id=root></div>")

    from app.core import config

    monkeypatch.setattr(config.settings, "static_dir", str(tmp_path))
    import app.main

    client = TestClient(importlib.reload(app.main).app)
    assert client.get("/").text == "<div id=root></div>"
    assert client.get("/some/route").text == "<div id=root></div>"
    assert client.get("/assets/app.js").text == "console.log(1)"
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/nope").status_code == 404
    assert client.get("/../pyproject.toml").text == "<div id=root></div>"
