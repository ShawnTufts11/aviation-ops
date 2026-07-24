"""
Route planner — the integration layer that ties aircraft performance, airport
data, weight & balance, and crew duty compliance into a complete mission
planning package.

This is the core "brain" that the mission builder calls. Given an aircraft
and a list of legs, it returns:
  - Per-leg: distance, block time, fuel burn, capabilities check
  - Per-destination: FBOs, hotels, fuel prices, customs, MRO, restrictions
  - Weight & Balance: per-leg loading analysis
  - Crew Duty Time: FAR 135.267 compliance check
  - Mission totals: time, fuel, distance, critical flags
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.services.distance import haversine_radians
from app.services.flight_performance import (
    estimate_block,
    check_capabilities,
    BlockEstimate,
    AircraftCapabilities,
)
from app.services.weight_balance import (
    calculate_leg_wb,
    wb_to_dict,
    WeightBalanceReport,
)
from app.services.crew_duty import (
    check_crew_duty,
    duty_check_to_dict,
    CrewCheckResult,
)
from app.services.weather import get_metar, get_taf, get_notams, weather_to_dict

if TYPE_CHECKING:
    from app.models.aircraft import Aircraft
    from app.models.airport import Airport


@dataclass
class LegPlan:
    """Complete planning data for a single route leg."""

    leg_index: int
    origin_icao: str
    destination_icao: str

    # Airport coordinates
    origin_lat: float = 0.0
    origin_lon: float = 0.0
    dest_lat: float = 0.0
    dest_lon: float = 0.0

    # Airport info
    origin_name: str = ""
    destination_name: str = ""
    destination_city: str = ""

    # Route math
    distance_nm: float = 0.0
    block: BlockEstimate | None = None
    capabilities: AircraftCapabilities | None = None
    wb: WeightBalanceReport | None = None

    # Destination intelligence
    fbo_count: int = 0
    fbo_options: list[dict] = field(default_factory=list)
    hotel_count: int = 0
    hotel_options: list[dict] = field(default_factory=list)
    fuel_price_jet_a: float | None = None
    fuel_price_avgas: float | None = None
    has_customs: bool = False
    customs_hours: str = ""
    has_night_ops: bool = False
    has_mro: bool = False
    maintenance_notes: str = ""
    operating_hours: str = ""
    has_landing_permit: bool = False
    has_overflight_permit: bool = False
    restrictions: list[dict] = field(default_factory=list)
    notes: str = ""
    weather: dict | None = None
    notams: list[dict] = field(default_factory=list)

    # Estimated cash costs (at destination)
    estimated_cash_needed: float = 0.0

    # Flags
    flags: list[str] = field(default_factory=list)
    is_ok: bool = True


@dataclass
class RoutePlan:
    """Complete multi-leg route plan."""

    aircraft_tail: str = ""
    aircraft_type: str = ""
    aircraft_cruise: int = 0
    aircraft_range: int = 0

    legs: list[LegPlan] = field(default_factory=list)
    crew_duty: CrewCheckResult | None = None

    total_distance_nm: float = 0.0
    total_block_time_min: int = 0
    total_block_hours: float = 0.0
    total_fuel_gal: float = 0.0
    total_flight_time_min: int = 0

    critical_flags: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    overnight_required: bool = False
    crew_swap_required: bool = False
    fuel_stop_required: bool = False
    weather_degraded: bool = False  # One or more legs have unavailable weather
    adsb_degraded: bool = False     # ADS-B tracking data unavailable

    # Estimated total cash needed across all legs
    estimated_total_cash_needed: float = 0.0


def _flag(leg: LegPlan, message: str, critical: bool = False) -> None:
    """Add a flag to a leg plan."""
    leg.flags.append(message)
    if critical:
        leg.is_ok = False


async def plan_route(
    aircraft: Aircraft,
    legs: list[tuple[Airport, Airport, int | None]],
    passenger_counts: list[int] | None = None,
    cargo_kg: float = 0.0,
    crew_count: int = 2,
    is_two_pilot: bool = True,
    crew_members: list[dict[str, Any]] | None = None,
) -> RoutePlan:
    """
    Plan a multi-leg route for a given aircraft.

    Args:
        aircraft: The Aircraft model instance (with performance data)
        legs: List of (origin_airport, destination_airport, cruise_altitude_ft) tuples
        passenger_counts: Optional passenger count per leg (for W&B)
        cargo_kg: Cargo weight in kg (same for all legs)
        crew_count: Number of crew
        is_two_pilot: True for 2-pilot crew, False for 1-pilot
        crew_members: Optional crew info for duty time checks

    Returns:
        RoutePlan with per-leg details, mission totals, W&B, and crew duty
    """
    plan = RoutePlan(
        aircraft_tail=aircraft.tail_number,
        aircraft_type=f"{aircraft.make} {aircraft.model}",
        aircraft_cruise=aircraft.cruise_speed_kt or 0,
        aircraft_range=aircraft.max_range_with_reserves_nm or (aircraft.range_nm or 0),
    )

    total_dist = 0.0
    total_block_min = 0
    total_fuel = 0.0
    total_flight_min = 0
    remaining_fuel_gal = 0.0  # Track cumulative fuel across legs

    for idx, (origin, destination, cruise_alt) in enumerate(legs):
        pax_count = (passenger_counts or [0] * len(legs))[idx]

        leg = LegPlan(
            leg_index=idx + 1,
            origin_icao=origin.icao_code,
            destination_icao=destination.icao_code,
            origin_name=origin.name,
            destination_name=destination.name,
            destination_city=destination.city or "",

            # Coordinates
            origin_lat=origin.latitude,
            origin_lon=origin.longitude,
            dest_lat=destination.latitude,
            dest_lon=destination.longitude,
        )

        # ── Distance ──────────────────────────────────────────────────────
        dist_nm, _, _ = haversine_radians(
            origin.latitude, origin.longitude,
            destination.latitude, destination.longitude,
        )
        leg.distance_nm = round(dist_nm, 1)
        total_dist += dist_nm

        # ── Block time & fuel ─────────────────────────────────────────────
        block = estimate_block(aircraft, origin, destination, cruise_alt)
        leg.block = block
        total_block_min += block.total_block_time_min
        total_fuel += block.total_fuel_gal

        flight_min = block.climb_time_min + block.cruise_time_min + block.descent_time_min
        total_flight_min += flight_min

        # ── Capabilities check ────────────────────────────────────────────
        caps = check_capabilities(aircraft, origin, destination)
        leg.capabilities = caps

        if not block.within_range:
            _flag(leg, block.note, critical=True)
            plan.fuel_stop_required = True

        if not caps.can_operate_leg:
            for r in caps.restrictions:
                _flag(leg, r, critical=True)

        if caps.overwater_required and not caps.overwater_capable:
            _flag(leg, "Aircraft not equipped for overwater", critical=True)

        if caps.icing_possible and not caps.icing_certified:
            _flag(leg, "Known icing possible — aircraft not certified", critical=False)
            plan.warnings.append(f"Leg {leg.leg_index}: icing risk")

        if not caps.rnp_capable and caps.rnp_required:
            _flag(leg, f"RNP required at {destination.icao_code} — not RNP capable", critical=True)

        # ── Weight & Balance ──────────────────────────────────────────────
        # Track cumulative fuel burn across legs for realistic W&B
        if leg.leg_index == 1:
            remaining_fuel_gal = block.total_fuel_gal  # First leg: full fuel load

        leg_burn_gal = block.cruise_fuel_gal + block.climb_fuel_gal + block.descent_fuel_gal
        
        wb = await calculate_leg_wb(
            aircraft=aircraft,
            origin=origin.icao_code,
            destination=destination.icao_code,
            leg_index=leg.leg_index,
            passenger_count=pax_count,
            cargo_kg=cargo_kg,
            fuel_gal=remaining_fuel_gal,
            fuel_burn_gal=leg_burn_gal,
            taxi_fuel_gal=block.taxi_fuel_gal,
            crew_count=crew_count,
        )
        leg.wb = wb
        
        # Subtract this leg's burn for next leg's starting fuel
        remaining_fuel_gal = max(0, remaining_fuel_gal - leg_burn_gal)

        if wb.overall_status == "over_limit":
            for note in wb.notes:
                _flag(leg, f"W&B: {note}", critical=True)
        elif wb.overall_status == "warning":
            for note in wb.notes:
                _flag(leg, f"W&B: {note}", critical=False)

        # ── Destination intelligence ──────────────────────────────────────
        leg.fbo_options = destination.fbo_options or []
        leg.fbo_count = len(leg.fbo_options)
        leg.hotel_options = destination.hotel_options or []
        leg.hotel_count = len(leg.hotel_options)
        leg.fuel_price_jet_a = destination.fuel_price_jet_a_usd
        leg.fuel_price_avgas = destination.fuel_price_avgas_usd
        leg.has_customs = destination.has_customs
        leg.customs_hours = destination.customs_hours or ""
        leg.has_night_ops = destination.has_night_ops
        leg.operating_hours = destination.operating_hours or ""
        leg.has_landing_permit = destination.has_landing_permit_required
        leg.has_overflight_permit = destination.has_overflight_permit_required
        leg.restrictions = destination.restrictions or []
        leg.notes = destination.notes or ""

        if destination.maintenance_capability:
            mro = destination.maintenance_capability
            leg.has_mro = mro.get("on_site_mro", False)
            if mro.get("aircraft_types"):
                leg.maintenance_notes = f"Supports: {', '.join(mro['aircraft_types'])}"
            if mro.get("notes"):
                leg.maintenance_notes = leg.maintenance_notes or mro["notes"]

        # ── Per-leg flags ─────────────────────────────────────────────────
        if destination.has_landing_permit_required:
            _flag(leg, f"Landing permit required at {destination.icao_code}", critical=True)
        if destination.has_overflight_permit_required:
            _flag(leg, f"Overflight permit for {destination.country_code} airspace", critical=True)
        if not destination.has_night_ops:
            _flag(leg, f"No night ops at {destination.icao_code}", critical=True)
        if destination.operating_hours and "sunrise" in destination.operating_hours.lower():
            _flag(leg, f"Limited hours: {destination.operating_hours}", critical=False)
        if not destination.has_jet_a and not destination.has_avgas:
            _flag(leg, f"No fuel at {destination.icao_code}", critical=True)
        if not destination.has_jet_a and aircraft.cruise_fuel_flow_gph:
            _flag(leg, f"No Jet-A at {destination.icao_code}", critical=True)

        # ── Estimated cash needed (landing + parking + handling + customs) ─
        leg.estimated_cash_needed = round(
            (destination.landing_fee_usd or 0)
            + (destination.overnight_parking_usd or 0)
            + (destination.handling_fee_usd or 0)
            + (destination.customs_fee_usd or 0),
            2,
        )

        for r in leg.restrictions:
            if r.get("type") == "security":
                _flag(leg, f"SECURITY: {r['description']}", critical=False)

        # ── Weather ──────────────────────────────────────────────────────
        wx = await get_metar(destination.icao_code)
        leg.weather = weather_to_dict(wx)
        if wx.error:
            _flag(leg, f"Weather data unavailable for {destination.icao_code}", critical=False)
            plan.warnings.append(f"Weather degraded: {destination.icao_code} — {wx.error[:60]}")
            plan.weather_degraded = True

        # ── NOTAMs ──────────────────────────────────────────────────────
        leg.notams = await get_notams(destination.icao_code)
        if leg.notams:
            leg.flags.append(f"{len(leg.notams)} NOTAM(s) at {destination.icao_code}")

        if leg.block and leg.block.total_block_time_min > 480:
            _flag(leg, "Leg exceeds 8hr — crew rest required", critical=True)
            plan.overnight_required = True

        plan.legs.append(leg)

    # ── Mission totals ────────────────────────────────────────────────────
    plan.total_distance_nm = round(total_dist, 1)
    plan.total_block_time_min = total_block_min
    plan.total_block_hours = round(total_block_min / 60, 2)
    plan.total_fuel_gal = round(total_fuel, 1)
    plan.total_flight_time_min = total_flight_min
    plan.estimated_total_cash_needed = round(
        sum(leg.estimated_cash_needed for leg in plan.legs), 2
    )

    # ── Crew duty time ────────────────────────────────────────────────────
    plan.crew_duty = await check_crew_duty(
        mission_flight_time_hrs=round(total_flight_min / 60, 2),
        is_two_pilot=is_two_pilot,
        crew_members=crew_members,
    )

    if plan.crew_duty and not plan.crew_duty.mission_legal:
        for v in plan.crew_duty.mission_violations:
            plan.critical_flags.append(f"CREW DUTY: {v}")

    # ── Mission-level flags ───────────────────────────────────────────────
    if plan.total_block_hours > 12:
        plan.overnight_required = True
        plan.critical_flags.append(
            f"Mission ({plan.total_block_hours}hrs) exceeds 12hr — overnight required"
        )

    if plan.total_block_hours > 8:
        plan.crew_swap_required = True
        if not any("crew swap" in f.lower() for f in plan.critical_flags):
            plan.critical_flags.append(
                f"Mission exceeds 8hr — crew swap recommended"
            )

    if plan.fuel_stop_required:
        plan.warnings.append("Fuel stop required — insufficient range for non-stop mission")

    return plan


def _is_daylight_leg(leg: LegPlan, destination: Airport) -> bool:
    """Conservative night-arrival assumption. Replace with sunrise/sunset calc."""
    return False


def route_plan_to_dict(plan: RoutePlan) -> dict[str, Any]:
    """Convert a RoutePlan dataclass tree to a JSON-serializable dict."""
    return {
        "aircraft": {
            "tail_number": plan.aircraft_tail,
            "type": plan.aircraft_type,
            "cruise_speed_kt": plan.aircraft_cruise,
            "max_range_with_reserves_nm": plan.aircraft_range,
        },
        "legs": [
            {
                "leg": leg.leg_index,
                "origin": leg.origin_icao,
                "destination": leg.destination_icao,
                "origin_lat": leg.origin_lat,
                "origin_lon": leg.origin_lon,
                "dest_lat": leg.dest_lat,
                "dest_lon": leg.dest_lon,
                "origin_name": leg.origin_name,
                "destination_name": leg.destination_name,
                "destination_city": leg.destination_city,
                "distance_nm": leg.distance_nm,
                "block_time_min": leg.block.total_block_time_min if leg.block else 0,
                "block_time_hrs": leg.block.total_block_hours if leg.block else 0.0,
                "fuel_gal": leg.block.total_fuel_gal if leg.block else 0.0,
                "within_range": leg.block.within_range if leg.block else True,
                "note": leg.block.note if leg.block else "",
                "capabilities_ok": leg.capabilities.can_operate_leg if leg.capabilities else True,
                "capability_restrictions": leg.capabilities.restrictions if leg.capabilities else [],
                "weight_balance": wb_to_dict(leg.wb) if leg.wb else None,
                "flags": leg.flags,
                "is_ok": leg.is_ok,
                "destination_intel": {
                    "fbo_count": leg.fbo_count,
                    "fbo_options": [
                        {
                            "name": f["name"],
                            "phone": f.get("phone", ""),
                            "fuel_price_jet_a": f.get("fuel_prices", {}).get("jet_a"),
                            "fuel_price_avgas": f.get("fuel_prices", {}).get("avgas"),
                            "services": f.get("services", []),
                        }
                        for f in leg.fbo_options
                    ],
                    "hotel_count": leg.hotel_count,
                    "hotel_options": [
                        {
                            "name": h["name"],
                            "distance_miles": h.get("distance_miles"),
                            "shuttle": h.get("shuttle", False),
                            "phone": h.get("phone", ""),
                            "crew_rate": h.get("crew_rate", False),
                        }
                        for h in leg.hotel_options
                    ],
                    "fuel_price_jet_a": leg.fuel_price_jet_a,
                    "fuel_price_avgas": leg.fuel_price_avgas,
                    "has_customs": leg.has_customs,
                    "customs_hours": leg.customs_hours,
                    "has_night_ops": leg.has_night_ops,
                    "has_mro": leg.has_mro,
                    "maintenance_notes": leg.maintenance_notes,
                    "operating_hours": leg.operating_hours,
                    "landing_permit_required": leg.has_landing_permit,
                    "overflight_permit_required": leg.has_overflight_permit,
                    "restrictions": leg.restrictions,
                    "notes": leg.notes,
                    "weather": leg.weather,
                    "notams": leg.notams[:10],
                },
                "estimated_cash_needed": leg.estimated_cash_needed,
            }
            for leg in plan.legs
        ],
        "totals": {
            "total_distance_nm": plan.total_distance_nm,
            "total_block_time_min": plan.total_block_time_min,
            "total_block_hours": plan.total_block_hours,
            "total_fuel_gal": plan.total_fuel_gal,
            "total_flight_time_min": plan.total_flight_time_min,
            "estimated_total_cash_needed": plan.estimated_total_cash_needed,
        },
        "crew_duty": duty_check_to_dict(plan.crew_duty) if plan.crew_duty else None,
        "flags": {
            "overnight_required": plan.overnight_required,
            "crew_swap_required": plan.crew_swap_required,
            "fuel_stop_required": plan.fuel_stop_required,
            "weather_degraded": plan.weather_degraded,
            "adsb_degraded": plan.adsb_degraded,
            "critical": plan.critical_flags,
            "warnings": plan.warnings,
        },
    }
