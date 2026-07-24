"""Live flight tracking via ADSB.lol API — Phase 1."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_org_membership
from app.models.aircraft import Aircraft
from app.models.airport import Airport
from app.models.user import User

router = APIRouter(prefix="/tracking", tags=["tracking"])

ADSB_API = "https://api.adsb.lol/v2/callsign"


@router.get("/live")
async def live_tracking(
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get live positions for the user's aircraft fleet.

    Queries ADSB.lol for each tail number. Gracefully degrades:
    - If ADSB.lol is unreachable/errors, returns ground positions with a
      ``degraded`` flag and ``"position estimated"`` note.
    - Individual aircraft not broadcasting ADS-B get ground positions from
      their home base (Aircraft.base → Airport.coordinates).
    - When all aircraft have no ADS-B data the response carries an explicit
      degraded message.
    """
    result = await db.execute(
        select(Aircraft.tail_number).where(
            Aircraft.organization_id == current_user.organization_id,
        )
    )
    tails = [row[0] for row in result.all()]

    if not tails:
        return {
            "aircraft": [],
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "degraded": False,
        }

    now_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # ── Query ADSB.lol with per-request try/except ──────────────────────
    adsb_live = {}  # tail -> position dict
    adsb_errors = 0  # count of failed / empty ADS-B responses

    async with httpx.AsyncClient(timeout=10) as client:
        for tail in tails:
            try:
                resp = await client.get(f"{ADSB_API}/{tail}")
                if resp.status_code != 200:
                    adsb_errors += 1
                    continue
                data = resp.json()
                ac_list = data.get("ac", [])
                if not ac_list:
                    adsb_errors += 1
                    continue
                ac = ac_list[0]
                adsb_live[tail] = {
                    "tail": tail,
                    "lat": ac.get("lat"),
                    "lon": ac.get("lon"),
                    "altitude_ft": ac.get("alt_geom") or ac.get("alt_baro"),
                    "speed_kts": ac.get("gs"),
                    "heading": ac.get("track"),
                    "callsign": (ac.get("flight") or "").strip(),
                    "seen_seconds": ac.get("seen"),
                    "rssi": ac.get("rssi"),
                    "status": "airborne",
                    "last_updated": now_ts,
                }
            except Exception:
                adsb_errors += 1
                continue

    degraded = adsb_errors > 0

    # ── Fetch aircraft + airport data for ground fallback ───────────────
    all_ac = (await db.execute(
        select(Aircraft).where(
            Aircraft.organization_id == current_user.organization_id
        )
    )).scalars().all()
    ac_by_tail = {a.tail_number: a for a in all_ac}

    # Build a cache of airport coordinates to avoid N+1 queries
    base_icaos = {ac.base for ac in all_ac if ac.base}
    airport_coords = {}
    if base_icaos:
        airport_rows = (await db.execute(
            select(Airport.icao_code, Airport.latitude, Airport.longitude).where(
                Airport.icao_code.in_(base_icaos)
            )
        )).all()
        airport_coords = {row.icao_code: (row.latitude, row.longitude) for row in airport_rows}

    positions = list(adsb_live.values())

    # ── Add ground positions for aircraft not found in ADS-B ────────────
    for idx, tail in enumerate(tails):
        if tail in adsb_live:
            continue
        ac = ac_by_tail.get(tail)
        if not ac:
            continue
        coords = airport_coords.get(ac.base)
        # Offset grounded aircraft so they don't stack at the same spot
        offset = (idx * 0.002) - 0.003
        positions.append({
            "tail": tail,
            "lat": (coords[0] + offset) if coords else 25.038,
            "lon": (coords[1] + offset) if coords else -77.466,
            "altitude_ft": 0,
            "speed_kts": 0,
            "heading": None,
            "callsign": None,
            "seen_seconds": None,
            "rssi": None,
            "status": "ground",
            "note": "position estimated",
            "home_base": ac.base,
            "last_updated": now_ts,
        })

    all_ground = all(p["status"] == "ground" for p in positions)

    if all_ground:
        return {
            "degraded": True,
            "message": "ADS-B data unavailable — showing ground positions",
            "aircraft": positions,
            "timestamp": now_ts,
        }

    return {
        "aircraft": positions,
        "degraded": degraded,
        "timestamp": now_ts,
    }


import math
from app.models.mission import Mission, MissionStatus, FlightLeg
from app.models.airport import Airport


