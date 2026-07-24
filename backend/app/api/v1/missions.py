"""Multi-leg mission planning API — Phase 1."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
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
from app.services.crew_duty import check_crew_duty, duty_check_to_dict
from app.services.weight_balance import (
    calculate_leg_wb,
    wb_to_dict,
    JET_A_KG_PER_L,
    JET_A_KG_PER_GAL,
)

router = APIRouter(prefix="/missions", tags=["missions"])


# ── Request models for W&B and duty-check ─────────────────────


class WeightBalanceRequest(BaseModel):
    """Optional overrides for the per-leg W&B calculation."""
    fuel_burn_gal: dict[int, float] | None = None


class DutyCrewMember(BaseModel):
    """Historical / cumulative data for a crew member on duty check."""
    name: str
    role: str
    is_pilot: bool = True
    last_duty_end: datetime | None = None
    flight_time_24hr: float = 0.0
    flight_time_quarter_hrs: float = 0.0
    flight_time_two_quarter_hrs: float = 0.0
    flight_time_year_hrs: float = 0.0


class DutyCheckRequest(BaseModel):
    """Optional overrides / historical data for crew duty check."""
    crew_members: list[DutyCrewMember] | None = None
    hypothetical_departure: datetime | None = None
    is_two_pilot: bool | None = None


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
    current_user: User = Depends(require_role([Role.ACCOUNTABLE_EXECUTIVE, Role.DIRECTOR_OF_OPERATIONS])),
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
    current_user: User = Depends(require_role([Role.ACCOUNTABLE_EXECUTIVE, Role.DIRECTOR_OF_OPERATIONS])),
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
    current_user: User = Depends(require_role([Role.ACCOUNTABLE_EXECUTIVE])),
    db: AsyncSession = Depends(get_db),
):
    """Delete a mission. Audit-logged for compliance tracking."""
    mission = await db.get(Mission, mission_id)
    if not mission or mission.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Mission not found")
    status_val = mission.status.value if hasattr(mission.status, 'value') else str(mission.status)
    await log_action(
        db=db, org_id=current_user.organization_id, user_id=current_user.id,
        action="mission.deleted", entity_type="mission", entity_id=mission.id,
        new_values={"status": status_val},
    )
    await db.delete(mission)
    await db.commit()


# ── Legs ────────────────────────────────────────────────────────


@router.post("/{mission_id}/legs", status_code=status.HTTP_201_CREATED)
async def add_leg(
    mission_id: str,
    body: LegCreate,
    current_user: User = Depends(require_role([Role.ACCOUNTABLE_EXECUTIVE, Role.DIRECTOR_OF_OPERATIONS])),
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
    current_user: User = Depends(require_role([Role.ACCOUNTABLE_EXECUTIVE, Role.DIRECTOR_OF_OPERATIONS])),
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
    current_user: User = Depends(require_role([Role.ACCOUNTABLE_EXECUTIVE, Role.DIRECTOR_OF_OPERATIONS])),
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
    current_user: User = Depends(require_role([Role.ACCOUNTABLE_EXECUTIVE, Role.DIRECTOR_OF_OPERATIONS])),
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
    current_user: User = Depends(require_role([Role.ACCOUNTABLE_EXECUTIVE, Role.DIRECTOR_OF_OPERATIONS])),
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


# ── Weight & Balance ──────────────────────────────────────────


@router.post("/{mission_id}/weight-balance")
async def mission_weight_balance(
    mission_id: str,
    body: WeightBalanceRequest | None = None,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Calculate weight & balance for each leg of a planned mission.

    Reads the mission's aircraft, all legs (with distances), and existing
    manifests (passengers + cargo). Returns per-leg W&B reports plus a
    mission-level summary.
    """
    mission = await db.get(Mission, mission_id)
    if not mission or mission.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Mission not found")
    if not mission.aircraft_id:
        raise HTTPException(status_code=400, detail="Mission has no aircraft assigned")
    if not mission.legs:
        raise HTTPException(status_code=400, detail="Mission has no legs")

    aircraft = await db.get(Aircraft, mission.aircraft_id)
    if not aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found")

    body_data = body.model_dump() if body else {}
    fuel_burn_overrides: dict[int, float] = body_data.get("fuel_burn_gal", {}) or {}

    # Try to get the fuel profile for burn estimation
    profile_row = await db.execute(
        select(AircraftFuelProfile).where(
            AircraftFuelProfile.aircraft_id == mission.aircraft_id
        )
    )
    profile = profile_row.scalar_one_or_none()
    if profile:
        cruise_speed_kt = profile.cruise_speed_kt or aircraft.cruise_speed_kt or 180
        cruise_burn_gph = profile.cruise_burn_lph * (JET_A_KG_PER_L / JET_A_KG_PER_GAL)
    else:
        cruise_speed_kt = aircraft.cruise_speed_kt or 180
        cruise_burn_gph = float(aircraft.cruise_fuel_flow_gph or 50)

    # Deterministic L→gal conversion factor (from weight_balance constants)
    L_TO_GAL = JET_A_KG_PER_L / JET_A_KG_PER_GAL

    crew_count = (1 if mission.pilot_in_command else 0) + (1 if mission.second_in_command else 0)
    if crew_count == 0:
        crew_count = 2  # sensible default

    report_rows: list[dict[str, Any]] = []
    totals: dict[str, Any] = {
        "total_passengers": 0,
        "total_cargo_kg": 0.0,
        "legs_ok": 0,
        "legs_warning": 0,
        "legs_over_limit": 0,
    }

    # Track cumulative fuel burn across legs for realistic W&B
    cumulative_fuel_burned_gal = 0.0

    for leg in mission.legs:
        # Tally manifest data for this leg
        pax_count = 0
        pax_weights: list[float] = []
        cargo_kg = 0.0

        for entry in leg.manifest_entries:
            if entry.entry_type == "passenger":
                pax_count += 1
                if entry.weight_kg is not None:
                    pax_weights.append(float(entry.weight_kg))
            elif entry.entry_type in ("cargo", "baggage"):
                if entry.weight_kg is not None:
                    cargo_kg += float(entry.weight_kg)

        # Fuel on board (L → gal)
        fuel_l = leg.fuel_on_board_l or leg.fuel_required_l or 0.0
        fuel_gal = fuel_l * L_TO_GAL

        # Fuel burn for this leg
        fuel_burn_gal = fuel_burn_overrides.get(leg.leg_number)
        if fuel_burn_gal is None:
            if leg.fuel_required_l and leg.fuel_required_l > 0:
                fuel_burn_gal = leg.fuel_required_l * L_TO_GAL
            elif leg.distance_nm and cruise_speed_kt:
                flight_hrs = leg.distance_nm / cruise_speed_kt
                fuel_burn_gal = round(flight_hrs * cruise_burn_gph, 1)
            else:
                fuel_burn_gal = fuel_gal * 0.5  # conservative default

        wb = await calculate_leg_wb(
            aircraft=aircraft,
            origin=leg.departure_airport,
            destination=leg.arrival_airport,
            leg_index=leg.leg_number,
            passenger_count=pax_count,
            passenger_weights=pax_weights or None,
            cargo_kg=cargo_kg,
            fuel_gal=max(0, fuel_gal - cumulative_fuel_burned_gal),
            fuel_burn_gal=fuel_burn_gal,
            taxi_fuel_gal=None,
            crew_count=crew_count,
        )

        # Track fuel consumed for realistic next-leg W&B
        cumulative_fuel_burned_gal += fuel_burn_gal

        wb_dict = wb_to_dict(wb)
        wb_dict["leg_number"] = leg.leg_number
        wb_dict["departure_airport"] = leg.departure_airport
        wb_dict["arrival_airport"] = leg.arrival_airport
        wb_dict["distance_nm"] = leg.distance_nm
        report_rows.append(wb_dict)

        totals["total_passengers"] += pax_count
        totals["total_cargo_kg"] = round(totals["total_cargo_kg"] + cargo_kg, 1)
        if wb.overall_status == "over_limit":
            totals["legs_over_limit"] += 1
        elif wb.overall_status == "warning":
            totals["legs_warning"] += 1
        else:
            totals["legs_ok"] += 1

    flagged = [
        {"leg_number": r["leg_number"], "status": r["overall_status"], "notes": r["notes"]}
        for r in report_rows
        if r["overall_status"] in ("over_limit", "warning")
    ]

    return {
        "mission_id": mission_id,
        "aircraft_tail": aircraft.tail_number,
        "leg_count": len(report_rows),
        "legs": report_rows,
        "summary": {
            **totals,
            "crew_count": crew_count,
            "overall_mission_status": (
                "over_limit" if totals["legs_over_limit"] > 0
                else "warning" if totals["legs_warning"] > 0
                else "ok"
            ),
            "flagged_legs": flagged,
        },
    }


