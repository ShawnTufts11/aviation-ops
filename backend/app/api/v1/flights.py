"""Flight operations endpoints — Module 4."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc, asc, and_, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.audit import log_action
from app.core.permissions import require_org_membership, require_role
from app.core.roles import Role
from app.models.aircraft import Aircraft
from app.models.flight import Flight, Route, FlightStatus
from app.models.user import User
from app.schemas.flight import (
    FlightCreate,
    FlightResponse,
    FlightUpdate,
    RouteCreate,
    RouteResponse,
)

router = APIRouter(prefix="/flights", tags=["flights"])


# ── List flights ────────────────────────────────────────────────


@router.get("")
async def list_flights(
    aircraft_id: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List flights with filtering."""
    org_id = current_user.organization_id
    conditions = [Flight.organization_id == org_id]

    if aircraft_id:
        conditions.append(Flight.aircraft_id == aircraft_id)
    if status_filter:
        conditions.append(Flight.status == status_filter)
    if from_date:
        conditions.append(Flight.scheduled_departure >= from_date)
    if to_date:
        conditions.append(Flight.scheduled_departure <= to_date + "T23:59:59")

    query = select(Flight).where(and_(*conditions))

    count_q = select(sa_func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Active flights first, then by departure time
    query = query.order_by(
        Flight.status == FlightStatus.ACTIVE,
        Flight.scheduled_departure.asc().nullslast(),
    )
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    flights = result.scalars().all()

    return {
        "data": [FlightResponse.model_validate(f) for f in flights],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ── Active flights (ops board) ──────────────────────────────────


@router.get("/active")
async def active_flights(
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> list[FlightResponse]:
    """Get all currently active/in-progress flights."""
    result = await db.execute(
        select(Flight).where(
            Flight.organization_id == current_user.organization_id,
            Flight.status == FlightStatus.ACTIVE,
        ).order_by(Flight.scheduled_departure.asc())
    )
    return [FlightResponse.model_validate(f) for f in result.scalars().all()]


# ── Today's flights (schedule board) ────────────────────────────


@router.get("/today")
async def todays_flights(
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> list[FlightResponse]:
    """Get today's scheduled flights."""
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)
    today_end = datetime.combine(date.today(), datetime.max.time()).replace(tzinfo=timezone.utc)

    result = await db.execute(
        select(Flight).where(
            Flight.organization_id == current_user.organization_id,
            Flight.scheduled_departure >= today_start,
            Flight.scheduled_departure <= today_end,
        ).order_by(Flight.scheduled_departure.asc())
    )
    return [FlightResponse.model_validate(f) for f in result.scalars().all()]


# ── Create flight ───────────────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_flight(
    body: FlightCreate,
    current_user: User = Depends(require_role([Role.ACCOUNTABLE_EXECUTIVE, Role.DIRECTOR_OF_OPERATIONS, Role.OPS_MANAGER])),
    db: AsyncSession = Depends(get_db),
) -> FlightResponse:
    """Create a new flight."""
    flight = Flight(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        aircraft_id=body.aircraft_id,
        flight_number=body.flight_number,
        flight_type=body.flight_type,
        status=FlightStatus.SCHEDULED,
        departure_airport=body.departure_airport.upper(),
        arrival_airport=body.arrival_airport.upper(),
        alternate_airport=body.alternate_airport.upper() if body.alternate_airport else None,
        scheduled_departure=body.scheduled_departure,
        scheduled_arrival=body.scheduled_arrival,
        pilot_in_command=body.pilot_in_command,
        second_in_command=body.second_in_command,
        passengers_count=body.passengers_count,
        cargo_weight_kg=body.cargo_weight_kg,
        notes=body.notes,
    )
    db.add(flight)
    await db.commit()
    await db.refresh(flight)

    await log_action(
        db=db, org_id=current_user.organization_id, user_id=current_user.id,
        action="flight.created", entity_type="flight", entity_id=flight.id,
        new_values={"flight_number": flight.flight_number, "route": f"{flight.departure_airport}→{flight.arrival_airport}"},
    )

    return FlightResponse.model_validate(flight)


# ── Get flight detail ───────────────────────────────────────────


@router.get("/{flight_id}")
async def get_flight(
    flight_id: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> FlightResponse:
    """Get a single flight."""
    flight = await db.get(Flight, flight_id)
    if not flight or flight.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Flight not found")
    return FlightResponse.model_validate(flight)


# ── Update flight ───────────────────────────────────────────────


@router.patch("/{flight_id}")
async def update_flight(
    flight_id: str,
    body: FlightUpdate,
    current_user: User = Depends(require_role([Role.ACCOUNTABLE_EXECUTIVE, Role.DIRECTOR_OF_OPERATIONS, Role.OPS_MANAGER])),
    db: AsyncSession = Depends(get_db),
) -> FlightResponse:
    """Update flight (status, times, crew, etc.)."""
    flight = await db.get(Flight, flight_id)
    if not flight or flight.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Flight not found")

    old_status = flight.status
    update_data = body.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if value is not None:
            setattr(flight, field, value)

    # Auto-calculate flight time when completed
    if update_data.get("status") == "completed" and flight.actual_departure and flight.actual_arrival and not update_data.get("flight_time_hours"):
        delta = flight.actual_arrival - flight.actual_departure
        flight.flight_time_hours = round(delta.total_seconds() / 3600, 2)

    # Auto-create financial records when completed
    if update_data.get("status") == "completed" and old_status != "completed":
        from app.models.finance import FinancialRecord, RecordType, CostCategory
        from datetime import date
        import uuid

        # Revenue entry (charter)
        rev_estimate = 5000.0  # placeholder — replace with rate card
        rev = FinancialRecord(
            id=str(uuid.uuid4()),
            organization_id=current_user.organization_id,
            aircraft_id=flight.aircraft_id,
            flight_id=flight.id,
            record_type=RecordType.REVENUE,
            category=CostCategory.CHARTER_REVENUE,
            amount=rev_estimate,
            description=f"Flight {flight.departure_airport}→{flight.arrival_airport}",
            entry_date=date.today(),
        )
        db.add(rev)

        # Fuel cost estimate
        if flight.fuel_burned_liters:
            fuel_cost = round(flight.fuel_burned_liters * 1.50, 2)  # $1.50/L estimate
            cost = FinancialRecord(
                id=str(uuid.uuid4()),
                organization_id=current_user.organization_id,
                aircraft_id=flight.aircraft_id,
                flight_id=flight.id,
                record_type=RecordType.COST,
                category=CostCategory.FUEL,
                amount=fuel_cost,
                description=f"Fuel {flight.fuel_burned_liters}L",
                entry_date=date.today(),
            )
            db.add(cost)

    # Auto-create logbook entries for PIC and SIC
    if flight.status == FlightStatus.COMPLETED and old_status != FlightStatus.COMPLETED:
        from app.models.logbook import PilotLogEntry
        from app.models.crew import CrewMember
        is_cross_country = flight.departure_airport[:2] != flight.arrival_airport[:2]
        for crew_field, is_pic in [("pilot_in_command", True), ("second_in_command", False)]:
            crew_id = getattr(flight, crew_field, None)
            if not crew_id:
                continue
            crew = await db.get(CrewMember, crew_id)
            if not crew:
                continue
            existing = await db.execute(
                select(PilotLogEntry).where(
                    PilotLogEntry.flight_id == flight.id,
                    PilotLogEntry.crew_id == crew_id,
                )
            )
            if existing.scalar_one_or_none():
                continue  # Already logged
            entry = PilotLogEntry(
                id=str(uuid.uuid4()),
                organization_id=current_user.organization_id,
                crew_id=crew_id,
                flight_id=flight.id,
                aircraft_id=flight.aircraft_id,
                flight_date=flight.actual_departure.date() if flight.actual_departure else date.today(),
                departure_airport=flight.departure_airport,
                arrival_airport=flight.arrival_airport,
                aircraft_tail="",
                aircraft_type="",
                flight_time_hours=flight.flight_time_hours or 0,
                pic=is_pic,
                sic=not is_pic,
                cross_country=is_cross_country,
            )
            # Get tail number and type
            ac = await db.get(Aircraft, flight.aircraft_id) if flight.aircraft_id else None
            if ac:
                entry.aircraft_tail = ac.tail_number
                entry.aircraft_type = f"{ac.make} {ac.model}"
            db.add(entry)

    flight.updated_at = datetime.now(timezone.utc)
    db.add(flight)
    await db.commit()
    await db.refresh(flight)

    await log_action(
        db=db, org_id=current_user.organization_id, user_id=current_user.id,
        action="flight.updated", entity_type="flight", entity_id=flight.id,
        old_values={"status": old_status}, new_values=update_data,
    )

    return FlightResponse.model_validate(flight)


# ── Cancel flight ───────────────────────────────────────────────


@router.post("/{flight_id}/cancel")
async def cancel_flight(
    flight_id: str,
    current_user: User = Depends(require_role([Role.ACCOUNTABLE_EXECUTIVE, Role.DIRECTOR_OF_OPERATIONS])),
    db: AsyncSession = Depends(get_db),
) -> FlightResponse:
    """Cancel a flight."""
    flight = await db.get(Flight, flight_id)
    if not flight or flight.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Flight not found")

    flight.status = FlightStatus.CANCELLED
    flight.updated_at = datetime.now(timezone.utc)
    db.add(flight)
    await db.commit()
    await db.refresh(flight)

    return FlightResponse.model_validate(flight)


# ── Routes ──────────────────────────────────────────────────────


@router.get("/routes")
async def list_routes(
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> list[RouteResponse]:
    """List frequently flown routes."""
    result = await db.execute(
        select(Route).where(
            Route.organization_id == current_user.organization_id,
            Route.is_active == True,
        ).order_by(Route.departure, Route.arrival)
    )
    return [RouteResponse.model_validate(r) for r in result.scalars().all()]


@router.post("/routes", status_code=status.HTTP_201_CREATED)
async def create_route(
    body: RouteCreate,
    current_user: User = Depends(require_role([Role.ACCOUNTABLE_EXECUTIVE, Role.DIRECTOR_OF_OPERATIONS])),
    db: AsyncSession = Depends(get_db),
) -> RouteResponse:
    """Add a frequently flown route."""
    route = Route(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        departure=body.departure.upper(),
        arrival=body.arrival.upper(),
        route_type=body.route_type,
        distance_nm=body.distance_nm,
        flight_time_mins=body.flight_time_mins,
    )
    db.add(route)
    await db.commit()
    await db.refresh(route)
    return RouteResponse.model_validate(route)
