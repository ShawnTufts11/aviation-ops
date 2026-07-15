"""
Airport auto-lookup service — populates airport data from public sources.

Primary source: OurAirports open data (https://ourairports.com/data/airports.csv)
— CC-BY 4.0, updated weekly, no API key required.

When a dispatcher enters an unknown ICAO code, this service fetches the
public data, maps it to our Airport model, and returns a preview for
the user to accept (with manual overrides).
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Any

import httpx

# OurAirports data URL — CSV of all known airports worldwide
OURAIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"

# ICAO code types we care about (our Airport model uses ICAO codes)
VALID_TYPES = {"large_airport", "medium_airport", "small_airport", "seaplane_base", "closed"}


@dataclass
class LookupResult:
    """Result of an airport lookup from an external source."""

    found: bool
    source: str = ""
    icao_code: str = ""
    iata_code: str | None = None
    name: str = ""
    city: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    timezone: str = "UTC"
    elevation_ft: int | None = None
    country_code: str = ""
    region: str | None = None
    longest_runway_ft: int | None = None
    has_jet_a: bool = False
    has_avgas: bool = False
    has_customs: bool = False
    operating_hours: str = ""
    data_source: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
    error: str = ""


def _parse_timezone(tz_str: str) -> str:
    """Clean up timezone string from OurAirports (e.g. 'America/Nassau')."""
    if not tz_str or tz_str == "\\N":
        return "UTC"
    return tz_str


def _parse_float(val: str) -> float | None:
    """Parse a numeric string, returning None for nulls."""
    if not val or val == "\\N":
        return None
    try:
        return float(val)
    except ValueError:
        return None


def _parse_int(val: str) -> int | None:
    """Parse an int string, returning None for nulls."""
    if not val or val == "\\N":
        return None
    try:
        return int(float(val))
    except ValueError:
        return None


def _country_code_from_iso(val: str) -> str:
    """Extract 2-letter country code from 'iso_region' field (e.g. 'US-FL' → 'US')."""
    if not val or val == "\\N":
        return ""
    return val.split("-")[0] if "-" in val else val[:2]


async def lookup_by_icao(icao: str) -> LookupResult:
    """
    Look up airport data from the OurAirports open dataset.

    Args:
        icao: 4-character ICAO airport code (e.g. 'MYNN')

    Returns:
        LookupResult with found=True if data was found, plus mapped fields.
    """
    icao = icao.upper().strip()
    if len(icao) != 4:
        return LookupResult(found=False, error="ICAO code must be 4 characters")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(OURAIRPORTS_URL)
            response.raise_for_status()
    except httpx.HTTPError as e:
        return LookupResult(
            found=False,
            error=f"Failed to fetch airport data from OurAirports: {str(e)}",
        )

    # Parse CSV and find matching ICAO
    reader = csv.DictReader(io.StringIO(response.text))

    for row in reader:
        row_icao = (row.get("ident", "") or "").strip().upper()
        row_type = (row.get("type", "") or "").strip()

        if row_icao != icao:
            continue

        # Found — map fields
        result = LookupResult(
            found=True,
            source="ourairports",
            icao_code=icao,
            iata_code=(row.get("iata_code", "") or "").strip().upper() or None,
            name=(row.get("name", "") or "").strip(),
            city=(row.get("municipality", "") or "").strip(),
            latitude=_parse_float(row.get("latitude_deg", "")) or 0.0,
            longitude=_parse_float(row.get("longitude_deg", "")) or 0.0,
            timezone=_parse_timezone(row.get("timezone_kgm", "") or ""),
            elevation_ft=_parse_int(row.get("elevation_ft", "")),
            country_code=_country_code_from_iso(row.get("iso_region", "")),
            region=(row.get("iso_region", "") or "").strip() or None,
            has_customs=row_type in {"large_airport", "medium_airport"},
            data_source="ourairports",
            raw={
                "type": row_type,
                "iso_region": row.get("iso_region", ""),
                "gps_code": row.get("gps_code", ""),
                "local_code": row.get("local_code", ""),
                "home_link": row.get("home_link", ""),
                "wikipedia_link": row.get("wikipedia_link", ""),
                "keywords": row.get("keywords", ""),
                "scheduled_service": row.get("scheduled_service", ""),
            },
        )
        return result

    return LookupResult(
        found=False,
        error=f"ICAO code '{icao}' not found in OurAirports database",
    )


async def lookup_and_populate(icao: str) -> LookupResult:
    """
    Look up an ICAO code and return data mapped to our Airport model fields,
    ready for preview and save.

    This is the primary endpoint for dispatchers adding a new airport on the fly.
    """
    result = await lookup_by_icao(icao)

    if not result.found:
        return result

    # OurAirports doesn't have fuel, FBO, hotel data — flag those as needing manual entry
    result.raw["_needs_manual"] = [
        "fuel_prices",
        "fbo_options",
        "hotel_options",
        "ground_transport",
        "maintenance_capability",
        "runway_info",
        "has_night_ops",
    ]

    return result


def result_to_create_schema(result: LookupResult) -> dict[str, Any]:
    """
    Convert a LookupResult to a dict suitable for creating/updating an Airport.
    The user can review and override before saving.
    """
    if not result.found:
        raise ValueError("Cannot convert: airport not found")

    return {
        "icao_code": result.icao_code,
        "iata_code": result.iata_code,
        "name": result.name,
        "city": result.city,
        "latitude": result.latitude,
        "longitude": result.longitude,
        "timezone": result.timezone,
        "elevation_ft": result.elevation_ft,
        "country_code": result.country_code,
        "region": result.region,
        "has_customs": result.has_customs,
        "operating_hours": result.operating_hours,
        "data_source": result.data_source,
        # These will need manual input:
        "fuel_price_jet_a_usd": None,
        "fbo_options": [],
        "hotel_options": [],
        "ground_transport": {},
        "maintenance_capability": {},
        "runway_info": [],
        "has_night_ops": False,
        "notes": f"Auto-populated from OurAirports. Fuel/FBO/hotel data needs manual entry.",
    }
