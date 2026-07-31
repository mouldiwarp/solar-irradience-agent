from solar_agent.models import ForecastResult


def format_report(result: ForecastResult) -> str:
    lines: list[str] = []

    lines.append("=" * 120)
    lines.append("Solar Irradiance Forecast")
    lines.append(f"Location: {result.metadata.latitude:.2f}°, {result.metadata.longitude:.2f}°")
    lines.append(f"Timezone: {result.metadata.timezone}")
    model_line = (
        f"Primary Model: {result.metadata.primary_model} | "
        f"DWD ICON Model: {result.metadata.dwd_icon_model}"
    )
    lines.append(model_line)
    lines.append(f"Generated: {result.metadata.generationtime_ms:.1f}ms")
    lines.append("=" * 120)

    header = (
        f"{'Time':<25} {'GHI (W/m²)':<15} {'DNI (W/m²)':<15} "
        f"{'DHI (W/m²)':<15} {'DWD-ICON GHI (W/m²)':<20}"
    )
    lines.append(header)
    lines.append("-" * 120)

    for record in result.hourly:
        time_str = record.time.strftime("%Y-%m-%d %H:%M")
        ghi_str = f"{record.ghi:.1f}" if record.ghi is not None else "-"
        dni_str = f"{record.dni:.1f}" if record.dni is not None else "-"
        dhi_str = f"{record.dhi:.1f}" if record.dhi is not None else "-"
        dwd_ghi_str = f"{record.dwd_icon_ghi:.1f}" if record.dwd_icon_ghi is not None else "-"

        row = f"{time_str:<25} {ghi_str:>14} {dni_str:>14} {dhi_str:>14} {dwd_ghi_str:>19}"
        lines.append(row)

    lines.append("=" * 120)

    return "\n".join(lines)
