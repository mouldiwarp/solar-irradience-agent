from solar_agent.models import ForecastResult


def _calculate_charging_weight(ghi: float | None) -> str:
    """
    Calculate charging opportunity weight (0-100).
    Higher value = darker/cloudier = better for overnight battery charging.
    Formula: 100 - normalized(GHI), capped at max realistic GHI ~1000 W/m².
    """
    if ghi is None or ghi < 0:
        return "-"
    max_ghi = 1000.0
    weight = 100 - (min(ghi, max_ghi) / max_ghi * 100)
    return f"{weight:.0f}"


def format_report(result: ForecastResult) -> str:
    lines: list[str] = []

    lines.append("=" * 150)
    lines.append("Solar Irradiance Forecast")
    lines.append(f"Location: {result.metadata.latitude:.2f}°, {result.metadata.longitude:.2f}°")
    lines.append(f"Timezone: {result.metadata.timezone}")
    model_line = (
        f"Primary Model: {result.metadata.primary_model} | "
        f"DWD ICON Model: {result.metadata.dwd_icon_model}"
    )
    lines.append(model_line)
    lines.append(f"Generated: {result.metadata.generationtime_ms:.1f}ms")
    lines.append("=" * 150)

    header = (
        f"{'Time':<25} {'GHI (W/m²)':<14} {'DNI (W/m²)':<14} {'DHI (W/m²)':<14} "
        f"{'DWD GHI (W/m²)':<15} {'Charge Wt':<11}"
    )
    lines.append(header)
    lines.append("-" * 150)

    for record in result.hourly:
        time_str = record.time.strftime("%Y-%m-%d %H:%M")
        ghi_str = f"{record.ghi:.1f}" if record.ghi is not None else "-"
        dni_str = f"{record.dni:.1f}" if record.dni is not None else "-"
        dhi_str = f"{record.dhi:.1f}" if record.dhi is not None else "-"
        dwd_ghi_str = f"{record.dwd_icon_ghi:.1f}" if record.dwd_icon_ghi is not None else "-"
        charge_wt = _calculate_charging_weight(record.ghi)

        row = (
            f"{time_str:<25} {ghi_str:>13} {dni_str:>13} {dhi_str:>13} "
            f"{dwd_ghi_str:>14} {charge_wt:>10}"
        )
        lines.append(row)

    lines.append("=" * 150)
    lines.append("\nCharging Weight (0-100): Weight for battery charging decisions (higher = darker = better for charging)")
    lines.append("  0 = Peak sun (panels at max production) | 100 = Full night/heavy clouds (ideal charging window)")

    return "\n".join(lines)
