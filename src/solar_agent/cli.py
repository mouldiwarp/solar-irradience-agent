import argparse
import sys
from typing import Literal

import uvicorn
from pydantic import ValidationError

from solar_agent import __version__
from solar_agent.api import create_app
from solar_agent.client import OpenMeteoClient
from solar_agent.config import get_settings
from solar_agent.forecast_service import build_forecast
from solar_agent.logging_config import configure_logging
from solar_agent.report import format_report


def main() -> None:
    desc = "Solar Irradiance Agent - fetch forecasts for battery charging"
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        "--mode",
        choices=["cli", "serve"],
        help="Override SOLAR_AGENT_MODE env var (cli or serve)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"solar-agent {__version__}",
    )

    args = parser.parse_args()

    try:
        settings = get_settings()
    except ValidationError as e:
        print("Configuration error:", file=sys.stderr)
        for error in e.errors():
            field = error["loc"][0]
            msg = error["msg"]
            print(f"  {field}: {msg}", file=sys.stderr)
        sys.exit(1)

    configure_logging(settings.log_level)

    mode: Literal["cli", "serve"] = args.mode or settings.mode

    if mode == "cli":
        try:
            with OpenMeteoClient(
                base_url=settings.open_meteo_base_url,
                timeout_seconds=settings.http_timeout_seconds,
                retry_attempts=settings.retry_attempts,
                retry_backoff_seconds=settings.retry_backoff_seconds,
            ) as client:
                result = build_forecast(settings, client)
                report = format_report(result)
                print(report)
        except Exception as e:
            print(f"Error fetching forecast: {e}", file=sys.stderr)
            sys.exit(1)

    elif mode == "serve":
        app = create_app()
        uvicorn.run(
            app,
            host=settings.http_host,
            port=settings.http_port,
            log_level=settings.log_level.lower(),
        )
