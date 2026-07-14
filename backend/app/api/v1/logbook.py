"""Pilot logbook — auto-populated from completed flights."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_org_membership
from app.models.aircraft import Aircraft
from app.models.crew import CrewMember
from app.models.flight import Flight, FlightStatus
from app.models.logbook import PilotLogEntry
from app.models.mission import FlightLeg
from app.models.user import User

router = APIRouter(prefix="/logbook", tags=["logbook"])


@router.get("")
async def list_logbook(
    crew_id: str | None = Query(None),
    aircraft_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List logbook entries. Filter by crew member or aircraft."""
    conditions = [PilotLogEntry.organization_id == current_user.organization_id]
    if crew_id:
        conditions.append(PilotLogEntry.crew_id == crew_id)
    if aircraft_id:
        conditions.append(PilotLogEntry.aircraft_id == aircraft_id)

    query = select(PilotLogEntry).where(*conditions).order_by(PilotLogEntry.flight_date.desc())

    count_q = select(sa_func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    entries = result.scalars().all()

    return {
        "data": [
            {
                "id": e.id,
                "crew_id": e.crew_id,
                "flight_date": e.flight_date.isoformat(),
                "departure_airport": e.departure_airport,
                "arrival_airport": e.arrival_airport,
                "aircraft_tail": e.aircraft_tail,
                "aircraft_type": e.aircraft_type,
                "flight_time_hours": e.flight_time_hours,
                "day_landings": e.day_landings,
                "night_landings": e.night_landings,
                "pic": e.pic,
                "sic": e.sic,
                "remarks": e.remarks,
                "auto_generated": e.auto_generated,
                "cross_country": e.cross_country,
            }
            for e in entries
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/crew/{crew_id}/summary")
async def crew_logbook_summary(
    crew_id: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get summary stats for a pilot's logbook."""
    conditions = [
        PilotLogEntry.organization_id == current_user.organization_id,
        PilotLogEntry.crew_id == crew_id,
    ]

    result = await db.execute(
        select(
            sa_func.count(PilotLogEntry.id),
            sa_func.coalesce(sa_func.sum(PilotLogEntry.flight_time_hours), 0),
            sa_func.coalesce(sa_func.sum(PilotLogEntry.day_landings), 0),
            sa_func.coalesce(sa_func.sum(PilotLogEntry.night_landings), 0),
        ).where(*conditions)
    )
    row = result.one()
    total_entries, total_hours, total_day_ldgs, total_night_ldgs = row

    # Last 90 days
    ninety_days_ago = date.today() - __import__("datetime").timedelta(days=90)
    result_90 = await db.execute(
        select(sa_func.coalesce(sa_func.sum(PilotLogEntry.flight_time_hours), 0)).where(
            *conditions, PilotLogEntry.flight_date >= ninety_days_ago,
        )
    )
    hours_90 = result_90.scalar() or 0

    return {
        "crew_id": crew_id,
        "total_entries": total_entries,
        "total_flight_hours": float(total_hours),
        "hours_last_90_days": float(hours_90),
        "total_day_landings": int(total_day_ldgs),
        "total_night_landings": int(total_night_ldgs),
    }


@router.patch("/{entry_id}")
async def update_log_entry(
    entry_id: str,
    body: dict[str, Any],
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update a logbook entry (remarks, times, etc.)."""
    entry = await db.get(PilotLogEntry, entry_id)
    if not entry or entry.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Entry not found")

    allowed = {"remarks", "day_landings", "night_landings", "instrument_time",
               "night_time", "pic", "sic", "dual", "instructor"}
    for field, value in body.items():
        if field in allowed and value is not None:
            setattr(entry, field, value)
    entry.auto_generated = False
    entry.updated_at = datetime.now(timezone.utc)

    db.add(entry)
    await db.commit()

    return {"status": "updated", "id": entry_id}
