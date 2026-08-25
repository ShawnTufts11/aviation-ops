"""Pre-flight operations checks — maintenance conflicts, route capability, weather."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_org_membership
from app.models.aircraft import Aircraft
from app.models.maintenance import MaintenanceTask
from app.models.user import User

router = APIRouter(prefix="/ops-checks", tags=["ops-checks"])


@router.get("/maintenance-conflicts")
async def maintenance_conflicts(
    aircraft_id: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Check an aircraft for open maintenance before scheduling a flight.

    Returns:
      - has_conflicts: true if any scheduled/overdue/in_progress tasks exist
      - open_tasks: list of conflicting tasks
      - severity: 'critical' if overdue, 'warning' if scheduled
    """
    ac = await db.get(Aircraft, aircraft_id)
    if not ac or ac.organization_id != current_user.organization_id:
        return {"has_conflicts": False, "open_tasks": [], "severity": None}

    # Get all non-completed tasks
    result = await db.execute(
        select(MaintenanceTask).where(
            MaintenanceTask.aircraft_id == aircraft_id,
            MaintenanceTask.status.in_(["scheduled", "overdue", "in_progress", "deferred"]),
        ).order_by(MaintenanceTask.scheduled_date.asc().nullslast())
    )
    tasks = result.scalars().all()

    if not tasks:
        return {"has_conflicts": False, "open_tasks": [], "severity": None}

    overdue = [t for t in tasks if t.status == "overdue"]
    severity = "critical" if overdue else "warning"

    return {
        "has_conflicts": True,
        "severity": severity,
        "open_tasks": [
            {
                "id": t.id,
                "title": t.title,
                "task_type": t.task_type,
                "status": t.status,
                "scheduled_date": t.scheduled_date.isoformat() if t.scheduled_date else None,
                "reference": t.reference,
            }
            for t in tasks
        ],
        "overdue_count": len(overdue),
        "total_open": len(tasks),
    }


