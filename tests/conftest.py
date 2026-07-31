import json
from pathlib import Path

import pytest


@pytest.fixture
def settings_env(monkeypatch):
    from solar_agent.config import get_settings

    get_settings.cache_clear()

    monkeypatch.setenv("SOLAR_AGENT_LATITUDE", "37.7749")
    monkeypatch.setenv("SOLAR_AGENT_LONGITUDE", "-122.4194")
    monkeypatch.setenv("SOLAR_AGENT_TIMEZONE", "auto")
    monkeypatch.setenv("SOLAR_AGENT_FORECAST_DAYS", "2")
    monkeypatch.setenv("SOLAR_AGENT_WEATHER_MODEL", "best_match")
    monkeypatch.setenv("SOLAR_AGENT_MODE", "cli")
    monkeypatch.setenv("SOLAR_AGENT_HTTP_HOST", "127.0.0.1")
    monkeypatch.setenv("SOLAR_AGENT_HTTP_PORT", "8000")
    monkeypatch.setenv("SOLAR_AGENT_LOG_LEVEL", "INFO")
    monkeypatch.setenv("SOLAR_AGENT_HTTP_TIMEOUT_SECONDS", "10.0")
    monkeypatch.setenv("SOLAR_AGENT_RETRY_ATTEMPTS", "3")
    monkeypatch.setenv("SOLAR_AGENT_RETRY_BACKOFF_SECONDS", "1.0")
    monkeypatch.setenv("SOLAR_AGENT_OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast")

    yield

    get_settings.cache_clear()


def load_fixture(name: str) -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / f"{name}.json"
    with open(fixture_path) as f:
        return json.load(f)
