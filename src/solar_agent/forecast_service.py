import logging
from datetime import datetime

from solar_agent.client import OpenMeteoClient
from solar_agent.config import Settings
from solar_agent.models import ForecastMetadata, ForecastResult, HourlyRecord, HourlyUnits

logger = logging.getLogger(__name__)


def build_forecast(settings: Settings, client: OpenMeteoClient) -> ForecastResult:
    primary = client.fetch_primary(
        latitude=settings.latitude,
        longitude=settings.longitude,
        timezone=settings.timezone,
        forecast_days=settings.forecast_days,
        model=settings.weather_model,
    )

    dwd_icon = client.fetch_dwd_icon(
        latitude=settings.latitude,
        longitude=settings.longitude,
        timezone=settings.timezone,
        forecast_days=settings.forecast_days,
    )

    primary_times = primary["hourly"]["time"]
    dwd_icon_times = dwd_icon["hourly"]["time"]

    dwd_icon_by_time: dict[str, dict] = {}
    for i, time_str in enumerate(dwd_icon_times):
        dwd_icon_by_time[time_str] = {
            "shortwave_radiation": dwd_icon["hourly"]["shortwave_radiation"][i],
            "direct_normal_irradiance": dwd_icon["hourly"]["direct_normal_irradiance"][i],
            "diffuse_radiation": dwd_icon["hourly"]["diffuse_radiation"][i],
            "direct_radiation": dwd_icon["hourly"]["direct_radiation"][i],
            "global_tilted_irradiance": dwd_icon["hourly"]["global_tilted_irradiance"][i],
        }

    hourly_records: list[HourlyRecord] = []

    for i, time_str in enumerate(primary_times):
        dt = datetime.fromisoformat(time_str)

        sr = primary["hourly"]["shortwave_radiation"]
        ghi = sr[i] if i < len(sr) else None
        dni_arr = primary["hourly"]["direct_normal_irradiance"]
        dni = dni_arr[i] if i < len(dni_arr) else None
        dr_arr = primary["hourly"]["diffuse_radiation"]
        dhi = dr_arr[i] if i < len(dr_arr) else None
        direct = primary["hourly"]["direct_radiation"]
        dr = direct[i] if i < len(direct) else None
        gti_arr = primary["hourly"]["global_tilted_irradiance"]
        gti = gti_arr[i] if i < len(gti_arr) else None

        dwd_icon_data = dwd_icon_by_time.get(time_str)
        if dwd_icon_data is None:
            logger.warning(f"DWD ICON data missing for timestamp {time_str}")
            dwd_icon_ghi = None
            dwd_icon_dni = None
            dwd_icon_dhi = None
        else:
            dwd_icon_ghi = dwd_icon_data["shortwave_radiation"]
            dwd_icon_dni = dwd_icon_data["direct_normal_irradiance"]
            dwd_icon_dhi = dwd_icon_data["diffuse_radiation"]

        record = HourlyRecord(
            time=dt,
            ghi=ghi,
            dni=dni,
            dhi=dhi,
            direct_radiation=dr,
            global_tilted_irradiance=gti,
            dwd_icon_ghi=dwd_icon_ghi,
            dwd_icon_dni=dwd_icon_dni,
            dwd_icon_dhi=dwd_icon_dhi,
        )
        hourly_records.append(record)

    metadata = ForecastMetadata(
        latitude=primary["latitude"],
        longitude=primary["longitude"],
        elevation=primary["elevation"],
        timezone=primary["timezone"],
        utc_offset_seconds=primary["utc_offset_seconds"],
        generationtime_ms=primary["generationtime_ms"],
        primary_model=settings.weather_model,
        dwd_icon_model="dwd_icon",
    )

    units = HourlyUnits()

    return ForecastResult(
        metadata=metadata,
        units=units,
        hourly=hourly_records,
    )
