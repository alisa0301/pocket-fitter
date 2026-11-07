import pytest

from app.core.config import settings


@pytest.fixture(autouse=True)
def scripted_mode(monkeypatch):
    """Tests never hit Gemini: force the scripted fallback."""
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "decision_engine", "auto")
