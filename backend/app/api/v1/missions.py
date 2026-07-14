"""Multi-leg mission planning API — Phase 1."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc, asc, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.audit import log_action
from app.core.permissions import require_org_membership, require_role
from app.core.roles import Role
from app.models.aircraft import Aircraft
from app.models.mission import (
    Mission, FlightLeg, ManifestEntry, AircraftFuelProfile,
    MissionStatus, LegStatus,
)
from app.models.user import User
from app.schemas.mission import (
    MissionCreate, MissionResponse, MissionUpdate,
    LegCreate, LegUpdate, LegResponse,
    ManifestEntryCreate, ManifestEntryResponse,
    FuelProfileCreate, FuelProfileResponse,
)

router = APIRouter(prefix="/missions", tags=["missions"])


# ── Fuel calculation helper ────────────────────────────────────


async def _calc_fuel(aircraft_id: str, distance_nm: int | None,
                     db: AsyncSession) -> dict[str, Any]:
    """Calculate fuel required for a given distance using aircraft's fuel profile."""
    if not distance_nm:
        return {"fuel_required_l": None, "profile_used": None}

    profile = await db.execute(
        select(AircraftFuelProfile).where(
            AircraftFuelProfile.aircraft_id == aircraft_id
        )
    )
    profile = profile.scalar_one_or_none()
    if not profile:
        return {"fuel_required_l": None, "profile_used": None}

    speed = profile.cruise_speed_kt or 180
    flight_hours = distance_nm / speed
    cruise_fuel = flight_hours * profile.cruise_burn_lph
    reserve_fuel = (profile.reserve_minutes / 60) * profile.cruise_burn_lph
    climb_fuel = (profile.climb_burn_lph or profile.cruise_burn_lph) * 0.15
    descent_fuel = (profile.descent_burn_lph or profile.cruise_burn_lph) * 0.1

    total = cruise_fuel + reserve_fuel + climb_fuel + descent_fuel

    return {
        "fuel_required_l": round(total, 1),
        "flight_hours": round(flight_hours, 1),
        "cruise_fuel_l": round(cruise_fuel, 1),
        "reserve_fuel_l": round(reserve_fuel, 1),
        "profile_used": {"cruise_burn": profile.cruise_burn_lph, "speed": speed},
    }


# ── Main warnings helper ───────────────────────────────────────


async def _mission_warnings(mission: Mission, db: AsyncSession) -> list[str]:
    """Run all pre-flight checks on a mission."""
    warnings = []
    ac = await db.get(Aircraft, mission.aircraft_id) if mission.aircraft_id else None

    for leg in mission.legs:
        # Range check
        if ac and ac.range_nm and leg.distance_nm:
            safe_range = ac.range_nm * 0.75
            if leg.distance_nm > safe_range:
                warnings.append(
                    f"Leg {leg.leg_number}: {leg.departure_airport}→{leg.arrival_airport} "
                    f"({leg.distance_nm}nm) exceeds safe range of {int(safe_range)}nm"
                )

        # Fuel check
        if leg.fuel_on_board_l and leg.fuel_required_l:
            if leg.fuel_on_board_l < leg.fuel_required_l:
                warnings.append(
                    f"Leg {leg.leg_number}: Fuel {leg.fuel_on_board_l}L < required {leg.fuel_required_l}L"
                )

    # Maintenance catch-up warning
    if ac and mission.legs:
        from app.models.maintenance import MaintenanceTask
        last_leg = mission.legs[-1]
        return_date = last_leg.scheduled_arrival.date() if last_leg.scheduled_arrival else None

        if return_date:
            mx = await db.execute(
                select(MaintenanceTask).where(
                    MaintenanceTask.aircraft_id == ac.id,
                    MaintenanceTask.status.in_(["scheduled", "overdue"]),
                    MaintenanceTask.scheduled_date <= return_date,
                ).limit(3)
            )
            for task in mx.scalars().all():
                warnings.append(
                    f"⚠ Maintenance '{task.title}' due {task.scheduled_date} — "
                    f"aircraft will be away from base"
                )

    return warnings


# ── Missions CRUD ──────────────────────────────────────────────


