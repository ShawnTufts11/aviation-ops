"""Aircraft CRUD endpoints — fleet configuration (Module 2)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.audit import log_action
from app.core.permissions import require_org_membership, require_role
from app.core.roles import Role
from app.models.aircraft import Aircraft, AircraftComponent
from app.models.user import User
from app.schemas.aircraft import (
    AircraftCreate,
    AircraftResponse,
    AircraftUpdate,
    ComponentCreate,
    ComponentResponse,
)

router = APIRouter(prefix="/aircraft", tags=["aircraft"])


# ── List aircraft ────────────────────────────────────────────────


@router.get("")
async def list_aircraft(
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None, alias="q"),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List aircraft for the current user's organization."""
    query = select(Aircraft).where(
        Aircraft.organization_id == current_user.organization_id
    )

    if status_filter:
        query = query.where(Aircraft.status == status_filter)
    if search:
        like = f"%{search}%"
        query = query.where(
            Aircraft.tail_number.ilike(like)
            | Aircraft.make.ilike(like)
            | Aircraft.model.ilike(like)
        )

    # Count
    from sqlalchemy import func as sa_func
    count_query = select(sa_func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginated query
    query = query.order_by(desc(Aircraft.updated_at))
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    aircraft = result.scalars().all()

    return {
        "data": [AircraftResponse.model_validate(a) for a in aircraft],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ── Create aircraft ──────────────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_aircraft(
    body: AircraftCreate,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.OPS_MANAGER, Role.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> AircraftResponse:
    """Add a new aircraft to the fleet."""
    # Check tail number uniqueness within org
    existing = await db.execute(
        select(Aircraft).where(
            Aircraft.tail_number == body.tail_number.upper(),
            Aircraft.organization_id == current_user.organization_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tail number already registered in your fleet",
        )

    aircraft = Aircraft(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        tail_number=body.tail_number.upper(),
        make=body.make,
        model=body.model,
        year=body.year,
        serial_number=body.serial_number or f"{body.make}-{body.year}-{uuid.uuid4().hex[:6].upper()}",
        category=body.category,
        mtow_kg=body.mtow_kg,
        max_seats=body.max_seats,
        max_cargo_kg=body.max_cargo_kg,
        status=body.status,
        base=body.base.upper(),
        home_airport=body.home_airport.upper(),
        country_reg=body.country_reg.upper(),
    )
    db.add(aircraft)
    await db.commit()
    await db.refresh(aircraft)

    await log_action(
        db=db, org_id=current_user.organization_id, user_id=current_user.id,
        action="aircraft.created", entity_type="aircraft", entity_id=aircraft.id,
        new_values={"tail_number": aircraft.tail_number, "make": aircraft.make, "model": aircraft.model},
    )

    return AircraftResponse.model_validate(aircraft)


# ── Get aircraft detail ──────────────────────────────────────────


@router.get("/{aircraft_id}")
async def get_aircraft(
    aircraft_id: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get full aircraft details with components."""
    aircraft = await db.get(Aircraft, aircraft_id)
    if not aircraft or aircraft.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Aircraft not found")

    # Get components
    comp_result = await db.execute(
        select(AircraftComponent).where(
            AircraftComponent.aircraft_id == aircraft_id
        ).order_by(AircraftComponent.name)
    )
    components = comp_result.scalars().all()

    return {
        "aircraft": AircraftResponse.model_validate(aircraft),
        "components": [ComponentResponse.model_validate(c) for c in components],
    }


# ── Update aircraft ──────────────────────────────────────────────


@router.patch("/{aircraft_id}")
async def update_aircraft(
    aircraft_id: str,
    body: AircraftUpdate,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.OPS_MANAGER, Role.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> AircraftResponse:
    """Update aircraft fields."""
    aircraft = await db.get(Aircraft, aircraft_id)
    if not aircraft or aircraft.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Aircraft not found")

    update_data = body.model_dump(exclude_unset=True)
    old_values = {"status": aircraft.status, "hours": aircraft.total_airframe_hours}

    for field, value in update_data.items():
        if value is not None:
            if field in ("tail_number", "base", "home_airport", "country_reg"):
                value = value.upper()
            setattr(aircraft, field, value)

    aircraft.updated_at = datetime.now(timezone.utc)
    db.add(aircraft)
    await db.commit()
    await db.refresh(aircraft)

    await log_action(
        db=db, org_id=current_user.organization_id, user_id=current_user.id,
        action="aircraft.updated", entity_type="aircraft", entity_id=aircraft.id,
        old_values=old_values, new_values=update_data,
    )

    return AircraftResponse.model_validate(aircraft)


# ── Delete aircraft ──────────────────────────────────────────────


@router.delete("/{aircraft_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_aircraft(
    aircraft_id: str,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """Delete an aircraft (super_admin only)."""
    aircraft = await db.get(Aircraft, aircraft_id)
    if not aircraft or aircraft.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Aircraft not found")

    await log_action(
        db=db, org_id=current_user.organization_id, user_id=current_user.id,
        action="aircraft.deleted", entity_type="aircraft", entity_id=aircraft.id,
        old_values={"tail_number": aircraft.tail_number},
    )

    await db.delete(aircraft)
    await db.commit()


# ── Components ───────────────────────────────────────────────────


@router.get("/{aircraft_id}/components")
async def list_components(
    aircraft_id: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> list[ComponentResponse]:
    """List all tracked components for an aircraft."""
    aircraft = await db.get(Aircraft, aircraft_id)
    if not aircraft or aircraft.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Aircraft not found")

    result = await db.execute(
        select(AircraftComponent).where(
            AircraftComponent.aircraft_id == aircraft_id
        ).order_by(AircraftComponent.name)
    )
    return [ComponentResponse.model_validate(c) for c in result.scalars().all()]


@router.post("/{aircraft_id}/components", status_code=status.HTTP_201_CREATED)
async def add_component(
    aircraft_id: str,
    body: ComponentCreate,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.OPS_MANAGER, Role.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> ComponentResponse:
    """Add a tracked component to an aircraft."""
    aircraft = await db.get(Aircraft, aircraft_id)
    if not aircraft or aircraft.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Aircraft not found")

    component = AircraftComponent(
        id=str(uuid.uuid4()),
        aircraft_id=aircraft_id,
        organization_id=current_user.organization_id,
        name=body.name,
        part_number=body.part_number,
        serial_number=body.serial_number,
        component_type=body.component_type,
        position=body.position,
        installed_date=body.installed_date,
        installed_hours=body.installed_hours,
        tbo_hours=body.tbo_hours,
        tbo_cycles=body.tbo_cycles,
        tbo_calendar_days=body.tbo_calendar_days,
        life_limited=body.life_limited,
        notes=body.notes,
    )
    db.add(component)
    await db.commit()
    await db.refresh(component)
    return ComponentResponse.model_validate(component)
