from pathlib import Path

import httpx
import pytest
import respx

from solar_agent.client import (
    OpenMeteoAPIError,
    OpenMeteoClient,
    OpenMeteoConnectionError,
    OpenMeteoInvalidResponseError,
    OpenMeteoTimeoutError,
)


def load_fixture(name: str) -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / f"{name}.json"
    import json as json_mod
    with open(fixture_path) as f:
        return json_mod.load(f)


@pytest.fixture
def mock_respx():
    with respx.mock(base_url="https://api.open-meteo.com/v1/forecast") as mock:
        yield mock


def test_fetch_primary_success(mock_respx, settings_env):
    fixture = load_fixture("open_meteo_best_match_success")
    mock_respx.get("").mock(return_value=httpx.Response(200, json=fixture))

    client = OpenMeteoClient(
        base_url="https://api.open-meteo.com/v1/forecast",
        timeout_seconds=10.0,
        retry_attempts=3,
        retry_backoff_seconds=1.0,
    )

    result = client.fetch_primary(37.7749, -122.4194, "auto", 2, "best_match")

    assert result["latitude"] == 37.7749
    assert result["hourly"]["time"] is not None
    assert len(result["hourly"]["time"]) > 0
    client.close()


def test_fetch_dwd_icon_success(mock_respx, settings_env):
    fixture = load_fixture("open_meteo_dwd_icon_success")
    mock_respx.get("").mock(return_value=httpx.Response(200, json=fixture))

    client = OpenMeteoClient(
        base_url="https://api.open-meteo.com/v1/forecast",
        timeout_seconds=10.0,
        retry_attempts=3,
        retry_backoff_seconds=1.0,
    )

    result = client.fetch_dwd_icon(37.7749, -122.4194, "auto", 2)

    assert result["latitude"] == 37.7749
    assert "dwd_icon" in str(result) or result["hourly"]["time"] is not None
    client.close()


def test_client_400_error_no_retry(mock_respx, settings_env):
    fixture = load_fixture("open_meteo_error_400")
    mock_respx.get("").mock(return_value=httpx.Response(400, json=fixture))

    client = OpenMeteoClient(
        base_url="https://api.open-meteo.com/v1/forecast",
        timeout_seconds=10.0,
        retry_attempts=3,
        retry_backoff_seconds=1.0,
    )

    with pytest.raises(OpenMeteoAPIError) as exc_info:
        client.fetch_primary(37.7749, -122.4194, "auto", 2, "best_match")

    assert exc_info.value.status_code == 400
    assert len(mock_respx.calls) == 1
    client.close()


def test_client_429_retries_then_fails(mock_respx, settings_env):
    fixture = load_fixture("open_meteo_error_400")
    mock_respx.get("").mock(return_value=httpx.Response(429, json=fixture))

    client = OpenMeteoClient(
        base_url="https://api.open-meteo.com/v1/forecast",
        timeout_seconds=10.0,
        retry_attempts=3,
        retry_backoff_seconds=0.01,
    )

    with pytest.raises(OpenMeteoAPIError) as exc_info:
        client.fetch_primary(37.7749, -122.4194, "auto", 2, "best_match")

    assert exc_info.value.status_code == 429
    assert len(mock_respx.calls) == 3
    client.close()


def test_client_500_retries_then_fails(mock_respx, settings_env):
    fixture = load_fixture("open_meteo_error_400")
    mock_respx.get("").mock(return_value=httpx.Response(500, json=fixture))

    client = OpenMeteoClient(
        base_url="https://api.open-meteo.com/v1/forecast",
        timeout_seconds=10.0,
        retry_attempts=3,
        retry_backoff_seconds=0.01,
    )

    with pytest.raises(OpenMeteoAPIError) as exc_info:
        client.fetch_primary(37.7749, -122.4194, "auto", 2, "best_match")

    assert exc_info.value.status_code == 500
    assert len(mock_respx.calls) == 3
    client.close()


def test_client_timeout_retries_then_fails(mock_respx, settings_env):
    mock_respx.get("").mock(side_effect=httpx.TimeoutException("timeout"))

    client = OpenMeteoClient(
        base_url="https://api.open-meteo.com/v1/forecast",
        timeout_seconds=10.0,
        retry_attempts=3,
        retry_backoff_seconds=0.01,
    )

    with pytest.raises(OpenMeteoTimeoutError):
        client.fetch_primary(37.7749, -122.4194, "auto", 2, "best_match")

    assert len(mock_respx.calls) == 3
    client.close()


def test_client_connection_error_retries_then_fails(mock_respx, settings_env):
    mock_respx.get("").mock(side_effect=httpx.ConnectError("connection failed"))

    client = OpenMeteoClient(
        base_url="https://api.open-meteo.com/v1/forecast",
        timeout_seconds=10.0,
        retry_attempts=3,
        retry_backoff_seconds=0.01,
    )

    with pytest.raises(OpenMeteoConnectionError):
        client.fetch_primary(37.7749, -122.4194, "auto", 2, "best_match")

    assert len(mock_respx.calls) == 3
    client.close()


def test_client_malformed_json(mock_respx, settings_env):
    mock_respx.get("").mock(return_value=httpx.Response(200, text="invalid json {"))

    client = OpenMeteoClient(
        base_url="https://api.open-meteo.com/v1/forecast",
        timeout_seconds=10.0,
        retry_attempts=3,
        retry_backoff_seconds=1.0,
    )

    with pytest.raises(OpenMeteoInvalidResponseError):
        client.fetch_primary(37.7749, -122.4194, "auto", 2, "best_match")

    client.close()


def test_client_missing_hourly_key(mock_respx, settings_env):
    mock_respx.get("").mock(return_value=httpx.Response(200, json={"latitude": 37.7749}))

    client = OpenMeteoClient(
        base_url="https://api.open-meteo.com/v1/forecast",
        timeout_seconds=10.0,
        retry_attempts=3,
        retry_backoff_seconds=1.0,
    )

    with pytest.raises(OpenMeteoInvalidResponseError):
        client.fetch_primary(37.7749, -122.4194, "auto", 2, "best_match")

    client.close()


def test_client_context_manager(mock_respx, settings_env):
    fixture = load_fixture("open_meteo_best_match_success")
    mock_respx.get("").mock(return_value=httpx.Response(200, json=fixture))

    with OpenMeteoClient(
        base_url="https://api.open-meteo.com/v1/forecast",
        timeout_seconds=10.0,
        retry_attempts=3,
        retry_backoff_seconds=1.0,
    ) as client:
        result = client.fetch_primary(37.7749, -122.4194, "auto", 2, "best_match")
        assert result["latitude"] == 37.7749
