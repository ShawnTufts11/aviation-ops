"""
Route planning endpoint — the "wow" piece.

POST /api/v1/routes/plan
  Takes an aircraft and a list of legs, returns a complete mission planning
  package: distances, block times, fuel, capabilities, and per-destination
  intel (FBOs, hotels, fuel prices, customs, MRO, restrictions).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_org_membership
from app.models.aircraft import Aircraft
from app.models.airport import Airport
from app.models.user import User
from app.services.route_planner import plan_route, route_plan_to_dict

router = APIRouter(prefix="/routes", tags=["routes"])


# ── Request schema ─────────────────────────────────────────────────────


class LegRequest(BaseModel):
    origin: str = Field(..., min_length=3, max_length=4, description="Origin ICAO code")
    destination: str = Field(..., min_length=3, max_length=4, description="Destination ICAO code")
    cruise_altitude_ft: int | None = Field(None, description="Cruise altitude in feet MSL")


class RoutePlanRequest(BaseModel):
    aircraft_id: str = Field(..., description="Aircraft UUID")
    legs: list[LegRequest] = Field(..., min_length=1, max_length=20, description="Route legs in order")
    passenger_counts: list[int] | None = Field(None, description="Passenger count per leg (optional, for W&B)")
    cargo_kg: float = Field(0.0, description="Cargo weight in kg (same for all legs)")
    crew_count: int = Field(2, description="Number of crew members")
    is_two_pilot: bool = Field(True, description="True for 2-pilot crew, False for 1-pilot")
    crew_members: list[dict] | None = Field(None, description="Optional crew info for duty time checks")


# ── Plan endpoint ──────────────────────────────────────────────────────


@router.post("/plan")
async def plan_route_endpoint(
    body: RoutePlanRequest,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Plan a multi-leg route.

    Given an aircraft and a list of legs (origin → destination), returns
    comprehensive planning data for the entire mission:
      - Per-leg: distance, block time, fuel, capabilities, destination intel
      - Totals: distance, time, fuel for the entire mission
      - Flags: overwater, permits, night ops, crew swap, fuel stops
    """
    # ── Resolve aircraft ─────────────────────────────────────────────────
    aircraft = await db.get(Aircraft, body.aircraft_id)
    if not aircraft or aircraft.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aircraft not found in your fleet",
        )

    # ── Resolve airports ─────────────────────────────────────────────────
    resolved_legs: list[tuple[Airport, Airport, int | None]] = []
    seen_icaos: set[str] = set()
    airport_cache: dict[str, Airport] = {}

    for leg_req in body.legs:
        origin_icao = leg_req.origin.upper()
        dest_icao = leg_req.destination.upper()

        for icao in (origin_icao, dest_icao):
            if icao not in airport_cache:
                apt = await db.get(Airport, icao)
                if not apt:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Airport {icao} not found in database. Use /api/v1/airports/lookup/{icao} to auto-populate.",
                    )
                airport_cache[icao] = apt

        resolved_legs.append((
            airport_cache[origin_icao],
            airport_cache[dest_icao],
            leg_req.cruise_altitude_ft,
        ))

    # ── Plan the route ───────────────────────────────────────────────────
    route_plan = await plan_route(
        aircraft=aircraft,
        legs=resolved_legs,
        passenger_counts=body.passenger_counts,
        cargo_kg=body.cargo_kg,
        crew_count=body.crew_count,
        is_two_pilot=body.is_two_pilot,
        crew_members=body.crew_members,
    )
    result = route_plan_to_dict(route_plan)

    return {
        "status": "ok",
        "plan": result,
    }
