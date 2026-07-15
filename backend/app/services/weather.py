"""
Weather service — free aviation weather via Open-Meteo API.

No API key required. Provides current conditions and basic forecast
for any airport by lat/lon coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather codes → human-readable
WMO_CODES: dict[int, str] = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    56: "Light freezing drizzle", 57: "Dense freezing drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}


@dataclass
class WeatherReport:
    """Current weather conditions at an airport."""

    icao: str = ""
    temperature_c: float | None = None
    temperature_f: float | None = None
    weather_code: int | None = None
    weather_desc: str = "Unknown"
    wind_speed_kts: float | None = None
    wind_direction_deg: int | None = None
    wind_direction_str: str = ""
    visibility_km: float | None = None
    visibility_statute_mi: float | None = None
    source: str = "Open-Meteo"
    error: str = ""


def _deg_to_cardinal(deg: int | None) -> str:
    """Convert wind direction degrees to cardinal string."""
    if deg is None:
        return ""
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return dirs[round(deg / 22.5) % 16]


async def get_weather(lat: float, lon: float, icao: str = "") -> WeatherReport:
    """
    Fetch current weather conditions from Open-Meteo.

    Args:
        lat: Decimal latitude
        lon: Decimal longitude
        icao: ICAO code (for logging/display)

    Returns:
        WeatherReport with current conditions, or error field.
    """
    report = WeatherReport(icao=icao)

    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,weather_code,wind_speed_10m,wind_direction_10m",
            "wind_speed_unit": "kn",
            "temperature_unit": "celsius",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(OPENMETEO_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, httpx.TimeoutException, ValueError) as e:
        report.error = f"Weather unavailable: {str(e)[:60]}"
        return report

    current = data.get("current", {})
    if not current:
        report.error = "No current weather data returned"
        return report

    temp_c = current.get("temperature_2m")
    if temp_c is not None:
        report.temperature_c = round(float(temp_c), 1)
        report.temperature_f = round(float(temp_c) * 9 / 5 + 32, 1)

    code = current.get("weather_code")
    if code is not None:
        report.weather_code = int(code)
        report.weather_desc = WMO_CODES.get(int(code), f"Code {code}")

    wind_kts = current.get("wind_speed_10m")
    if wind_kts is not None:
        report.wind_speed_kts = round(float(wind_kts), 1)

    wind_dir = current.get("wind_direction_10m")
    if wind_dir is not None:
        report.wind_direction_deg = int(wind_dir)
        report.wind_direction_str = _deg_to_cardinal(int(wind_dir))

    return report


def weather_to_dict(report: WeatherReport) -> dict[str, Any]:
    """Convert to JSON-serializable dict."""
    return {
        "icao": report.icao,
        "temperature_c": report.temperature_c,
        "temperature_f": report.temperature_f,
        "conditions": report.weather_desc,
        "wind_speed_kts": report.wind_speed_kts,
        "wind_direction": report.wind_direction_str if report.wind_direction_str else report.wind_direction_deg,
        "source": report.source,
        "error": report.error if report.error else None,
    }
