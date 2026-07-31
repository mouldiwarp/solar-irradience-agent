
import pytest
from pydantic import ValidationError

from solar_agent.config import Settings, get_settings


def test_settings_required_fields_missing(monkeypatch):
    monkeypatch.delenv("SOLAR_AGENT_LATITUDE", raising=False)
    monkeypatch.delenv("SOLAR_AGENT_LONGITUDE", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    errors = exc_info.value.errors()
    error_fields = {e["loc"][0] for e in errors}
    assert "latitude" in error_fields
    assert "longitude" in error_fields


def test_settings_defaults_applied(settings_env):
    settings = Settings()

    assert settings.timezone == "auto"
    assert settings.forecast_days == 2
    assert settings.weather_model == "best_match"
    assert settings.mode == "cli"
    assert settings.http_host == "127.0.0.1"
    assert settings.http_port == 8000
    assert settings.api_key is None
    assert settings.log_level == "INFO"
    assert settings.http_timeout_seconds == 10.0
    assert settings.retry_attempts == 3
    assert settings.retry_backoff_seconds == 1.0


def test_settings_invalid_latitude(settings_env, monkeypatch):
    monkeypatch.setenv("SOLAR_AGENT_LATITUDE", "91.0")

    with pytest.raises(ValidationError):
        Settings()


def test_settings_invalid_longitude(settings_env, monkeypatch):
    monkeypatch.setenv("SOLAR_AGENT_LONGITUDE", "181.0")

    with pytest.raises(ValidationError):
        Settings()


def test_settings_invalid_mode(settings_env, monkeypatch):
    monkeypatch.setenv("SOLAR_AGENT_MODE", "invalid")

    with pytest.raises(ValidationError):
        Settings()


def test_settings_valid_mode_cli(settings_env, monkeypatch):
    monkeypatch.setenv("SOLAR_AGENT_MODE", "cli")
    settings = Settings()
    assert settings.mode == "cli"


def test_settings_valid_mode_serve(settings_env, monkeypatch):
    monkeypatch.setenv("SOLAR_AGENT_MODE", "serve")
    settings = Settings()
    assert settings.mode == "serve"


def test_get_settings_caching(settings_env):
    get_settings.cache_clear()

    s1 = get_settings()
    s2 = get_settings()

    assert s1 is s2


def test_all_env_vars_documented(settings_env):
    documented_vars = {
        "latitude",
        "longitude",
        "timezone",
        "forecast_days",
        "weather_model",
        "mode",
        "http_host",
        "http_port",
        "api_key",
        "log_level",
        "http_timeout_seconds",
        "retry_attempts",
        "retry_backoff_seconds",
        "open_meteo_base_url",
    }

    settings_fields = set(Settings.model_fields.keys())

    missing = documented_vars - settings_fields
    extra = settings_fields - documented_vars
    assert settings_fields == documented_vars, f"Missing: {missing}, Extra: {extra}"