@router.get("")
async def list_missions(
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=50),
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List missions."""
    conditions = [Mission.organization_id == current_user.organization_id]
    if status_filter:
        conditions.append(Mission.status == status_filter)

    query = select(Mission).where(*conditions).order_by(Mission.created_at.desc())
    count_q = select(sa_func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    return {
        "data": [MissionResponse.model_validate(m) for m in result.scalars().all()],
        "total": total, "page": page, "per_page": per_page,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_mission(
    body: MissionCreate,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.OPS_MANAGER])),
    db: AsyncSession = Depends(get_db),
) -> MissionResponse:
    """Create a new mission shell."""
    mission = Mission(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        aircraft_id=body.aircraft_id,
        pilot_in_command=body.pilot_in_command,
        second_in_command=body.second_in_command,
        mission_date=body.mission_date,
        home_base=body.home_base,
        notes=body.notes,
    )
    db.add(mission)
    await db.commit()
    await db.refresh(mission)
    return MissionResponse.model_validate(mission)


@router.get("/{mission_id}")
async def get_mission(
    mission_id: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get mission detail with legs, manifest, and warnings."""
    mission = await db.get(Mission, mission_id)
    if not mission or mission.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Mission not found")

    warnings = await _mission_warnings(mission, db)

    return {
        "mission": MissionResponse.model_validate(mission),
        "warnings": warnings,
    }


@router.patch("/{mission_id}")
async def update_mission(
    mission_id: str,
    body: MissionUpdate,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.OPS_MANAGER])),
    db: AsyncSession = Depends(get_db),
) -> MissionResponse:
    """Update mission (aircraft, crew, status)."""
    mission = await db.get(Mission, mission_id)
    if not mission or mission.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Mission not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(mission, field, value)

    mission.updated_at = datetime.now(timezone.utc)
    db.add(mission)
    await db.commit()
    await db.refresh(mission)
    return MissionResponse.model_validate(mission)


@router.delete("/{mission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mission(
    mission_id: str,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """Delete a draft mission."""
    mission = await db.get(Mission, mission_id)
    if not mission or mission.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Mission not found")
    if mission.status != MissionStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Can only delete draft missions")
    await db.delete(mission)
    await db.commit()


# ── Legs ────────────────────────────────────────────────────────


@router.post("/{mission_id}/legs", status_code=status.HTTP_201_CREATED)
async def add_leg(
    mission_id: str,
    body: LegCreate,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.OPS_MANAGER])),
    db: AsyncSession = Depends(get_db),
) -> LegResponse:
    """Add a flight leg to a mission. Auto-calculates fuel if profile exists."""
    mission = await db.get(Mission, mission_id)
    if not mission or mission.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Mission not found")

    leg = FlightLeg(
        id=str(uuid.uuid4()),
        mission_id=mission_id,
        leg_number=body.leg_number,
        departure_airport=body.departure_airport.upper(),
        arrival_airport=body.arrival_airport.upper(),
        alternate_airport=body.alternate_airport.upper() if body.alternate_airport else None,
        scheduled_departure=body.scheduled_departure,
        scheduled_arrival=body.scheduled_arrival,
        distance_nm=body.distance_nm,
        fuel_on_board_l=body.fuel_on_board_l,
        notams=body.notams,
    )

    # Auto-calculate fuel
    if mission.aircraft_id and body.distance_nm and not body.fuel_on_board_l:
        fuel_info = await _calc_fuel(mission.aircraft_id, body.distance_nm, db)
        leg.fuel_required_l = fuel_info.get("fuel_required_l")

    db.add(leg)
    await db.commit()
    await db.refresh(leg)
    return LegResponse.model_validate(leg)


@router.get("/{mission_id}/legs")
async def list_legs(
    mission_id: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> list[LegResponse]:
    """List all legs for a mission."""
    mission = await db.get(Mission, mission_id)
    if not mission or mission.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Mission not found")
    return [LegResponse.model_validate(l) for l in mission.legs]


@router.patch("/{mission_id}/legs/{leg_id}")
async def update_leg(
    mission_id: str,
    leg_id: str,
    body: LegUpdate,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.OPS_MANAGER])),
    db: AsyncSession = Depends(get_db),
) -> LegResponse:
    """Update a flight leg (status, times, fuel, NOTAMs)."""
    leg = await db.get(FlightLeg, leg_id)
    if not leg or leg.mission_id != mission_id:
        raise HTTPException(status_code=404, detail="Leg not found")

    update_data = body.model_dump(exclude_unset=True)
    old_status = leg.status
    for field, value in update_data.items():
        if value is not None:
            setattr(leg, field, value)

    # Auto-complete leg
    if update_data.get("status") == "completed" and old_status != "completed":
        leg.actual_arrival = datetime.now(timezone.utc)
        if leg.scheduled_departure and leg.scheduled_arrival:
            delta = (leg.actual_arrival or leg.scheduled_arrival) - (leg.actual_departure or leg.scheduled_departure)
            leg.flight_time_minutes = int(delta.total_seconds() / 60)

    db.add(leg)
    await db.commit()
    await db.refresh(leg)
    return LegResponse.model_validate(leg)


