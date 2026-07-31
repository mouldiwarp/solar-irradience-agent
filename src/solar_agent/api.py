from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse

from solar_agent.client import (
    OpenMeteoAPIError,
    OpenMeteoClient,
    OpenMeteoConnectionError,
    OpenMeteoInvalidResponseError,
    OpenMeteoTimeoutError,
)
from solar_agent.config import Settings, get_settings
from solar_agent.forecast_service import build_forecast
from solar_agent.models import ForecastResult


def verify_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    from solar_agent.config import get_settings

    settings = get_settings()
    if settings.api_key is None:
        return

    if x_api_key is None or x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Solar Irradiance Agent",
        description="Fetch solar irradiance forecasts from Open-Meteo",
        version="0.1.0",
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/forecast", response_model=ForecastResult)
    def forecast(
        settings: Annotated[Settings, Depends(get_settings)] = None,
        _: None = Depends(verify_api_key),
    ) -> ForecastResult:
        try:
            with OpenMeteoClient(
                base_url=settings.open_meteo_base_url,
                timeout_seconds=settings.http_timeout_seconds,
                retry_attempts=settings.retry_attempts,
                retry_backoff_seconds=settings.retry_backoff_seconds,
            ) as client:
                return build_forecast(settings, client)

        except (OpenMeteoAPIError, OpenMeteoInvalidResponseError) as e:
            return JSONResponse(
                status_code=502,
                content={"error": True, "detail": str(e)},
            )
        except (OpenMeteoTimeoutError, OpenMeteoConnectionError) as e:
            return JSONResponse(
                status_code=504,
                content={"error": True, "detail": str(e)},
            )

    return app
