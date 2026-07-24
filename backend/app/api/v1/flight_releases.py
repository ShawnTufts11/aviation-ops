"""
Flight Release API endpoints — the three-gate signoff system.

POST   /api/v1/flight-releases          — create new release (auto-generates FR number)
GET    /api/v1/flight-releases          — list releases (filterable by status, aircraft, date)
GET    /api/v1/flight-releases/:id      — get full release detail
PATCH  /api/v1/flight-releases/:id      — update release fields
POST   /api/v1/flight-releases/:id/sign — sign a gate (maint/pic/dispatch)
GET    /api/v1/flight-releases/:id/pdf  — generate downloadable PDF
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_org_membership
from app.models.flight_release import FlightRelease, ReleaseStatus, MissionCapability
from app.models.aircraft import Aircraft
from app.models.user import User

router = APIRouter(prefix="/flight-releases", tags=["flight-releases"])


# ── Schemas ──────────────────────────────────────────────────────────────


class GripeItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    severity: str = "yellow"  # red / yellow / green
    status: str = "open"  # open / deferred / resolved
    reported_by: str | None = None
    reported_at: str | None = None  # ISO datetime
    resolved_by: str | None = None
    resolved_at: str | None = None


class WaypointItem(BaseModel):
    ident: str
    lat: float = 0.0
    lon: float = 0.0
    course: float | None = None
    distance_nm: float | None = None
    eta: str | None = None  # HH:MM Z
    fuel_remaining_lbs: float | None = None


class FuelPlan(BaseModel):
    ramp_lbs: float = 0
    trip_lbs: float = 0
    contingency_lbs: float = 0
    alternate_lbs: float = 0
    final_reserve_lbs: float = 0
    taxy_lbs: float = 0
    fuel_on_arrival_lbs: float = 0
    legal: bool = False
    notes: str | None = None


class WeatherBrief(BaseModel):
    departure: dict[str, Any] = Field(default_factory=dict)
    destination: dict[str, Any] = Field(default_factory=dict)
    alternate: dict[str, Any] = Field(default_factory=dict)
    route_weather: list[dict[str, Any]] = Field(default_factory=list)
    sigmets: list[str] = Field(default_factory=list)
    winds_aloft: str | None = None
    go_nogo: str | None = None  # recommended / hold / caution


class NOTAMSet(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    tfr_active: list[dict[str, Any]] = Field(default_factory=list)


class ReleaseCreate(BaseModel):
    organization_id: str
    aircraft_id: str
    mission_name: str = ""
    origin_icao: str
    dest_icao: str
    alternate_icao: str | None = None
    legs: list[WaypointItem] = Field(default_factory=list)
    departure_time: str | None = None  # ISO datetime
    pic_id: str | None = None
    sic_id: str | None = None


class ReleaseUpdate(BaseModel):
    mission_name: str | None = None
    departure_time: str | None = None
    est_enroute_minutes: int | None = None
    pic_id: str | None = None
    sic_id: str | None = None
    fuel_plan: FuelPlan | None = None
    weather_brief: WeatherBrief | None = None
    notams: NOTAMSet | None = None
    destination_risk: str | None = None
    ground_security: str | None = None
    customs_status: str | None = None
    notes: str | None = None


class SignRequest(BaseModel):
    gate: str  # "maintenance" | "pic" | "pic_reject" | "dispatcher"
    signer_name: str
    signer_title: str | None = None
    rejection_reason: str | None = None


# ── Helpers ──────────────────────────────────────────────────────────────


def _release_to_dict(r: FlightRelease) -> dict[str, Any]:
    """Convert a FlightRelease ORM object to a JSON-safe dict."""
    return {
        "id": r.id,
        "release_number": r.release_number,
        "status": r.status.value if r.status else "draft",
        "organization_id": r.organization_id,
        "aircraft_id": r.aircraft_id,
        "mission_name": r.mission_name or "",
        "origin_icao": r.origin_icao,
        "dest_icao": r.dest_icao,
        "alternate_icao": r.alternate_icao or "",
        "legs": r.route_waypoints if r.route_waypoints else [],
        "departure_time": r.departure_time.isoformat() if r.departure_time else None,
        "est_enroute_minutes": r.est_enroute_minutes,
        "pic_id": r.pic_id,
        "sic_id": r.sic_id,
        "pic_duty_start": r.pic_duty_start.isoformat() if r.pic_duty_start else None,
        "pic_duty_end": r.pic_duty_end.isoformat() if r.pic_duty_end else None,
        "sic_duty_start": r.sic_duty_start.isoformat() if r.sic_duty_start else None,
        "sic_duty_end": r.sic_duty_end.isoformat() if r.sic_duty_end else None,
        "duty_compliant": False,  # computed field — not stored on model
        "fuel_plan": {
            "ramp_lbs": r.ramp_fuel_lbs,
            "trip_lbs": r.trip_fuel_lbs,
            "contingency_lbs": r.contingency_fuel_lbs,
            "alternate_lbs": r.alternate_fuel_lbs,
            "final_reserve_lbs": r.reserve_fuel_lbs,
            "fuel_on_arrival_lbs": r.arrival_fuel_lbs,
            "legal": r.fuel_legal,
        },
        "weather_brief": r.weather_brief or {},
        "notams": r.notam_refs or [],
        "safe_for_flight": r.safe_for_flight,
        "safe_for_flight_signed_by": r.safe_for_flight_signed_by,
        "safe_for_flight_signed_at": r.safe_for_flight_signed_at.isoformat() if r.safe_for_flight_signed_at else None,
        "mission_capability": r.mission_capability.value if r.mission_capability else "full",
        "mission_capability_restrictions": (
            r.maintenance_restrictions
            if r.maintenance_restrictions
            else []
        ),
        "gripes_open": r.gripes_open or [],
        "gripes_deferred": r.gripes_deferred or [],
        "pic_accepted": r.pic_accepted,
        "pic_accepted_at": r.pic_accepted_at.isoformat() if r.pic_accepted_at else None,
        "pic_signed_at": r.pic_signed_at.isoformat() if r.pic_signed_at else None,
        "pic_rejected": r.pic_rejected,
        "pic_rejected_at": r.pic_rejected_at.isoformat() if r.pic_rejected_at else None,
        "pic_rejected_by": r.pic_rejected_by,
        "pic_rejection_reason": r.pic_rejection_reason,
        "dispatcher_signed_at": r.dispatcher_signed_at.isoformat() if r.dispatcher_signed_at else None,
        "reviewed_by": r.reviewed_by,
        "destination_risk": r.destination_risk,
        "ground_security": r.ground_security,
        "overwater_legs": r.overwater_legs,
        "etp_waypoint": r.etp_waypoint,
        "customs_status": r.customs_status,
        "notes": "",  # notes field not stored on model — use mission_name
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        "amended_at": r.amended_at.isoformat() if r.amended_at else None,
        "closed_at": r.closed_at.isoformat() if r.closed_at else None,
    }


# ── Endpoints ────────────────────────────────────────────────────────────


@router.get("")
async def list_releases(
    status_filter: str | None = Query(None, alias="status"),
    aircraft_id: str | None = Query(None),
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List all flight releases, optionally filtered."""
    from sqlalchemy import select as sql_select

    org_id = current_user.organization_id
    stmt = sql_select(FlightRelease).where(
        FlightRelease.organization_id == org_id
    ).order_by(FlightRelease.created_at.desc())

    if status_filter:
        stmt = stmt.where(FlightRelease.status == status_filter)
    if aircraft_id:
        stmt = stmt.where(FlightRelease.aircraft_id == aircraft_id)

    result = await db.execute(stmt)
    releases = result.scalars().all()
    return {
        "releases": [_release_to_dict(r) for r in releases],
        "total": len(releases),
    }