# ── Crew Duty Check ───────────────────────────────────────────


@router.post("/{mission_id}/duty-check")
async def mission_duty_check(
    mission_id: str,
    body: DutyCheckRequest | None = None,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Check FAR 135.267 crew duty time compliance for a mission.

    Reads the mission's assigned crew (PIC / SIC) and all legs with their
    flight times (actual, scheduled, or distance-estimated).  Returns per-crew
    compliance status, mission-level legality, and any violations.

    Optional body fields let you provide historical cumulative flight times
    for more accurate compliance checking.
    """
    mission = await db.get(Mission, mission_id)
    if not mission or mission.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Mission not found")
    if not mission.legs:
        raise HTTPException(status_code=400, detail="Mission has no legs")

    body_data = body.model_dump() if body else {}
    body_crew = body_data.get("crew_members")
    hypothetical_departure = body_data.get("hypothetical_departure")
    is_two_pilot_override = body_data.get("is_two_pilot")

    # ── Compute total flight time ──────────────────────────────
    total_flight_minutes = sum(
        (leg.flight_time_minutes or 0) for leg in mission.legs
    )
    # Fallback to scheduled times when flight_time_minutes is not set
    if total_flight_minutes == 0:
        for leg in mission.legs:
            if leg.scheduled_departure and leg.scheduled_arrival:
                delta = (leg.scheduled_arrival - leg.scheduled_departure).total_seconds()
                total_flight_minutes += int(delta / 60)
    # Last resort: estimate from distance at 180 kt average
    if total_flight_minutes == 0:
        for leg in mission.legs:
            if leg.distance_nm:
                total_flight_minutes += int(leg.distance_nm / 180 * 60)

    flight_time_hrs = round(total_flight_minutes / 60, 2)

    is_two_pilot = (
        is_two_pilot_override
        if is_two_pilot_override is not None
        else bool(mission.pilot_in_command) and bool(mission.second_in_command)
    )

    # ── Build crew list from mission data ──────────────────────
    crew_members: list[dict[str, Any]] | None = None
    if body_crew:
        crew_members = [
            {
                "name": cm.name,
                "role": cm.role,
                "is_pilot": cm.is_pilot,
                "last_duty_end": cm.last_duty_end,
                "flight_time_24hr": cm.flight_time_24hr,
                "flight_time_quarter_hrs": cm.flight_time_quarter_hrs,
                "flight_time_two_quarter_hrs": cm.flight_time_two_quarter_hrs,
                "flight_time_year_hrs": cm.flight_time_year_hrs,
            }
            for cm in body_crew
        ]
    elif mission.pilot_in_command or mission.second_in_command:
        crew_members = []
        if mission.pilot_in_command:
            crew_members.append({
                "name": mission.pilot_in_command,
                "role": "captain",
                "is_pilot": True,
            })
        if mission.second_in_command:
            crew_members.append({
                "name": mission.second_in_command,
                "role": "first_officer",
                "is_pilot": True,
            })

    # Determine departure time
    departure = hypothetical_departure
    if departure is None and mission.legs:
        departure = mission.legs[0].scheduled_departure

    result = await check_crew_duty(
        mission_flight_time_hrs=flight_time_hrs,
        mission_duty_period_hrs=None,
        is_two_pilot=is_two_pilot,
        crew_members=crew_members,
        hypothetical_departure=departure,
    )

    output = duty_check_to_dict(
        result,
        is_two_pilot=is_two_pilot,
        departure_time=departure.isoformat() if departure else None,
    )
    output["mission_id"] = mission_id
    output["total_flight_time_hrs"] = flight_time_hrs
    output["leg_count"] = len(mission.legs)

    return output
