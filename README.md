# Solar Irradiance Agent

A Python agent that fetches hourly solar irradiance forecasts from [Open-Meteo](https://open-meteo.com/) for your home location. Designed to provide clear, forward-looking radiation data (GHI, DNI, DHI) to help plan and automate overnight battery charging for optimal financial impact.

**What it does:**
- Fetches 1–16 day hourly solar irradiance forecasts (Global Horizontal Irradiance, Direct Normal Irradiance, Diffuse Horizontal Irradiance)
- Runs as a standalone CLI tool (print-once reports) or a persistent HTTP server (JSON API)
- Includes both primary forecast model (configurable, defaults to Open-Meteo's best match) and DWD ICON NWP model for comparison
- Full regression test suite with no network calls (all tests use mocked fixtures)
- Docker-ready: multi-stage build, non-root user, health checks

**What it does NOT do:**
- Battery charge/discharge scheduling (out of scope — this is a data source only)
- Tariff/pricing logic
- Data persistence or historical tracking
- Real-time irradiance observations (it's forecast-only; see "DWD MTG" note below)

---

## Quickstart

### Prerequisites
- Python 3.11+ (check your version: `python3 --version` or `python3.11 --version`)
- pip

### Local setup (CLI)

```bash
# Clone or enter the repo
cd solar-irradience-agent

# Create and activate a virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Copy and edit environment variables
cp .env.example .env
# Edit .env and fill in your latitude/longitude
```

### Running the CLI

```bash
# Print a forecast report to stdout and exit
solar-agent

# Example output:
# ========================================...=============
# Solar Irradiance Forecast
# Location: 37.77°, -122.42°
# Timezone: America/Los_Angeles
# Primary Model: best_match | DWD ICON Model: dwd_icon
# Generated: 1.2ms
# ========================================...=============
# Time                      GHI (W/m²)  DNI (W/m²)  DHI (W/m²)  DWD-ICON GHI (W/m²)
# ----------------------------------------...----------------------------------------
# 2024-07-31 00:00               -           -           -                  -
# 2024-07-31 06:00             150.0       120.0        30.0              140.0
# 2024-07-31 12:00             720.0       660.0        60.0              710.0
# ...
```

### Running the HTTP service

```bash
# Start the server (listens on 0.0.0.0:8000 by default)
SOLAR_AGENT_MODE=serve solar-agent

# In another terminal, test the API
curl -s http://localhost:8000/health
# {"status":"ok"}

curl -s http://localhost:8000/forecast | python -m json.tool
# {
#   "metadata": {
#     "latitude": 37.7749,
#     "longitude": -122.4194,
#     "timezone": "America/Los_Angeles",
#     "primary_model": "best_match",
#     "dwd_icon_model": "dwd_icon",
#     ...
#   },
#   "hourly": [
#     {
#       "time": "2024-07-31T00:00:00",
#       "ghi": 0.0,
#       "dni": 0.0,
#       "dhi": 0.0,
#       "dwd_icon_ghi": 0.0,
#       ...
#     },
#     ...
#   ],
#   "units": {
#     "shortwave_radiation": "W/m²",
#     "direct_normal_irradiance": "W/m²",
#     ...
#   }
# }

# View auto-generated OpenAPI docs
open http://localhost:8000/docs
```

---

## Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `SOLAR_AGENT_LATITUDE` | **Yes** | — | Home latitude (−90 to 90°) |
| `SOLAR_AGENT_LONGITUDE` | **Yes** | — | Home longitude (−180 to 180°) |
| `SOLAR_AGENT_TIMEZONE` | No | `auto` | Timezone for forecast output (`auto` = infer from lat/long, or a timezone string like `America/Los_Angeles`) |
| `SOLAR_AGENT_FORECAST_DAYS` | No | `2` | Forecast horizon in days (0–16); 2 covers tonight + tomorrow for overnight charging planning |
| `SOLAR_AGENT_WEATHER_MODEL` | No | `best_match` | Weather model for primary GHI/DNI/DHI call (e.g., `best_match`, `gfs_seamless`, `icon_seamless`, etc.) |
| `SOLAR_AGENT_MODE` | No | `cli` | `cli` = run once and print report; `serve` = HTTP server |
| `SOLAR_AGENT_HTTP_HOST` | No | `0.0.0.0` | Uvicorn bind host (serve mode) |
| `SOLAR_AGENT_HTTP_PORT` | No | `8000` | Uvicorn bind port (serve mode) |
| `SOLAR_AGENT_API_KEY` | No | unset | If set, `/forecast` requires `X-API-Key: <value>` header; `/health` always open |
| `SOLAR_AGENT_LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `SOLAR_AGENT_HTTP_TIMEOUT_SECONDS` | No | `10.0` | Timeout for individual Open-Meteo requests (seconds) |
| `SOLAR_AGENT_RETRY_ATTEMPTS` | No | `3` | Max attempts on transient failures (429, 500–504, timeout, connection error) |
| `SOLAR_AGENT_RETRY_BACKOFF_SECONDS` | No | `1.0` | Base backoff for exponential retry (actual: `base * 2^attempt + jitter`) |
| `SOLAR_AGENT_OPEN_METEO_BASE_URL` | No | `https://api.open-meteo.com/v1/forecast` | Overridable for commercial tier or self-hosted Open-Meteo mirror |

See `.env.example` for a complete reference with inline comments.

---

## Run Modes

### CLI mode (default)
```bash
solar-agent
```
Fetches the forecast once, prints a formatted table to stdout, and exits. Useful for one-off reports, cron jobs, or testing.

### Serve mode
```bash
SOLAR_AGENT_MODE=serve solar-agent
```
Starts a FastAPI HTTP server on the configured host/port. Endpoints:
- `GET /health` — liveness check (no upstream call, always unauthenticated)
- `GET /forecast` — returns full forecast as JSON (optional API-key auth)

### Mode override via CLI flag
For local development, you can override the env var with `--mode`:
```bash
SOLAR_AGENT_MODE=serve solar-agent --mode cli   # Runs CLI even though MODE=serve
```

---

## HTTP API Reference

### GET /health
Liveness check (no upstream call).

```bash
curl -s http://localhost:8000/health
# {"status":"ok"}
```

### GET /forecast
Fetch the full solar irradiance forecast.

```bash
curl -s http://localhost:8000/forecast | python -m json.tool
```

**Optional authentication** (if `SOLAR_AGENT_API_KEY` is set):
```bash
curl -s -H "X-API-Key: your-secret-key" http://localhost:8000/forecast | python -m json.tool
```

**Response schema:**
```json
{
  "metadata": {
    "latitude": 37.7749,
    "longitude": -122.4194,
    "elevation": 52.0,
    "timezone": "America/Los_Angeles",
    "utc_offset_seconds": -28800,
    "generationtime_ms": 1.23,
    "primary_model": "best_match",
    "dwd_icon_model": "dwd_icon"
  },
  "hourly": [
    {
      "time": "2024-07-31T00:00:00",
      "ghi": 0.0,
      "dni": 0.0,
      "dhi": 0.0,
      "direct_radiation": 0.0,
      "global_tilted_irradiance": 0.0,
      "dwd_icon_ghi": 0.0,
      "dwd_icon_dni": 0.0,
      "dwd_icon_dhi": 0.0
    },
    ...
  ],
  "units": {
    "time": "iso8601",
    "shortwave_radiation": "W/m²",
    "direct_normal_irradiance": "W/m²",
    "diffuse_radiation": "W/m²",
    "direct_radiation": "W/m²",
    "global_tilted_irradiance": "W/m²"
  }
}
```

**Error responses:**
- `401` (if API key is set but missing or incorrect)
- `502` (upstream API error or invalid response)
- `504` (upstream timeout or connection error)

**Auto-generated API docs:**
Open http://localhost:8000/docs in your browser for an interactive Swagger UI.

---

## Docker

### Build the image
```bash
docker build -t solar-agent .
```

### Run as a container (CLI mode)
```bash
docker run --rm \
  -e SOLAR_AGENT_LATITUDE=37.7749 \
  -e SOLAR_AGENT_LONGITUDE=-122.4194 \
  -e SOLAR_AGENT_MODE=cli \
  solar-agent
```

### Run as a service (HTTP server)
```bash
docker run -d \
  -e SOLAR_AGENT_LATITUDE=37.7749 \
  -e SOLAR_AGENT_LONGITUDE=-122.4194 \
  -e SOLAR_AGENT_MODE=serve \
  -p 8000:8000 \
  --name solar-agent \
  solar-agent
```

### Using docker-compose
```bash
# Edit .env with your location
cp .env.example .env
# (fill in SOLAR_AGENT_LATITUDE and SOLAR_AGENT_LONGITUDE)

# Start the service
docker compose up -d

# Check logs
docker compose logs -f solar-agent

# Test the endpoint
curl http://localhost:8000/health
curl http://localhost:8000/forecast | python -m json.tool

# Stop
docker compose down
```

**Container details:**
- Base image: `python:3.11-slim` (minimal, ~150 MB)
- Runs as non-root user `appuser` (UID 1000)
- Default mode: `serve`
- Health check: `GET /health` every 30 seconds
- Exposed port: `8000`

---

## Data Sources & Attribution

### Open-Meteo
All forecast data comes from [Open-Meteo](https://open-meteo.com/), a free, no-auth-required weather API.

**Attribution:** 
> Data provided by Open-Meteo.com. For details, terms of use, and data sources, see https://open-meteo.com/

**Free tier notes:**
- No API key required for non-commercial use
- Unofficial rate limits (not documented, treat as approximate): ~5,000 calls/hour, 600 calls/min, 10,000/day
- This agent includes automatic retry/backoff for transient failures (timeouts, 429, 5xx) as mitigation
- See `SOLAR_AGENT_RETRY_ATTEMPTS` and `SOLAR_AGENT_RETRY_BACKOFF_SECONDS` to tune retry behavior

---

## Why DWD ICON, not DWD MTG?

### The backstory
The user originally requested a "DWD MTG" column for radiation data. However, **true DWD MTG (Meteosat Third Generation) satellite data on Open-Meteo is observational/nowcast only** — it provides real-time observed radiation from geostationary satellites with ~20 minutes latency, but **cannot forecast future hours**.

Since the whole point of this agent is to forecast overnight charging opportunities (e.g., "charge from 2–5am when clouds are thick"), using a nowcast product for every hour after midnight would result in all-`null` values.

### The solution
Instead, the agent:
1. Fetches the **DWD ICON** (Integrated Forecast System) **NWP model** forecast for radiation variables — this is a genuine forward-looking numerical weather prediction model from the German Weather Service, available via Open-Meteo
2. Labels it clearly as **"DWD ICON"** in all output and code (not "MTG")
3. Compares it side-by-side with the primary forecast model so you can see forecast spread

This gives you two independent forward-looking predictions (primary model + DWD ICON) to evaluate forecast confidence for charging decisions.

---

## Testing

### Run the full test suite
```bash
pytest
```

All tests use **mocked HTTP responses** (`respx` library); no real network calls are made.

### Coverage report
```bash
pytest --cov=solar_agent --cov-report=html
open htmlcov/index.html
```

### Test files
- `tests/test_config.py` — environment variable parsing and defaults
- `tests/test_client.py` — Open-Meteo client, retries, error handling
- `tests/test_forecast_service.py` — response merging, empty/partial arrays, timezone handling
- `tests/test_report.py` — CLI table formatting
- `tests/test_cli.py` — CLI and serve mode dispatch
- `tests/test_api.py` — FastAPI endpoints, authentication, error responses

Test fixtures (mocked JSON responses) are in `tests/fixtures/`.

---

## Development

### Code style & linting
```bash
ruff check src tests
ruff format src tests
```

### Local server + auto-reload
For development, run with `uvicorn` directly:
```bash
pip install uvicorn[standard]
uvicorn solar_agent.api:create_app --reload --host 0.0.0.0 --port 8000
```

---

## Architecture

```
src/solar_agent/
├── config.py              # Pydantic Settings, env var parsing
├── models.py              # Pydantic data models (HourlyRecord, ForecastResult, etc.)
├── client.py              # OpenMeteoClient: HTTP calls, retry logic, exceptions
├── forecast_service.py    # Orchestration: fetch both endpoints, merge by timestamp
├── report.py              # CLI table formatting (pure function)
├── api.py                 # FastAPI app factory
├── cli.py                 # CLI entrypoint (argparse, mode dispatch)
├── logging_config.py      # Basic logging setup
└── __main__.py            # Enables `python -m solar_agent`
```

---

## License

MIT (see LICENSE file, if present).

---

## Support & Issues

For issues, suggestions, or contributions, please refer to the project repository.
