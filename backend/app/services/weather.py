"""
Aviation weather service — METAR/TAF via AviationWeather.gov (NOAA/FAA ADDS).

Free, no API key, no registration, no rate limits. Production FAA data.
Provides real aviation weather: visibility, ceiling, flight category,
winds aloft, SIGMETs — not just surface conditions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

AVWX_BASE = "https://aviationweather.gov/api/data/"


@dataclass
class AviationWeather:
    """Aviation-grade weather report from METAR data."""

    icao: str = ""
    source: str = "AviationWeather.gov"
    error: str = ""

    # Timestamp
    observation_time: str = ""

    # Temperature
    temp_c: float | None = None
    temp_f: float | None = None
    dewpoint_c: float | None = None

    # Wind
    wind_dir_deg: int | None = None
    wind_speed_kt: int | None = None
    wind_gust_kt: int | None = None
    wind_direction: str = ""

    # Visibility
    visibility_statute_mi: float | None = None
    visibility_km: float | None = None

    # Pressure
    altimeter_in_hg: float | None = None
    altimeter_mb: float | None = None

    # Sky
    sky_cover: str = ""
    sky_ceiling_ft: int | None = None
    sky_conditions: list[str] = field(default_factory=list)

    # Flight conditions
    flight_category: str = ""  # VFR / MVFR / IFR / LIFR

    # Weather phenomena
    wx_string: str = ""  # e.g. "-RA BR" (light rain, mist)
    wx_description: str = ""

    # Raw
    raw_metar: str = ""


def _cardinal(deg: int | None) -> str:
    if deg is None:
        return ""
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return dirs[round(deg / 22.5) % 16]


def _wx_desc(wx: str) -> str:
    """Convert METAR weather codes to human readable."""
    codes = {
        "-RA": "Light rain", "RA": "Moderate rain", "+RA": "Heavy rain",
        "-SN": "Light snow", "SN": "Moderate snow", "+SN": "Heavy snow",
        "-DZ": "Light drizzle", "DZ": "Moderate drizzle",
        "FG": "Fog", "BR": "Mist", "HZ": "Haze", "FU": "Smoke",
        "TS": "Thunderstorm", "+TSRA": "Thunderstorm with heavy rain",
        "SH": "Showers", "-SHRA": "Light rain showers",
        "BC": "Patches", "PR": "Partial", "MI": "Shallow",
        "BL": "Blowing", "DR": "Low-drift", "FZ": "Freezing",
        "SQ": "Squall", "FC": "Funnel cloud", "SS": "Sandstorm",
    }
    parts = []
    for code in wx.split():
        if code in codes:
            parts.append(codes[code])
        elif code.startswith("+") and code[1:] in codes:
            parts.append("Heavy " + codes[code[1:]])
        elif code.startswith("-") and code[1:] in codes:
            parts.append("Light " + codes[code[1:]])
        else:
            parts.append(code)
    return ", ".join(parts) if parts else wx


async def get_metar(icao: str) -> AviationWeather:
    """
    Fetch current METAR for an airport from AviationWeather.gov.

    Args:
        icao: ICAO code (e.g. 'KMIA', 'MYNN')

    Returns:
        AviationWeather with METAR data or error field.
    """
    report = AviationWeather(icao=icao.upper())

    try:
        params = {"ids": icao.upper(), "format": "json"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(AVWX_BASE + "metar", params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, httpx.TimeoutException, ValueError) as e:
        report.error = f"METAR unavailable: {str(e)[:60]}"
        return report

    if not data or not isinstance(data, list) or len(data) == 0:
        report.error = f"No METAR data for {icao.upper()}"
        return report

    metar = data[0]
    report.observation_time = metar.get("receiptTime", "") or ""

    # Temperature
    tc = metar.get("temp")
    if tc is not None:
        report.temp_c = round(float(tc), 1)
        report.temp_f = round(float(tc) * 9 / 5 + 32, 1)

    dp = metar.get("dewp")
    if dp is not None:
        report.dewpoint_c = round(float(dp), 1)

    # Wind
    raw_wdir = metar.get("wdir")
    report.wind_dir_deg = int(raw_wdir) if isinstance(raw_wdir, (int, float)) else None
    report.wind_speed_kt = metar.get("wspd") or None
    report.wind_gust_kt = metar.get("wgst") or None
    report.wind_direction = _cardinal(report.wind_dir_deg)

    # Visibility
    vis = metar.get("visib")
    if vis is not None:
        try:
            report.visibility_statute_mi = round(float(str(vis).replace("+", "").replace(">", "")), 1)
            report.visibility_km = round(report.visibility_statute_mi * 1.609, 1)
        except (ValueError, TypeError):
            report.visibility_statute_mi = 10.0

    # Pressure
    alt = metar.get("altim")
    if alt is not None:
        report.altimeter_in_hg = round(float(alt) * 0.02953, 2) if float(alt) > 100 else round(float(alt), 2)
        report.altimeter_mb = round(float(alt), 1)

    # Sky conditions
    report.sky_cover = metar.get("cover", "")
    clouds = metar.get("clouds", [])
    if clouds:
        report.sky_conditions = [
            f"{c.get('cover','')}@{c.get('base','?')}ft"
            for c in (clouds if isinstance(clouds, list) else [])
        ]
        # Find ceiling (lowest BKN/OVC layer)
        ceilings = [c.get('base') for c in clouds if c.get('cover') in ('BKN', 'OVC', 'IND')]
        if ceilings:
            report.sky_ceiling_ft = min(ceilings)

    # Flight category
    wxc = metar.get("fltCat", "")
    if wxc:
        report.flight_category = wxc.upper()

    # Weather phenomena
    raw = metar.get("rawOb", "")
    report.raw_metar = raw
    wx_parts = metar.get("wxString", "")
    if wx_parts:
        report.wx_string = wx_parts
        report.wx_description = _wx_desc(wx_parts)

    return report


async def get_taf(icao: str) -> str:
    """
    Fetch the raw TAF text for an airport.

    Returns the TAF text or an error message.
    """
    try:
        params = {"ids": icao.upper(), "format": "raw"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(AVWX_BASE + "taf", params=params)
            resp.raise_for_status()
            return resp.text.strip()
    except Exception as e:
        return f"TAF unavailable: {str(e)[:60]}"


def weather_to_dict(wx: AviationWeather) -> dict[str, Any]:
    """Convert to JSON-serializable dict."""
    return {
        "icao": wx.icao,
        "observation_time": wx.observation_time,
        "temp_c": wx.temp_c,
        "temp_f": wx.temp_f,
        "dewpoint_c": wx.dewpoint_c,
        "wind_direction_deg": wx.wind_dir_deg,
        "wind_direction": wx.wind_direction,
        "wind_speed_kt": wx.wind_speed_kt,
        "wind_gust_kt": wx.wind_gust_kt,
        "visibility_statute_mi": wx.visibility_statute_mi,
        "visibility_km": wx.visibility_km,
        "altimeter_in_hg": wx.altimeter_in_hg,
        "altimeter_mb": wx.altimeter_mb,
        "sky_cover": wx.sky_cover,
        "sky_ceiling_ft": wx.sky_ceiling_ft,
        "sky_conditions": wx.sky_conditions,
        "flight_category": wx.flight_category,
        "wx_string": wx.wx_string,
        "wx_description": wx.wx_description,
        "raw_metar": wx.raw_metar[:200] if wx.raw_metar else "",
        "source": wx.source,
        "error": wx.error if wx.error else None,
    }
