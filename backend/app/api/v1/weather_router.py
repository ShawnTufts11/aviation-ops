"""
Weather Integration endpoints — fetch aviation weather for a flight release.

POST /api/v1/flight-releases/{release_id}/fetch-weather
  - Reads the release's origin/dest/alternate airports
  - Calls get_metar / get_taf / get_notams for each
  - Stores structured weather brief + NOTAM refs on the release
  - Returns the brief
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_org_membership
from app.models.flight_release import FlightRelease
from app.models.user import User
from app.services.weather import get_metar, get_taf, get_notams, weather_to_dict

router = APIRouter(prefix="/flight-releases", tags=["flight-releases"])


async def _build_airport_brief(icao: str) -> dict[str, Any]:
    """
    Fetch METAR, TAF, and NOTAMs for a single airport and return a
    structured brief dict.
    """
    metar = await get_metar(icao)
    taf_raw = await get_taf(icao)
    notams = await get_notams(icao)

    brief: dict[str, Any] = {
        "icao": icao.upper(),
        "metar": weather_to_dict(metar),
        "taf": taf_raw if taf_raw and not taf_raw.startswith("TAF unavailable") else None,
        "notams": notams[:20],  # cap per airport
        "notam_count": len(notams),
    }
    return brief


def _compute_go_nogo(briefs: dict[str, dict]) -> str:
    """
    Simple go/nogo heuristic based on flight categories across airports.

    Returns one of: 'caution', 'hold', 'recommended'
    """
    categories = []
    for key in ("departure", "destination", "alternate"):
        mb = briefs.get(key, {})
        metar = mb.get("metar", {})
        cat = (metar.get("flight_category") or "").upper()
        if cat:
            categories.append(cat)

    if "LIFR" in categories or "IFR" in categories:
        return "hold"
    if "MVFR" in categories:
        return "caution"
    return "recommended"


@router.post("/{release_id}/fetch-weather", status_code=200)
async def fetch_weather_for_release(
    release_id: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Fetch live METAR, TAF, and NOTAM data for all airports on a flight
    release (origin, destination, alternate) and store the structured
    weather brief + NOTAM refs on the release record.

    Returns the compiled weather brief.
    """
    # ── Load release ───────────────────────────────────────────────────
    result = await db.execute(
        select(FlightRelease).where(
            FlightRelease.id == release_id,
            FlightRelease.organization_id == current_user.organization_id,
        )
    )
    release = result.scalar_one_or_none()
    if not release:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flight release not found",
        )

    # ── Collect airports ───────────────────────────────────────────────
    airports: list[str] = [release.origin_icao.upper()]
    if release.dest_icao:
        airports.append(release.dest_icao.upper())
    if release.alternate_icao:
        airports.append(release.alternate_icao.upper())

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_airports: list[str] = []
    for ap in airports:
        if ap not in seen:
            seen.add(ap)
            unique_airports.append(ap)

    # ── Fetch weather for each airport ─────────────────────────────────
    briefs: dict[str, dict[str, Any]] = {}
    all_notams: list[dict[str, Any]] = []

    for icao in unique_airports:
        airport_brief = await _build_airport_brief(icao)
        # Route each brief to the correct slot
        if icao == release.origin_icao.upper():
            briefs["departure"] = airport_brief
        elif icao == release.dest_icao.upper():
            briefs["destination"] = airport_brief
        elif release.alternate_icao and icao == release.alternate_icao.upper():
            briefs["alternate"] = airport_brief
        else:
            briefs[icao] = airport_brief  # should not happen

        all_notams.extend(airport_brief.get("notams", []))

    # ── Build structured weather brief ─────────────────────────────────
    go_nogo = _compute_go_nogo(briefs)

    weather_brief: dict[str, Any] = {
        "departure": briefs.get("departure", {}),
        "destination": briefs.get("destination", {}),
        "alternate": briefs.get("alternate", {}),
        "route_weather": [],  # reserved for en-route weather
        "sigmets": [],        # reserved for SIGMETs
        "winds_aloft": None,  # reserved for winds-aloft data
        "go_nogo": go_nogo,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    notam_refs: list[dict[str, Any]] = [
        {
            "id": n.get("id", ""),
            "message": n.get("message", ""),
            "location": n.get("location", ""),
        }
        for n in all_notams
        if n.get("id")
    ]

    # ── Store on the release ───────────────────────────────────────────
    # The FlightRelease model stores weather_brief as a JSON column
    # and notam_refs as a JSON column.
    await db.execute(
        update(FlightRelease)
        .where(FlightRelease.id == release_id)
        .values(
            weather_brief=weather_brief,
            notam_refs=notam_refs,
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()

    return {
        "weather_brief": weather_brief,
        "notam_refs": notam_refs,
        "airports_fetched": unique_airports,
        "total_notams": len(notam_refs),
    }