@router.get("/routes")
async def active_mission_routes(
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get active mission routes with waypoint geometry for the tracking map.

    Returns active/draft missions with their leg waypoints (airport lat/lon),
    aircraft tail number, and route summary. Suitable for drawing polylines
    and waypoint markers on the live flight tracking map.
    """
    # Get active + draft missions for this org
    result = await db.execute(
        select(Mission)
        .where(
            Mission.organization_id == current_user.organization_id,
            Mission.status.in_([MissionStatus.ACTIVE, MissionStatus.DRAFT]),
        )
        .order_by(Mission.created_at.desc())
    )
    missions = result.scalars().all()

    # Build airport lookup
    airport_result = await db.execute(select(Airport))
    airports = airport_result.scalars().all()
    airport_map = {a.icao_code.upper(): a for a in airports}

    # Build aircraft lookup
    ac_result = await db.execute(
        select(Aircraft).where(
            Aircraft.organization_id == current_user.organization_id
        )
    )
    aircraft_map = {a.id: a.tail_number for a in ac_result.scalars().all()}

    routes = []
    for m in missions:
        tail = aircraft_map.get(m.aircraft_id, "N/A") if m.aircraft_id else "N/A"
        legs_data = []
        for leg in sorted(m.legs, key=lambda x: x.leg_number):
            dep = airport_map.get(leg.departure_airport.upper())
            arr = airport_map.get(leg.arrival_airport.upper())
            alt = airport_map.get(leg.alternate_airport.upper()) if leg.alternate_airport else None

            leg_entry = {
                "leg_number": leg.leg_number,
                "departure_icao": leg.departure_airport,
                "arrival_icao": leg.arrival_airport,
                "alternate_icao": leg.alternate_airport,
                "departure_lat": dep.latitude if dep else None,
                "departure_lon": dep.longitude if dep else None,
                "arrival_lat": arr.latitude if arr else None,
                "arrival_lon": arr.longitude if arr else None,
                "alternate_lat": alt.latitude if alt else None,
                "alternate_lon": alt.longitude if alt else None,
                "distance_nm": leg.distance_nm,
                "status": leg.status.value,
                "scheduled_departure": leg.scheduled_departure.isoformat() if leg.scheduled_departure else None,
                "scheduled_arrival": leg.scheduled_arrival.isoformat() if leg.scheduled_arrival else None,
                "flight_time_minutes": leg.flight_time_minutes,
            }
            legs_data.append(leg_entry)

        # Compute route polyline (series of [lon, lat] for MapLibre)
        polyline = []
        for leg in legs_data:
            if leg["departure_lat"] is not None and leg["departure_lon"] is not None:
                if not polyline or polyline[-1] != [leg["departure_lon"], leg["departure_lat"]]:
                    polyline.append([leg["departure_lon"], leg["departure_lat"]])
            if leg["arrival_lat"] is not None and leg["arrival_lon"] is not None:
                polyline.append([leg["arrival_lon"], leg["arrival_lat"]])

        # Compute total distance and ETP candidates (overwater legs)
        total_distance_nm = sum(leg.get("distance_nm") or 0 for leg in legs_data)
        etp_candidates = []
        for leg in legs_data:
            dist = leg.get("distance_nm") or 0
            # Flag legs > 100nm as ETP candidates (overwater / remote)
            if dist > 100 and leg["departure_lat"] and leg["arrival_lat"]:
                mid_lat = (leg["departure_lat"] + leg["arrival_lat"]) / 2
                mid_lon = (leg["departure_lon"] + leg["arrival_lon"]) / 2
                etp_candidates.append({
                    "leg": leg["leg_number"],
                    "departure": leg["departure_icao"],
                    "arrival": leg["arrival_icao"],
                    "distance_nm": dist,
                    "etp_lat": round(mid_lat, 4),
                    "etp_lon": round(mid_lon, 4),
                })

        route_entry = {
            "mission_id": m.id,
            "status": m.status.value,
            "tail": tail,
            "aircraft_id": m.aircraft_id,
            "home_base": m.home_base,
            "pilot_in_command": m.pilot_in_command,
            "second_in_command": m.second_in_command,
            "mission_date": m.mission_date.isoformat() if m.mission_date else None,
            "legs": legs_data,
            "polyline": polyline,
            "total_legs": len(legs_data),
            "total_distance_nm": total_distance_nm,
            "etp_candidates": etp_candidates,
        }
        routes.append(route_entry)

    return {"routes": routes, "count": len(routes)}


@router.get("/notams/map")
async def notams_for_map(
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get NOTAMs geocoded to airport positions for map overlay.

    Returns NOTAMs grouped by airport with lat/lon for map markers.
    """
    from app.services.weather import get_notams

    # Get all airports (global, not org-scoped)
    result = await db.execute(select(Airport))
    airports_list = result.scalars().all()

    notam_markers = []
    for apt in airports_list[:20]:  # cap at 20 airports for performance
        try:
            notams = await get_notams(apt.icao_code)
            if notams:
                # Take top 3 most critical
                for n in notams[:3]:
                    notam_markers.append({
                        "icao": apt.icao_code,
                        "lat": apt.latitude,
                        "lon": apt.longitude,
                        "id": n.get("id", ""),
                        "message": (n.get("message") or "")[:200],
                        "type": n.get("type", ""),
                    })
        except Exception:
            continue

    return {"notams": notam_markers, "count": len(notam_markers)}
