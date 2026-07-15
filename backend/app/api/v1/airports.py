"""
Airport management endpoints — route planning foundation.

Provides CRUD for the global airport database and a distance calculator
for use by the mission builder and flight planning services.
"""

from __future__ import annotations

import math
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_org_membership
from app.core.roles import Role
from app.models.airport import Airport
from app.models.user import User
from app.schemas.airport import (
    AirportCreate,
    AirportDistanceResponse,
    AirportResponse,
    AirportUpdate,
)

router = APIRouter(prefix="/airports", tags=["airports"])


# ── Great-circle distance ──────────────────────────────────────────────


def _haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Compute the great-circle distance between two points in nautical miles.

    Uses the Haversine formula — accurate to ~0.5% for most aviation-grade
    route calculations.
    """
    R_km = 6371.0  # Earth mean radius (km)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R_km * c * 0.539957  # km → nm


# ── List airports ──────────────────────────────────────────────────────


@router.get("")
async def list_airports(
    search: str | None = Query(None, alias="q"),
    country: str | None = Query(None),
    has_customs: bool | None = Query(None),
    has_jet_a: bool | None = Query(None),
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Search the global airport database."""
    query = select(Airport)

    if search:
        like = f"%{search.upper()}%"
        query = query.where(
            Airport.icao_code.ilike(like)
            | Airport.iata_code.ilike(like)
            | Airport.name.ilike(like)
        )
    if country:
        query = query.where(Airport.country_code == country.upper())
    if has_customs is not None:
        query = query.where(Airport.has_customs == has_customs)
    if has_jet_a is not None:
        query = query.where(Airport.has_jet_a == has_jet_a)

    query = query.order_by(Airport.country_code, Airport.icao_code)

    result = await db.execute(query)
    airports = result.scalars().all()

    return {
        "data": [AirportResponse.model_validate(a) for a in airports],
        "total": len(airports),
    }


# ── Get airport by ICAO ────────────────────────────────────────────────


@router.get("/{icao_code}")
async def get_airport(
    icao_code: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> AirportResponse:
    """Get full airport details by ICAO code."""
    airport = await db.get(Airport, icao_code.upper())
    if not airport:
        raise HTTPException(status_code=404, detail="Airport not found")
    return AirportResponse.model_validate(airport)


# ── Create airport ─────────────────────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_airport(
    body: AirportCreate,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> AirportResponse:
    """Add an airport to the global database."""
    icao = body.icao_code.upper()
    existing = await db.get(Airport, icao)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Airport {icao} already exists",
        )

    airport = Airport(
        icao_code=icao,
        iata_code=body.iata_code.upper() if body.iata_code else None,
        name=body.name,
        latitude=body.latitude,
        longitude=body.longitude,
        timezone=body.timezone,
        elevation_ft=body.elevation_ft,
        country_code=body.country_code.upper(),
        region=body.region,
        longest_runway_ft=body.longest_runway_ft,
        runway_surface=body.runway_surface,
        has_jet_a=body.has_jet_a,
        has_avgas=body.has_avgas,
        has_customs=body.has_customs,
        has_landing_permit_required=body.has_landing_permit_required,
        has_overflight_permit_required=body.has_overflight_permit_required,
        operating_hours=body.operating_hours,
        notes=body.notes,
    )
    db.add(airport)
    await db.commit()
    await db.refresh(airport)
    return AirportResponse.model_validate(airport)


# ── Update airport ─────────────────────────────────────────────────────


@router.patch("/{icao_code}")
async def update_airport(
    icao_code: str,
    body: AirportUpdate,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> AirportResponse:
    """Update airport fields."""
    airport = await db.get(Airport, icao_code.upper())
    if not airport:
        raise HTTPException(status_code=404, detail="Airport not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(airport, field, value)

    db.add(airport)
    await db.commit()
    await db.refresh(airport)
    return AirportResponse.model_validate(airport)


# ── Delete airport ─────────────────────────────────────────────────────


@router.delete("/{icao_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_airport(
    icao_code: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
):
    """Remove an airport from the database."""
    airport = await db.get(Airport, icao_code.upper())
    if not airport:
        raise HTTPException(status_code=404, detail="Airport not found")
    await db.delete(airport)
    await db.commit()


# ── Distance calculator ────────────────────────────────────────────────


@router.get("/{origin}/distance/{destination}")
async def calculate_distance(
    origin: str,
    destination: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> AirportDistanceResponse:
    """Calculate great-circle distance between two airports."""
    orig_apt = await db.get(Airport, origin.upper())
    dest_apt = await db.get(Airport, destination.upper())

    if not orig_apt:
        raise HTTPException(status_code=404, detail=f"Origin {origin.upper()} not found")
    if not dest_apt:
        raise HTTPException(status_code=404, detail=f"Destination {destination.upper()} not found")

    distance_nm = round(
        _haversine_nm(
            orig_apt.latitude, orig_apt.longitude,
            dest_apt.latitude, dest_apt.longitude,
        ),
        1,
    )
    distance_km = round(distance_nm * 1.852, 1)

    return AirportDistanceResponse(
        origin=AirportResponse.model_validate(orig_apt),
        destination=AirportResponse.model_validate(dest_apt),
        distance_nm=distance_nm,
        distance_km=distance_km,
    )
