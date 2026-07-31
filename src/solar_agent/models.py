from datetime import datetime

from pydantic import BaseModel, Field


class HourlyUnits(BaseModel):
    time: str = "iso8601"
    shortwave_radiation: str = Field(default="W/m²")
    direct_normal_irradiance: str = Field(default="W/m²")
    diffuse_radiation: str = Field(default="W/m²")
    direct_radiation: str = Field(default="W/m²")
    global_tilted_irradiance: str = Field(default="W/m²")


class HourlyRecord(BaseModel):
    time: datetime
    ghi: float | None = Field(
        default=None,
        description="Global Horizontal Irradiance (shortwave_radiation)",
    )
    dni: float | None = Field(
        default=None,
        description="Direct Normal Irradiance",
    )
    dhi: float | None = Field(
        default=None,
        description="Diffuse Horizontal Irradiance",
    )
    direct_radiation: float | None = Field(default=None)
    global_tilted_irradiance: float | None = Field(default=None)
    dwd_icon_ghi: float | None = Field(
        default=None,
        description="DWD ICON GHI forecast",
    )
    dwd_icon_dni: float | None = Field(default=None)
    dwd_icon_dhi: float | None = Field(default=None)


class ForecastMetadata(BaseModel):
    latitude: float
    longitude: float
    elevation: float
    timezone: str
    utc_offset_seconds: int
    generationtime_ms: float
    primary_model: str
    dwd_icon_model: str = "dwd_icon"


class ForecastResult(BaseModel):
    metadata: ForecastMetadata
    units: HourlyUnits
    hourly: list[HourlyRecord]
