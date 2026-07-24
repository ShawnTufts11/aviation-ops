"""eAPIS export — generate pre-filled US Customs manifest from mission data."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_org_membership
from app.models.aircraft import Aircraft
from app.models.crew import CrewMember
from app.models.flight import Flight
from app.models.mission import FlightLeg, ManifestEntry, Mission
from app.models.organization import Organization
from app.models.user import User

router = APIRouter(prefix="/export", tags=["export"])

COUNTRY_NAMES = {
    "US": "United States", "BS": "Bahamas", "HT": "Haiti",
    "DO": "Dominican Republic", "CU": "Cuba", "CA": "Canada",
    "GB": "United Kingdom", "FR": "France",
}


@router.get("/eapis/{mission_id}")
async def export_eapis(
    mission_id: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate a pre-filled eAPIS manifest for a mission.

    Returns structured JSON with all fields needed for US Customs
    eAPIS submission. Ready for copy-to-clipboard or printable view.
    """
    mission = await db.get(Mission, mission_id)
    if not mission or mission.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Mission not found")

    org = await db.get(Organization, mission.organization_id)
    ac = await db.get(Aircraft, mission.aircraft_id) if mission.aircraft_id else None

    # Load legs with manifest
    legs_result = await db.execute(
        select(FlightLeg).where(
            FlightLeg.mission_id == mission_id
        ).order_by(FlightLeg.leg_number)
    )
    legs = legs_result.scalars().all()

    if not legs:
        raise HTTPException(status_code=400, detail="Mission has no legs")

    # Gather passengers per leg with boarding/deplaning context
    leg_passengers: dict[int, list[dict]] = {}
    all_passengers: dict[str, dict] = {}
    for leg in legs:
        lp = []
        for entry in leg.manifest_entries:
            if entry.entry_type != "passenger":
                continue
            pdata = {
                "full_name": entry.full_name,
                "date_of_birth": entry.date_of_birth.isoformat() if entry.date_of_birth else None,
                "gender": entry.gender,
                "nationality": entry.nationality,
                "passport_number": entry.passport_number,
                "passport_expiry": entry.passport_expiry.isoformat() if entry.passport_expiry else None,
                "id_number": entry.id_number,
                "weight_kg": entry.weight_kg,
                "boarding_leg": entry.boarding_leg_number,
                "deplaning_leg": entry.deplaning_leg_number,
            }
            lp.append(pdata)
            key = entry.full_name
            if key not in all_passengers:
                all_passengers[key] = pdata
        leg_passengers[leg.leg_number] = lp

    # Detect passenger changes: which passengers are unique to each leg
    leg_changes: dict[int, dict[str, list[str]]] = {}
    prev_leg_passengers: set[str] = set()
    for leg in legs:
        current_set = {p["full_name"] for p in leg_passengers.get(leg.leg_number, [])}
        boarded = current_set - prev_leg_passengers
        deplaned = prev_leg_passengers - current_set
        if boarded or deplaned:
            leg_changes[leg.leg_number] = {
                "boarded": sorted(boarded),
                "deplaned": sorted(deplaned),
            }
        prev_leg_passengers = current_set

    # Get crew
    crew_info: list[dict] = []
    if mission.pilot_in_command:
        pic = await db.get(CrewMember, mission.pilot_in_command)
        if pic:
            crew_info.append({
                "role": "PIC",
                "full_name": f"{pic.first_name} {pic.last_name}",
                "license": pic.license_number,
            })
    if mission.second_in_command:
        sic = await db.get(CrewMember, mission.second_in_command)
        if sic:
            crew_info.append({
                "role": "SIC",
                "full_name": f"{sic.first_name} {sic.last_name}",
                "license": sic.license_number,
            })

    # Emergency contact
    emergency = {
        "name": org.settings.get("emergency_contact_name") if org else None,
        "phone": org.settings.get("emergency_contact_phone") if org else None,
    }

    # Build legs for eAPIS
    eapis_legs = []
    for leg in legs:
        dest_country = _icao_to_country(leg.arrival_airport)
        leg_pax = leg_passengers.get(leg.leg_number, [])
        entry = {
            "leg": leg.leg_number,
            "departure": {
                "airport": leg.departure_airport,
                "date": leg.scheduled_departure.strftime("%Y-%m-%d") if leg.scheduled_departure else None,
                "time_utc": leg.scheduled_departure.strftime("%H:%M") if leg.scheduled_departure else None,
            },
            "arrival": {
                "airport": leg.arrival_airport,
                "date": leg.scheduled_arrival.strftime("%Y-%m-%d") if leg.scheduled_arrival else None,
                "time_utc": leg.scheduled_arrival.strftime("%H:%M") if leg.scheduled_arrival else None,
            },
            "destination_country": dest_country,
            "passenger_count": len(leg_pax),
            "passengers": [p["full_name"] for p in leg_pax],
        }
        change = leg_changes.get(leg.leg_number)
        if change:
            entry["changes"] = change
        eapis_legs.append(entry)

    return {
        "manifest": {
            "generated": datetime.now(timezone.utc).isoformat(),
            "eapis_version": "1.0",
            "status": "ready_for_review",
        },
        "flight": {
            "aircraft_tail": ac.tail_number if ac else None,
            "aircraft_make": ac.make if ac else None,
            "aircraft_model": ac.model if ac else None,
            "registration_country": ac.country_reg if ac else "BS",
            "operator": org.name if org else None,
            "operator_address": org.settings.get("address") if org else None,
            "flight_number": f"MISSION-{mission_id[:8].upper()}",
            "call_sign": ac.tail_number if ac else None,
        },
        "itinerary": eapis_legs,
        "crew": crew_info,
        "passengers": list(all_passengers.values()),
        "emergency_contact": emergency,
        "total_passengers": len(all_passengers),
        "total_crew": len(crew_info),
        "notes": mission.notes,
    }