@router.get("/{release_id}")
async def get_release(
    release_id: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get full flight release detail."""
    result = await db.execute(
        select(FlightRelease).where(
            FlightRelease.id == release_id,
            FlightRelease.organization_id == current_user.organization_id,
        )
    )
    release = result.scalar_one_or_none()
    if not release:
        raise HTTPException(status_code=404, detail="Flight release not found")
    return {"release": _release_to_dict(release)}


@router.post("", status_code=201)
async def create_release(
    body: ReleaseCreate,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new flight release with auto-generated release number."""
    # Generate release number: FR-YYYY-NNN
    today = date.today()
    year = today.year
    # Count existing releases this year for sequential numbering
    count_stmt = select(FlightRelease).where(
        FlightRelease.organization_id == body.organization_id,
        FlightRelease.release_number.like(f"FR-{year}-%"),
    )
    count_result = await db.execute(count_stmt)
    existing = count_result.scalars().all()
    seq = len(existing) + 1
    release_number = f"FR-{year}-{seq:04d}"

    legs_json = json.dumps([l.model_dump() for l in body.legs]) if body.legs else "[]"

    release = FlightRelease(
        id=str(uuid.uuid4()),
        release_number=release_number,
        organization_id=body.organization_id,
        aircraft_id=body.aircraft_id,
        mission_name=body.mission_name or "",
        origin_icao=body.origin_icao,
        dest_icao=body.dest_icao,
        alternate_icao=body.alternate_icao or "",
        route_waypoints=json.loads(legs_json) if body.legs else [],
        departure_time=datetime.fromisoformat(body.departure_time.replace("Z", "+00:00"))
        if body.departure_time else None,
        pic_id=body.pic_id,
        sic_id=body.sic_id,
        status=ReleaseStatus.DRAFT,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(release)
    await db.commit()
    await db.refresh(release)
    return {"release": _release_to_dict(release)}


@router.patch("/{release_id}")
async def update_release(
    release_id: str,
    body: ReleaseUpdate,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update fields on an existing release."""
    result = await db.execute(
        select(FlightRelease).where(
            FlightRelease.id == release_id,
            FlightRelease.organization_id == current_user.organization_id,
        )
    )
    release = result.scalar_one_or_none()
    if not release:
        raise HTTPException(status_code=404, detail="Flight release not found")

    updates = {}
    if body.mission_name is not None:
        updates["mission_name"] = body.mission_name
    if body.departure_time is not None:
        updates["departure_time"] = datetime.fromisoformat(body.departure_time.replace("Z", "+00:00"))
    if body.est_enroute_minutes is not None:
        updates["est_enroute_minutes"] = body.est_enroute_minutes
    if body.pic_id is not None:
        updates["pic_id"] = body.pic_id
    if body.sic_id is not None:
        updates["sic_id"] = body.sic_id
    if body.fuel_plan is not None:
        updates["fuel_plan_json"] = body.fuel_plan.model_dump_json()
    if body.weather_brief is not None:
        updates["weather_brief_json"] = body.weather_brief.model_dump_json()
    if body.notams is not None:
        updates["notams_json"] = body.notams.model_dump_json()
    if body.destination_risk is not None:
        updates["destination_risk"] = body.destination_risk
    if body.ground_security is not None:
        updates["ground_security"] = body.ground_security
    if body.customs_status is not None:
        updates["customs_status"] = body.customs_status
    if body.notes is not None:
        updates["notes"] = body.notes

    updates["updated_at"] = datetime.now(timezone.utc)
    await db.execute(
        update(FlightRelease).where(FlightRelease.id == release_id).values(**updates)
    )
    await db.commit()

    # Re-fetch
    fresh = await db.execute(select(FlightRelease).where(FlightRelease.id == release_id))
    release = fresh.scalar_one()
    return {"release": _release_to_dict(release)}


@router.post("/{release_id}/sign")
async def sign_release(
    release_id: str,
    body: SignRequest,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Sign one of the three gates on a flight release."""
    result = await db.execute(
        select(FlightRelease).where(
            FlightRelease.id == release_id,
            FlightRelease.organization_id == current_user.organization_id,
        )
    )
    release = result.scalar_one_or_none()
    if not release:
        raise HTTPException(status_code=404, detail="Flight release not found")

    now = datetime.now(timezone.utc)
    updates: dict[str, Any] = {"updated_at": now}

    if body.gate == "maintenance":
        updates["safe_for_flight"] = True
        updates["safe_for_flight_signed_by"] = body.signer_name
        updates["safe_for_flight_signed_at"] = now
    elif body.gate == "pic":
        # Reset any prior rejection state when PIC accepts
        updates["pic_accepted"] = True
        updates["pic_accepted_at"] = now
        updates["pic_signed_at"] = now
        updates["pic_rejected"] = False
        updates["pic_rejected_at"] = None
        updates["pic_rejected_by"] = None
        updates["pic_rejection_reason"] = None
    elif body.gate == "pic_reject":
        updates["pic_accepted"] = False
        updates["pic_accepted_at"] = None
        updates["pic_rejected"] = True
        updates["pic_rejected_at"] = now
        updates["pic_rejected_by"] = body.signer_name
        updates["pic_rejection_reason"] = body.rejection_reason or "No reason provided"
        updates["safe_for_flight"] = False
        updates["safe_for_flight_signed_by"] = None
        updates["safe_for_flight_signed_at"] = None
        updates["status"] = ReleaseStatus.IN_MAINTENANCE
    elif body.gate == "dispatcher":
        updates["dispatcher_signed_at"] = now
        updates["reviewed_by"] = body.signer_name
        updates["status"] = ReleaseStatus.RELEASED
    else:
        raise HTTPException(status_code=400, detail=f"Unknown gate: {body.gate}")

    await db.execute(
        update(FlightRelease).where(FlightRelease.id == release_id).values(**updates)
    )
    await db.commit()

    fresh = await db.execute(select(FlightRelease).where(FlightRelease.id == release_id))
    release = fresh.scalar_one()
    return {"release": _release_to_dict(release), "message": f"{body.gate} gate signed"}


@router.get("/{release_id}/pdf")
async def get_release_pdf(
    release_id: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate and return a downloadable flight release PDF.

    For V1, returns the release data in a format that can be rendered as PDF
    on the client side using the browser's print function. Future versions
    will use a proper PDF generation library.
    """
    result = await db.execute(
        select(FlightRelease).where(
            FlightRelease.id == release_id,
            FlightRelease.organization_id == current_user.organization_id,
        )
    )
    release = result.scalar_one_or_none()
    if not release:
        raise HTTPException(status_code=404, detail="Flight release not found")

    return {
        "release": _release_to_dict(release),
        "pdf_hint": "Open this page in your browser and use Print → Save as PDF",
    }
