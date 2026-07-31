# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Commands

```bash
# Setup
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env

# Test & Lint
pytest                              # Run full suite (42 tests, 96% coverage)
pytest tests/test_client.py -v      # Single test file
pytest tests/test_client.py::test_fetch_primary_success -v  # Single test
pytest --cov=solar_agent --cov-report=html  # Coverage report (htmlcov/index.html)
ruff check src tests                # Lint check
ruff format src tests               # Auto-format

# Run
solar-agent                         # CLI mode (one-shot report)
SOLAR_AGENT_MODE=serve solar-agent  # HTTP server mode (port 8000)

# Docker
docker compose build
docker compose up -d
curl http://localhost:8000/forecast
docker compose down
```

## Architecture Overview

### High-Level Design

This is a dual-mode weather data agent:
- **CLI mode**: Fetches forecast once, prints a formatted table, exits
- **HTTP mode**: Runs a persistent FastAPI server serving JSON forecasts

The core pattern: **config → client → orchestration → output**

```
Config (env vars)
    ↓
OpenMeteoClient (HTTP + retry logic)
    ↓
build_forecast() (orchestration: fetch 2 endpoints, merge by timestamp)
    ↓
report.format_report() (CLI table) or api.create_app() (JSON)
```

### Two API Calls (Merged Client-Side)

The agent makes **two independent Open-Meteo API calls**, then merges by timestamp:

1. **Primary call** — user-configurable model (default: `best_match`)
   - Variables: GHI (shortwave_radiation), DNI, DHI, direct_radiation, global_tilted_irradiance
   - Used when user needs a single best forecast

2. **DWD ICON call** — hardcoded to `models=dwd_icon` for comparison
   - Same variables as primary, but from DWD's Integrated Forecast System
   - Purpose: Give user two independent forecasts to assess confidence

**Why two separate calls, not one combined `models=` parameter?**
- Open-Meteo's variable-name suffixing for multi-model requests is undocumented
- Separate calls keep test fixtures independent and composable
- Allows one call to fail without blocking the other (future enhancement)

**Why DWD ICON, not DWD MTG?**
- True DWD MTG satellite data is nowcast/observation-only (~20 min latency), cannot forecast future hours
- DWD ICON is a real NWP model with genuine forward-looking predictions
- See README.md "Why DWD ICON, not DWD MTG" for full explanation

### Data Flow

1. **Config** (`config.py`) — Pydantic `Settings` singleton reads env vars, validates ranges
2. **Client** (`client.py`) — `OpenMeteoClient` wraps httpx with retry logic (exponential backoff + jitter on 429/5xx/timeout)
3. **Orchestration** (`forecast_service.py`) — `build_forecast()` calls both endpoints, aligns responses by `hourly.time` string, fills missing data with `None`, logs warnings
4. **Output**:
   - CLI: `report.format_report()` → fixed-width table (pure function, easy to test)
   - HTTP: Pydantic models auto-serialize to JSON via FastAPI

### Key Implementation Details

**Settings singleton:**
```python
@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```
Avoids re-parsing env vars on every request. Tests call `get_settings.cache_clear()` between test cases.

**Pydantic models as dual schema:**
- `HourlyRecord`, `ForecastResult`, etc. validate data AND serve as FastAPI response models
- No separate DTO/schema layer needed; one source of truth for shape + validation

**HTTP client context manager:**
```python
with OpenMeteoClient(...) as client:
    result = build_forecast(settings, client)
```
Ensures `httpx.Client` is closed (connection pooling cleanup) after use.

**Exception hierarchy:**
- `OpenMeteoError` (base)
- `OpenMeteoAPIError(status_code, reason)` — API returned 400 (never retried)
- `OpenMeteoTimeoutError` — timeout (retried)
- `OpenMeteoConnectionError` — connection failed (retried)
- `OpenMeteoInvalidResponseError` — malformed JSON / missing keys

