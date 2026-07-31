import json
from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from solar_agent.api import create_app


def load_fixture(name: str) -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / f"{name}.json"
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
def mock_respx():
    with respx.mock(base_url="https://api.open-meteo.com/v1/forecast") as mock:
        yield mock


@pytest.fixture
def client(settings_env):
    from solar_agent.config import get_settings

    get_settings.cache_clear()
    app = create_app()
    return TestClient(app)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_forecast_endpoint_success(mock_respx, client):
    primary_fixture = load_fixture("open_meteo_best_match_success")
    dwd_fixture = load_fixture("open_meteo_dwd_icon_success")

    call_count = 0

    def handle_request(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(200, json=primary_fixture)
        else:
            return httpx.Response(200, json=dwd_fixture)

    mock_respx.get("").mock(side_effect=handle_request)

    response = client.get("/forecast")
    assert response.status_code == 200

    data = response.json()
    assert "metadata" in data
    assert "hourly" in data
    assert "units" in data
    assert data["metadata"]["latitude"] == 37.7749
    assert len(data["hourly"]) == 48


def test_forecast_endpoint_api_error(mock_respx, client):
    error_fixture = load_fixture("open_meteo_error_400")
    mock_respx.get("").mock(return_value=httpx.Response(400, json=error_fixture))

    response = client.get("/forecast")
    assert response.status_code == 502
    assert response.json()["error"] is True


def test_forecast_endpoint_server_error_retry(mock_respx, client):
    error_fixture = load_fixture("open_meteo_error_400")
    mock_respx.get("").mock(return_value=httpx.Response(503, json=error_fixture))

    response = client.get("/forecast")
    assert response.status_code == 502


def test_forecast_endpoint_timeout(mock_respx, client):
    mock_respx.get("").mock(side_effect=httpx.TimeoutException("timeout"))

    response = client.get("/forecast")
    assert response.status_code == 504


def test_forecast_endpoint_connection_error(mock_respx, client):
    mock_respx.get("").mock(side_effect=httpx.ConnectError("connection failed"))

    response = client.get("/forecast")
    assert response.status_code == 504


def test_api_key_not_required_by_default(mock_respx, client, settings_env):
    primary_fixture = load_fixture("open_meteo_best_match_success")
    dwd_fixture = load_fixture("open_meteo_dwd_icon_success")

    call_count = 0

    def handle_request(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(200, json=primary_fixture)
        else:
            return httpx.Response(200, json=dwd_fixture)

    mock_respx.get("").mock(side_effect=handle_request)

    from solar_agent.config import get_settings

    get_settings.cache_clear()

    response = client.get("/forecast")
    assert response.status_code == 200


def test_api_key_required_when_set(mock_respx, settings_env, monkeypatch):
    monkeypatch.setenv("SOLAR_AGENT_API_KEY", "secret123")

    from solar_agent.config import get_settings

    get_settings.cache_clear()

    app = create_app()
    client = TestClient(app)

    response = client.get("/forecast")
    assert response.status_code == 401


def test_api_key_accepted_with_correct_header(mock_respx, settings_env, monkeypatch):
    monkeypatch.setenv("SOLAR_AGENT_API_KEY", "secret123")

    from solar_agent.config import get_settings

    get_settings.cache_clear()

    app = create_app()
    client = TestClient(app)

    primary_fixture = load_fixture("open_meteo_best_match_success")
    dwd_fixture = load_fixture("open_meteo_dwd_icon_success")

    call_count = 0

    def handle_request(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(200, json=primary_fixture)
        else:
            return httpx.Response(200, json=dwd_fixture)

    mock_respx.get("").mock(side_effect=handle_request)

    response = client.get("/forecast", headers={"X-API-Key": "secret123"})
    assert response.status_code == 200


def test_api_key_rejected_with_wrong_header(mock_respx, settings_env, monkeypatch):
    monkeypatch.setenv("SOLAR_AGENT_API_KEY", "secret123")

    from solar_agent.config import get_settings

    get_settings.cache_clear()

    app = create_app()
    client = TestClient(app)

    response = client.get("/forecast", headers={"X-API-Key": "wrongkey"})
    assert response.status_code == 401


def test_forecast_response_schema(mock_respx, client):
    primary_fixture = load_fixture("open_meteo_best_match_success")
    dwd_fixture = load_fixture("open_meteo_dwd_icon_success")

    call_count = 0

    def handle_request(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(200, json=primary_fixture)
        else:
            return httpx.Response(200, json=dwd_fixture)

    mock_respx.get("").mock(side_effect=handle_request)

    response = client.get("/forecast")
    data = response.json()

    assert "metadata" in data
    assert "hourly" in data
    assert "units" in data

    metadata = data["metadata"]
    assert "latitude" in metadata
    assert "longitude" in metadata
    assert "elevation" in metadata
    assert "timezone" in metadata
    assert "utc_offset_seconds" in metadata
    assert "generationtime_ms" in metadata
    assert "primary_model" in metadata
    assert "dwd_icon_model" in metadata

    units = data["units"]
    assert "time" in units
    assert "shortwave_radiation" in units

    assert len(data["hourly"]) > 0
    first_hour = data["hourly"][0]
    assert "time" in first_hour
    assert "ghi" in first_hour
    assert "dni" in first_hour
    assert "dhi" in first_hour
    assert "dwd_icon_ghi" in first_hour
