from datetime import datetime

from solar_agent.models import ForecastMetadata, ForecastResult, HourlyRecord, HourlyUnits
from solar_agent.report import format_report


def test_format_report_with_data():
    metadata = ForecastMetadata(
        latitude=37.7749,
        longitude=-122.4194,
        elevation=52.0,
        timezone="America/Los_Angeles",
        utc_offset_seconds=-28800,
        generationtime_ms=1.23,
        primary_model="best_match",
        dwd_icon_model="dwd_icon",
    )

    units = HourlyUnits()

    hourly = [
        HourlyRecord(
            time=datetime(2024, 7, 31, 0, 0),
            ghi=0.0,
            dni=0.0,
            dhi=0.0,
            direct_radiation=0.0,
            global_tilted_irradiance=0.0,
            dwd_icon_ghi=0.0,
        ),
        HourlyRecord(
            time=datetime(2024, 7, 31, 6, 0),
            ghi=150.0,
            dni=120.0,
            dhi=30.0,
            direct_radiation=100.0,
            global_tilted_irradiance=180.0,
            dwd_icon_ghi=140.0,
        ),
        HourlyRecord(
            time=datetime(2024, 7, 31, 12, 0),
            ghi=720.0,
            dni=660.0,
            dhi=60.0,
            direct_radiation=520.0,
            global_tilted_irradiance=840.0,
            dwd_icon_ghi=710.0,
        ),
    ]

    result = ForecastResult(metadata=metadata, units=units, hourly=hourly)
    report = format_report(result)

    assert "Solar Irradiance Forecast" in report
    assert "37.77°, -122.42°" in report
    assert "America/Los_Angeles" in report
    assert "best_match" in report
    assert "dwd_icon" in report
    assert "Time" in report
    assert "GHI (W/m²)" in report
    assert "DNI (W/m²)" in report
    assert "DHI (W/m²)" in report
    assert "DWD GHI (W/m²)" in report
    assert "Charge Wt" in report
    assert "2024-07-31 00:00" in report
    assert "2024-07-31 06:00" in report
    assert "2024-07-31 12:00" in report
    assert "150.0" in report
    assert "720.0" in report


def test_format_report_none_values_render_as_dash():
    metadata = ForecastMetadata(
        latitude=37.7749,
        longitude=-122.4194,
        elevation=52.0,
        timezone="America/Los_Angeles",
        utc_offset_seconds=-28800,
        generationtime_ms=1.23,
        primary_model="best_match",
        dwd_icon_model="dwd_icon",
    )

    units = HourlyUnits()

    hourly = [
        HourlyRecord(
            time=datetime(2024, 7, 31, 0, 0),
            ghi=None,
            dni=None,
            dhi=None,
            dwd_icon_ghi=None,
        ),
    ]

    result = ForecastResult(metadata=metadata, units=units, hourly=hourly)
    report = format_report(result)

    assert "-" in report


def test_format_report_empty_hourly():
    metadata = ForecastMetadata(
        latitude=37.7749,
        longitude=-122.4194,
        elevation=52.0,
        timezone="America/Los_Angeles",
        utc_offset_seconds=-28800,
        generationtime_ms=1.23,
        primary_model="best_match",
        dwd_icon_model="dwd_icon",
    )

    units = HourlyUnits()
    hourly: list[HourlyRecord] = []

    result = ForecastResult(metadata=metadata, units=units, hourly=hourly)
    report = format_report(result)

    assert "Solar Irradiance Forecast" in report
    assert "Time" in report