**Retry strategy:**
- Retries on: `{429, 500, 502, 503, 504}` + timeout + connection errors
- Does NOT retry 400 (bad request — retrying won't help, wastes calls)
- Exponential backoff: `base * 2^attempt + random.uniform(0, 0.1)`
- Configurable: `SOLAR_AGENT_RETRY_ATTEMPTS` (default 3), `SOLAR_AGENT_RETRY_BACKOFF_SECONDS` (default 1.0)

### Testing Philosophy

- **Zero network calls**: All HTTP responses are mocked via `respx`
- **Fixture-driven**: Sample JSON files in `tests/fixtures/` represent real Open-Meteo response shapes
- **Comprehensive coverage**: 42 tests across config, client, service, report, CLI, API
- **Edge cases tested**: empty hourly arrays, partial data, mismatched timestamps, malformed JSON

No external API calls ever happen during tests; CI/CD can run offline.

### Environment Variables Reference

See `.env.example` for the complete list. Key ones for common tasks:

- `SOLAR_AGENT_LATITUDE`, `SOLAR_AGENT_LONGITUDE` — **required**, no defaults
- `SOLAR_AGENT_MODE` — `cli` (default) or `serve`
- `SOLAR_AGENT_WEATHER_MODEL` — primary model name (default `best_match`); DWD ICON is always hardcoded
- `SOLAR_AGENT_FORECAST_DAYS` — 0-16 (default 2, covers tonight + tomorrow)
- `SOLAR_AGENT_API_KEY` — optional; if set, `/forecast` requires `X-API-Key` header
- `SOLAR_AGENT_HTTP_HOST`, `SOLAR_AGENT_HTTP_PORT` — serve mode binding
- `SOLAR_AGENT_RETRY_ATTEMPTS`, `SOLAR_AGENT_RETRY_BACKOFF_SECONDS` — resilience tuning

## Common Development Tasks

### Adding a new endpoint or CLI option
1. Define the handler in `api.py` (FastAPI) or `cli.py` (argparse)
2. If it needs config, add the field to `Settings` in `config.py`
3. Write tests in the corresponding `test_*.py` file
4. Update README.md if it's user-facing

### Changing the Open-Meteo request (e.g., adding a new variable)
1. Update the `hourly` parameter string in `client.py` (`fetch_primary`, `fetch_dwd_icon`)
2. Add the new field to test fixtures (`tests/fixtures/*.json`)
3. Add it to `HourlyRecord` in `models.py`
4. Update the merge logic in `forecast_service.py` if needed
5. Tests will catch if the fixture shape doesn't match expectations

### Running a single test during development
```bash
pytest tests/test_client.py::test_fetch_primary_success -v
pytest tests/test_api.py::test_forecast_endpoint_success -v
```

### Debugging a test
```bash
pytest tests/test_client.py::test_client_429_retries_then_fails -vv --tb=short
```
Add `-vv` for verbose output and `--tb=short` for readable tracebacks.

### Checking test coverage
```bash
pytest --cov=solar_agent --cov-report=html
open htmlcov/index.html
```

### Linting before commit
```bash
ruff check src tests     # Find issues
ruff format src tests    # Auto-fix style
pytest                   # Ensure tests still pass
```

## Design Constraints & Patterns

1. **No external dependencies for retry/formatting** — Hand-rolled retry (exponential backoff, ~25 lines) and report table (pure function) keep code clear and dependency count low. Not worth adding `tenacity` or `rich`.

2. **Minimal settings/configuration** — Use env vars only; no config files or CLI args for connection details (keeps deployment declarative).

3. **Pydantic for all boundaries** — Input validation (Settings from env), data shape validation (API response parsing), output schema (FastAPI responses). Single point of truth.

4. **Context managers for resources** — `OpenMeteoClient` is a context manager; HTTP client is closed automatically. Prevents connection leaks.

5. **Specific exceptions, not generic** — `OpenMeteoAPIError` vs `OpenMeteoTimeoutError` vs `OpenMeteoConnectionError` make it clear to the caller which failures are retryable vs. permanent.

6. **Pure functions where possible** — `format_report()`, `build_forecast()` take inputs and return outputs; easy to test, reason about, and reuse.

## Troubleshooting

**Tests fail with "ModuleNotFoundError: No module named 'solar_agent'"**
- Run `pip install -e .` from the repo root (editable install; needed for tests to find the package)

**"SOLAR_AGENT_LATITUDE" validation error when running CLI**
- Set required env vars before running: `export SOLAR_AGENT_LATITUDE=37.7749 SOLAR_AGENT_LONGITUDE=-122.4194`
- Or copy `.env.example` to `.env` and fill in your values

**Tests try to make real HTTP calls / respx mocking isn't working**
- Ensure `respx` is installed: `pip install respx`
- Check that test functions have the `mock_respx` fixture: `def test_foo(mock_respx):`
- `respx` intercepts `httpx` calls in the `https://api.open-meteo.com/v1/forecast` base URL

**Docker container exits immediately**
- Check logs: `docker compose logs solar-agent`
- Ensure `.env` has `SOLAR_AGENT_LATITUDE` and `SOLAR_AGENT_LONGITUDE` set
- By default, docker-compose.yml runs serve mode; set `SOLAR_AGENT_MODE=cli` to run once

## Related Documentation

- **README.md** — User guide, quickstart, env var reference, DWD MTG explanation, API reference
- **.env.example** — All env var options with inline comments
- **pyproject.toml** — Dependencies, pytest/ruff config, package metadata
