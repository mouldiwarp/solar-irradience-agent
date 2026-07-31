import json
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import respx

from solar_agent.cli import main


def load_fixture(name: str) -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / f"{name}.json"
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
def mock_respx():
    with respx.mock(base_url="https://api.open-meteo.com/v1/forecast") as mock:
        yield mock


def test_cli_mode_success(mock_respx, settings_env, capsys, monkeypatch):
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

    monkeypatch.setenv("SOLAR_AGENT_MODE", "cli")
    monkeypatch.setattr("sys.argv", ["solar-agent"])

    try:
        main()
    except SystemExit:
        pass

    captured = capsys.readouterr()
    assert "Solar Irradiance Forecast" in captured.out
    assert "GHI" in captured.out
    assert "DNI" in captured.out
    assert "DHI" in captured.out


def test_cli_mode_missing_latitude(monkeypatch, capsys):
    monkeypatch.delenv("SOLAR_AGENT_LATITUDE", raising=False)
    monkeypatch.delenv("SOLAR_AGENT_LONGITUDE", raising=False)
    monkeypatch.setattr("sys.argv", ["solar-agent"])

    from solar_agent.config import get_settings

    get_settings.cache_clear()

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Configuration error" in captured.err


def test_cli_mode_with_mode_override(mock_respx, settings_env, capsys, monkeypatch):
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

    monkeypatch.setenv("SOLAR_AGENT_MODE", "serve")
    monkeypatch.setattr("sys.argv", ["solar-agent", "--mode", "cli"])

    try:
        main()
    except SystemExit:
        pass

    captured = capsys.readouterr()
    assert "Solar Irradiance Forecast" in captured.out


@patch("uvicorn.run")
def test_serve_mode_starts_server(mock_uvicorn_run, settings_env, monkeypatch):
    from solar_agent.config import get_settings

    get_settings.cache_clear()

    monkeypatch.setenv("SOLAR_AGENT_MODE", "serve")
    monkeypatch.setattr("sys.argv", ["solar-agent"])

    main()

    mock_uvicorn_run.assert_called_once()
    call_args = mock_uvicorn_run.call_args
    assert call_args[1]["host"] == "127.0.0.1"
    assert call_args[1]["port"] == 8000


def test_cli_version_flag(capsys, monkeypatch):
    from solar_agent.config import get_settings

    get_settings.cache_clear()

    monkeypatch.setattr("sys.argv", ["solar-agent", "--version"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "0.1.0" in captured.out