@router.get("/route-capability")
async def route_capability(
    aircraft_id: str,
    departure: str = Query(..., min_length=3),
    arrival: str = Query(..., min_length=3),
    distance_nm: float | None = Query(None),
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Check if an aircraft can safely fly a route.

    Returns range capability, warnings if distance exceeds range,
    and a safety score.
    """
    ac = await db.get(Aircraft, aircraft_id)
    if not ac or ac.organization_id != current_user.organization_id:
        return {"capable": False, "error": "Aircraft not found"}

    range_nm = ac.range_nm
    if not range_nm:
        return {"capable": True, "range_nm": None, "note": "Range data not configured"}

    if not distance_nm:
        # Try to look up from routes table
        from app.models.flight import Route
        route_result = await db.execute(
            select(Route).where(
                Route.departure == departure,
                Route.arrival == arrival,
            ).limit(1)
        )
        route = route_result.scalar_one_or_none()
        if route and route.distance_nm:
            distance_nm = float(route.distance_nm)

    if not distance_nm:
        return {
            "capable": True,
            "range_nm": range_nm,
            "distance_nm": None,
            "note": "Distance unknown — check manually",
        }

    safe_range = range_nm * 0.75  # 75% of max range (reserve fuel)
    margin_nm = safe_range - distance_nm

    return {
        "capable": margin_nm >= 0,
        "range_nm": range_nm,
        "safe_range_nm": round(safe_range, 0),
        "distance_nm": distance_nm,
        "margin_nm": round(margin_nm, 0),
        "requires_fuel_stop": margin_nm < 0,
        "advisory": "Within range" if margin_nm >= 50 else
                    "Tight — verify fuel reserves" if margin_nm >= 0 else
                    "EXCEEDS SAFE RANGE — requires fuel stop",
    }


@router.get("/weather")
async def route_weather(
    departure: str = Query(..., min_length=3),
    arrival: str = Query(..., min_length=3),
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Fetch live METAR weather for departure and arrival airports.

    Uses Open-Meteo Aviation API (free, no API key required).
    """
    async with httpx.AsyncClient(timeout=10) as client:
        dep_resp = await client.get(
            f"https://aviation-api.open-meteo.com/v1/metar",
            params={"icao": departure},
        )
        arr_resp = await client.get(
            f"https://aviation-api.open-meteo.com/v1/metar",
            params={"icao": arrival},
        )

    result: dict[str, Any] = {
        "departure": {"icao": departure, "metar": None, "error": None},
        "arrival": {"icao": arrival, "metar": None, "error": None},
        "conditions": "unknown",
    }

    for key, resp in [("departure", dep_resp), ("arrival", arr_resp)]:
        if resp.status_code == 200:
            data = resp.json()
            raw = data.get("metar", {}).get("raw") if isinstance(data.get("metar"), dict) else data.get("raw")
            result[key]["metar"] = raw
        else:
            result[key]["error"] = f"HTTP {resp.status_code}"

    # Simple conditions assessment
    dep_raw = result["departure"]["metar"] or ""
    arr_raw = result["arrival"]["metar"] or ""

    if "VFR" in dep_raw and "VFR" in arr_raw:
        result["conditions"] = "vfr"
    elif "IFR" in dep_raw or "IFR" in arr_raw:
        result["conditions"] = "ifr"
    elif "MVFR" in dep_raw or "MVFR" in arr_raw:
        result["conditions"] = "mvfr"
    elif dep_raw or arr_raw:
        result["conditions"] = "check_manually"
    else:
        result["conditions"] = "no_data"

    return result


@router.get("/all")
async def full_preflight_check(
    aircraft_id: str,
    departure: str = Query(..., min_length=3),
    arrival: str = Query(..., min_length=3),
    distance_nm: float | None = None,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Run all pre-flight checks in one call.

    Combines maintenance conflicts, route capability, and weather.
    """
    mx = await maintenance_conflicts(aircraft_id, current_user, db)
    route = await route_capability(aircraft_id, departure, arrival, distance_nm, current_user, db)
    weather = await route_weather(departure, arrival, current_user, db)

    warnings = []
    if mx.get("has_conflicts"):
        if mx.get("severity") == "critical":
            warnings.append(f"⚠️ {mx['overdue_count']} overdue maintenance tasks — resolve before flight")
        else:
            warnings.append(f"🟡 {mx['total_open']} open maintenance tasks")
    if not route.get("capable"):
        warnings.append(f"⛔ Route exceeds safe range ({route.get('distance_nm', '?')}nm vs {route.get('safe_range_nm', '?')}nm safe)")
    if weather.get("conditions") == "ifr":
        warnings.append("🌧️ IFR conditions at one or both airports")
    elif weather.get("conditions") == "no_data":
        warnings.append("🌤️ Weather data unavailable — check manually")

    go = len([w for w in warnings if w.startswith("⛔")]) == 0

    return {
        "flight_ready": go,
        "warnings": warnings,
        "maintenance": mx,
        "route": route,
        "weather": weather,
    }


from app.models.airport import Airport

@router.get("/weather/briefing")
async def weather_briefing(
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return METAR flight categories for the organization's region airports."""
    result = await db.execute(
        select(Airport).limit(20)
    )
    airports_data = result.scalars().all()
    
    from app.services.weather import get_metar, weather_to_dict
    weather_data = {}
    for ap in airports_data:
        if not ap.latitude or not ap.longitude:
            continue
        try:
            metar = await get_metar(ap.icao_code)
            if metar and not metar.error:
                wx = weather_to_dict(metar)
                weather_data[ap.icao_code] = {
                    "flight_category": wx.get("flight_category", "UNKNOWN"),
                    "wind": f'{wx.get("wind_direction_deg", "")}@{wx.get("wind_speed_kt", "")}' if wx.get("wind_speed_kt") else None,
                    "visibility": wx.get("visibility_statute_mi"),
                    "raw_metar": wx.get("raw_metar", ""),
                }
        except Exception:
            pass
    return {"airports": weather_data}
