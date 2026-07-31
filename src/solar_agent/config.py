import functools
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SOLAR_AGENT_",
        case_sensitive=False,
    )

    latitude: float = Field(
        description="Home latitude (-90 to 90)",
    )
    longitude: float = Field(
        description="Home longitude (-180 to 180)",
    )
    timezone: str = Field(
        default="auto",
        description="Timezone passed to Open-Meteo (auto = infer from lat/long)",
    )
    forecast_days: int = Field(
        default=2,
        ge=0,
        le=16,
        description="Forecast horizon in days",
    )
    weather_model: str = Field(
        default="best_match",
        description="Weather model for primary GHI/DNI/DHI call",
    )
    mode: Literal["cli", "serve"] = Field(
        default="cli",
        description="Run mode: cli (print once) or serve (HTTP server)",
    )
    http_host: str = Field(
        default="0.0.0.0",
        description="Uvicorn bind host",
    )
    http_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Uvicorn bind port",
    )
    api_key: str | None = Field(
        default=None,
        description="Optional API key for /forecast endpoint (X-API-Key header)",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )
    http_timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        description="Timeout for Open-Meteo requests",
    )
    retry_attempts: int = Field(
        default=3,
        ge=1,
        description="Max retry attempts for transient failures",
    )
    retry_backoff_seconds: float = Field(
        default=1.0,
        gt=0,
        description="Base backoff for exponential retry",
    )
    open_meteo_base_url: str = Field(
        default="https://api.open-meteo.com/v1/forecast",
        description="Open-Meteo API base URL",
    )

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if not -90 <= v <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if not -180 <= v <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return v


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