# ── Manifest ────────────────────────────────────────────────────


@router.get("/{mission_id}/legs/{leg_id}/manifest")
async def get_manifest(
    mission_id: str,
    leg_id: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> list[ManifestEntryResponse]:
    """Get manifest entries for a leg."""
    leg = await db.get(FlightLeg, leg_id)
    if not leg or leg.mission_id != mission_id:
        raise HTTPException(status_code=404, detail="Leg not found")
    return [ManifestEntryResponse.model_validate(m) for m in leg.manifest_entries]


@router.post("/{mission_id}/legs/{leg_id}/manifest", status_code=status.HTTP_201_CREATED)
async def add_manifest_entry(
    mission_id: str,
    leg_id: str,
    body: ManifestEntryCreate,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.OPS_MANAGER])),
    db: AsyncSession = Depends(get_db),
) -> ManifestEntryResponse:
    """Add a passenger, crew, or cargo to a leg's manifest."""
    leg = await db.get(FlightLeg, leg_id)
    if not leg or leg.mission_id != mission_id:
        raise HTTPException(status_code=404, detail="Leg not found")

    entry = ManifestEntry(
        id=str(uuid.uuid4()),
        leg_id=leg_id,
        entry_type=body.entry_type,
        full_name=body.full_name,
        date_of_birth=body.date_of_birth,
        gender=body.gender,
        nationality=body.nationality,
        passport_number=body.passport_number,
        passport_expiry=body.passport_expiry,
        id_number=body.id_number,
        weight_kg=body.weight_kg,
        boarding_leg_number=body.boarding_leg_number or leg.leg_number,
        deplaning_leg_number=body.deplaning_leg_number,
        description=body.description,
        hazardous=body.hazardous,
        notes=body.notes,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return ManifestEntryResponse.model_validate(entry)


@router.delete("/{mission_id}/legs/{leg_id}/manifest/{entry_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def remove_manifest_entry(
    mission_id: str, leg_id: str, entry_id: str,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.OPS_MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """Remove a manifest entry."""
    entry = await db.get(ManifestEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    await db.delete(entry)
    await db.commit()


# ── Fuel Profiles ───────────────────────────────────────────────


@router.get("/fuel-profiles")
async def list_fuel_profiles(
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> list[FuelProfileResponse]:
    """List all fuel profiles for org's aircraft."""
    ac_ids = (
        select(Aircraft.id).where(
            Aircraft.organization_id == current_user.organization_id
        )
    )
    result = await db.execute(
        select(AircraftFuelProfile).where(
            AircraftFuelProfile.aircraft_id.in_(ac_ids)
        )
    )
    return [FuelProfileResponse.model_validate(p) for p in result.scalars().all()]


@router.put("/fuel-profiles/{aircraft_id}")
async def set_fuel_profile(
    aircraft_id: str,
    body: FuelProfileCreate,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.OPS_MANAGER])),
    db: AsyncSession = Depends(get_db),
) -> FuelProfileResponse:
    """Create or update fuel profile for an aircraft."""
    ac = await db.get(Aircraft, aircraft_id)
    if not ac or ac.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Aircraft not found")

    existing = await db.execute(
        select(AircraftFuelProfile).where(
            AircraftFuelProfile.aircraft_id == aircraft_id
        )
    )
    profile = existing.scalar_one_or_none()

    if profile:
        for field, value in body.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(profile, field, value)
    else:
        profile = AircraftFuelProfile(
            id=str(uuid.uuid4()),
            aircraft_id=aircraft_id,
            **body.model_dump(exclude_unset=True),
        )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return FuelProfileResponse.model_validate(profile)