def _icao_to_country(icao: str) -> str:
    """Simple ICAO prefix to country mapping."""
    prefix = icao[:2].upper()
    mapping = {
        "MY": "Bahamas", "MT": "Haiti", "MD": "Dominican Republic",
        "MU": "Cuba", "MK": "Jamaica", "MW": "Cayman Islands",
        "MP": "Panama", "MB": "Turks and Caicos", "K": "United States",
        "C": "Canada", "M": "Unknown Caribbean",
    }
    return mapping.get(prefix, "Unknown")


@router.get("/customs/{mission_id}")
async def export_customs(
    mission_id: str,
    country: str | None = None,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate country-specific customs form data.

    If *country* is omitted, returns all applicable forms for all legs.
    """
    mission = await db.get(Mission, mission_id)
    if not mission or mission.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Mission not found")

    legs_result = await db.execute(
        select(FlightLeg).where(
            FlightLeg.mission_id == mission_id
        ).order_by(FlightLeg.leg_number)
    )
    legs = legs_result.scalars().all()

    # Get unique countries visited
    countries = set()
    for leg in legs:
        countries.add(_icao_to_country(leg.arrival_airport))
        if leg.departure_airport:
            countries.add(_icao_to_country(leg.departure_airport))

    def _forms_for_country(c: str) -> list[dict]:
        """Which forms are needed for each country."""
        forms = {
            "Bahamas": [
                {"form": "Bahamas Immigration Card", "required": True, "per_passenger": True},
                {"form": "Bahamas Customs Declaration", "required": True, "per_passenger": False},
                {"form": "General Declaration", "required": True, "per_passenger": False},
            ],
            "Haiti": [
                {"form": "Haiti Landing Permit", "required": True, "per_passenger": False},
                {"form": "Haiti Passenger Manifest", "required": True, "per_passenger": False},
                {"form": "Customs Declaration", "required": True, "per_passenger": True},
            ],
            "United States": [
                {"form": "eAPIS Manifest", "required": True, "per_passenger": False},
                {"form": "US Customs Declaration (CBP Form 6059B)", "required": True, "per_passenger": True},
                {"form": "General Declaration", "required": True, "per_passenger": False},
            ],
            "Dominican Republic": [
                {"form": "DR Landing Permit", "required": True, "per_passenger": False},
                {"form": "DR Tourist Card / E-Ticket", "required": True, "per_passenger": True},
                {"form": "Customs Declaration", "required": True, "per_passenger": True},
            ],
        }
        return forms.get(c, [{"form": "Check local requirements", "required": True, "per_passenger": False}])

    if country:
        result = {country: _forms_for_country(country)}
    else:
        result = {c: _forms_for_country(c) for c in sorted(countries)}

    return {
        "mission_id": mission_id,
        "countries": sorted(countries),
        "forms": result,
        "note": "Pilot must verify current requirements before each flight",
    }
