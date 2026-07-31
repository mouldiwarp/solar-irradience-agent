import json
from pathlib import Path

import httpx
import pytest
import respx

from solar_agent.client import OpenMeteoClient
from solar_agent.forecast_service import build_forecast


def load_fixture(name: str) -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / f"{name}.json"
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
def mock_respx():
    with respx.mock(base_url="https://api.open-meteo.com/v1/forecast") as mock:
        yield mock


@pytest.fixture
def settings(settings_env):
    from solar_agent.config import get_settings

    get_settings.cache_clear()
    return get_settings()


def test_build_forecast_success(mock_respx, settings):
    primary_fixture = load_fixture("open_meteo_best_match_success")
    dwd_fixture = load_fixture("open_meteo_dwd_icon_success")

    mock_respx.get("").mock(return_value=httpx.Response(200, json=primary_fixture))

    with OpenMeteoClient(
        base_url=settings.open_meteo_base_url,
        timeout_seconds=settings.http_timeout_seconds,
        retry_attempts=settings.retry_attempts,
        retry_backoff_seconds=settings.retry_backoff_seconds,
    ) as client:
        def mock_fetch_dwd(*args, **kwargs):
            return dwd_fixture

        client.fetch_dwd_icon = mock_fetch_dwd

        result = build_forecast(settings, client)

    assert result.metadata.latitude == 37.7749
    assert result.metadata.longitude == -122.4194
    assert result.metadata.primary_model == "best_match"
    assert result.metadata.dwd_icon_model == "dwd_icon"
    assert len(result.hourly) == 48
    assert result.hourly[0].time.hour == 0
    assert result.hourly[6].ghi == 150
    assert result.hourly[6].dwd_icon_ghi == 140


def test_build_forecast_empty_hourly(mock_respx, settings):
    primary_fixture = load_fixture("open_meteo_empty_hourly")
    dwd_fixture = load_fixture("open_meteo_empty_hourly")

    mock_respx.get("").mock(return_value=httpx.Response(200, json=primary_fixture))

    with OpenMeteoClient(
        base_url=settings.open_meteo_base_url,
        timeout_seconds=settings.http_timeout_seconds,
        retry_attempts=settings.retry_attempts,
        retry_backoff_seconds=settings.retry_backoff_seconds,
    ) as client:
        client.fetch_dwd_icon = lambda *a, **k: dwd_fixture

        result = build_forecast(settings, client)

    assert len(result.hourly) == 0


def test_build_forecast_partial_data_fills_none(mock_respx, settings):
    primary_fixture = load_fixture("open_meteo_best_match_success")
    dwd_fixture = load_fixture("open_meteo_best_match_success")
    for key in [
        "time",
        "shortwave_radiation",
        "direct_normal_irradiance",
        "diffuse_radiation",
        "direct_radiation",
        "global_tilted_irradiance",
    ]:
        dwd_fixture["hourly"][key] = dwd_fixture["hourly"][key][:24]

    mock_respx.get("").mock(return_value=httpx.Response(200, json=primary_fixture))

    with OpenMeteoClient(
        base_url=settings.open_meteo_base_url,
        timeout_seconds=settings.http_timeout_seconds,
        retry_attempts=settings.retry_attempts,
        retry_backoff_seconds=settings.retry_backoff_seconds,
    ) as client:
        client.fetch_dwd_icon = lambda *a, **k: dwd_fixture

        result = build_forecast(settings, client)

    assert len(result.hourly) == 48
    assert result.hourly[0].dwd_icon_ghi is not None
    assert result.hourly[24].dwd_icon_ghi is None
    assert result.hourly[25].dwd_icon_ghi is None


def test_build_forecast_timezone_handling(mock_respx, settings):
    primary_fixture = load_fixture("open_meteo_best_match_success")
    dwd_fixture = load_fixture("open_meteo_dwd_icon_success")

    mock_respx.get("").mock(return_value=httpx.Response(200, json=primary_fixture))

    with OpenMeteoClient(
        base_url=settings.open_meteo_base_url,
        timeout_seconds=settings.http_timeout_seconds,
        retry_attempts=settings.retry_attempts,
        retry_backoff_seconds=settings.retry_backoff_seconds,
    ) as client:
        client.fetch_dwd_icon = lambda *a, **k: dwd_fixture

        result = build_forecast(settings, client)

    assert result.metadata.timezone == "America/Los_Angeles"
    assert result.hourly[0].time.tzinfo is not None or result.hourly[0].time.hour == 0
