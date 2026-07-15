"""
Flight performance calculator — estimated block time, fuel burn, and range
checks for multi-leg mission planning.

Uses the aircraft's performance profile (cruise speed, climb rate, fuel flow)
combined with great-circle distances to produce realistic block estimates.

NOTE: These are PLANNING estimates, not AFM/POH numbers. The senior pilot
will refine these per aircraft once the actual fleet data is available.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.services.distance import haversine_radians

if TYPE_CHECKING:
    from app.models.aircraft import Aircraft
    from app.models.airport import Airport


@dataclass
class BlockEstimate:
    """Estimated time and fuel for a single leg."""

    leg_distance_nm: float
    taxi_time_min: int = 0
    climb_time_min: int = 0
    cruise_time_min: int = 0
    descent_time_min: int = 0
    total_block_time_min: int = 0
    total_block_hours: float = 0.0

    taxi_fuel_gal: float = 0.0
    climb_fuel_gal: float = 0.0
    cruise_fuel_gal: float = 0.0
    descent_fuel_gal: float = 0.0
    reserve_fuel_gal: float = 0.0
    total_fuel_gal: float = 0.0

    remaining_range_at_destination_nm: float | None = None
    within_range: bool = True
    note: str = ""


@dataclass
class AircraftCapabilities:
    """Human-readable summary of what an aircraft can and can't do on a given leg."""

    can_operate_leg: bool = True
    runway_ok: bool = True
    overwater_required: bool = False
    overwater_capable: bool = False
    icing_possible: bool = False
    icing_certified: bool = False
    rnp_required: bool = False
    rnp_capable: bool = False
    landing_permit_required: bool = False
    restrictions: list[str] = field(default_factory=list)


def estimate_block(
    aircraft: Aircraft,
    origin: Airport,
    destination: Airport,
    cruise_altitude_ft: int | None = None,
) -> BlockEstimate:
    """
    Estimate block time and fuel burn for an aircraft on a single leg.

    Breaks the flight into four standard phases:
      1. Taxi — surface movement (fixed time/fuel per aircraft)
      2. Climb — from field elevation to cruise altitude
      3. Cruise — level flight at cruise speed
      4. Descent — from cruise altitude to destination

    Then adds FAR 135 reserve fuel (default 45 min at cruise burn).
    """
    distance_nm, _, _ = haversine_radians(
        origin.latitude, origin.longitude,
        destination.latitude, destination.longitude,
    )

    # ── Pull aircraft performance (with sensible defaults) ────────────────
    cruise_spd = aircraft.cruise_speed_kt or 180
    climb_spd = aircraft.climb_speed_kt or 140
    climb_rate = aircraft.climb_rate_fpm or 1000
    descent_spd = aircraft.descent_speed_kt or 160
    cruise_ff = float(aircraft.cruise_fuel_flow_gph or 60)
    taxi_fuel = float(aircraft.taxi_fuel_gallons or 5.0)
    reserve_min = aircraft.reserve_fuel_minutes or 45
    max_range = aircraft.max_range_with_reserves_nm or (aircraft.range_nm or 600)

    # ── Climb phase ───────────────────────────────────────────────────────
    cruise_alt = cruise_altitude_ft or (aircraft.typical_cruise_alt_ft or 10000)
    climb_alt_gain = cruise_alt - (origin.elevation_ft or 0)
    if climb_alt_gain < 0:
        climb_alt_gain = 0

    climb_time_min = int(climb_alt_gain / climb_rate) if climb_rate > 0 else 0
    # Approximate fuel burn in climb: ~1.5x cruise flow, slightly rich mixture
    climb_fuel_gal = round(climb_time_min * (cruise_ff * 1.5 / 60), 1)

    # Distance covered during climb (approximate — assumes constant climb gradient)
    climb_dist_nm = (climb_time_min / 60) * climb_spd

    # ── Descent phase ─────────────────────────────────────────────────────
    descent_alt_loss = cruise_alt - (destination.elevation_ft or 0)
    if descent_alt_loss < 0:
        descent_alt_loss = 0

    # Standard descent: ~3° glide path or ~500 ft/min descent rate
    descent_rate = 1500  # ft/min typical
    descent_time_min = int(descent_alt_loss / descent_rate) if descent_rate > 0 else 0
    descent_fuel_gal = round(descent_time_min * (cruise_ff * 0.4 / 60), 1)
    descent_dist_nm = (descent_time_min / 60) * descent_spd

    # ── Cruise phase ──────────────────────────────────────────────────────
    cruise_dist_nm = max(0.0, distance_nm - climb_dist_nm - descent_dist_nm)
    cruise_time_min = int((cruise_dist_nm / cruise_spd) * 60) if cruise_spd > 0 else 0
    cruise_fuel_gal = round(cruise_time_min * (cruise_ff / 60), 1)

    # ── Totals ────────────────────────────────────────────────────────────
    taxi_time_min = 10  # Standard 10-minute taxi assumption
    total_time_min = taxi_time_min + climb_time_min + cruise_time_min + descent_time_min
    total_hours = round(total_time_min / 60, 2)

    total_fuel = round(taxi_fuel + climb_fuel_gal + cruise_fuel_gal + descent_fuel_gal, 1)
    reserve_gal = round(reserve_min * (cruise_ff / 60), 1)
    total_with_reserve = round(total_fuel + reserve_gal, 1)

    # ── Range check ───────────────────────────────────────────────────────
    fuel_available = float(aircraft.fuel_capacity_l or 0) * 0.264172  # L → gal
    within_range = True
    remaining_range = None
    note = ""

    if fuel_available > 0 and distance_nm > max_range:
        within_range = False
        note = f"Leg distance ({distance_nm}nm) exceeds max range with reserves ({max_range}nm)"
    elif fuel_available > 0 and total_with_reserve > fuel_available:
        within_range = False
        note = f"Estimated fuel required ({total_with_reserve}gal) exceeds capacity ({round(fuel_available, 1)}gal)"
    elif fuel_available > 0:
        remaining_fuel = round(fuel_available - total_with_reserve, 1)
        remaining_range = int(
            (remaining_fuel / (cruise_ff / 60)) * (cruise_spd / 60)
        ) if cruise_ff > 0 and cruise_spd > 0 else None

    return BlockEstimate(
        leg_distance_nm=round(distance_nm, 1),
        taxi_time_min=taxi_time_min,
        climb_time_min=climb_time_min,
        cruise_time_min=cruise_time_min,
        descent_time_min=descent_time_min,
        total_block_time_min=total_time_min,
        total_block_hours=total_hours,
        taxi_fuel_gal=taxi_fuel,
        climb_fuel_gal=climb_fuel_gal,
        cruise_fuel_gal=cruise_fuel_gal,
        descent_fuel_gal=descent_fuel_gal,
        reserve_fuel_gal=reserve_gal,
        total_fuel_gal=total_with_reserve,
        remaining_range_at_destination_nm=remaining_range,
        within_range=within_range,
        note=note,
    )


def check_capabilities(
    aircraft: Aircraft,
    origin: Airport,
    destination: Airport,
) -> AircraftCapabilities:
    """
    Check if the aircraft can legally and safely operate the given leg.

    Examines overwater requirements, known icing risk (simplified — latitude-based),
    RNP requirements, and permit requirements at the destination.
    """
    caps = AircraftCapabilities()
    distance_nm, _, _ = haversine_radians(
        origin.latitude, origin.longitude,
        destination.latitude, destination.longitude,
    )

    # ── Overwater ─────────────────────────────────────────────────────────
    # Simplified heuristic: any leg > 50nm over water (no land near the great circle)
    # For now: flag any leg between island nations or over open water
    overwater_routes = {
        ("MYNN", "MIA"), ("MIA", "MYNN"),
        ("MYNN", "MTPP"), ("MTPP", "MYNN"),
        ("MYNN", "PAP"), ("PAP", "MYNN"),
        ("MYNN", "HAV"), ("HAV", "MYNN"),
        ("MIA", "HAV"), ("HAV", "MIA"),
        ("MIA", "MTPP"), ("MTPP", "MIA"),
        ("MEX", "HAV"), ("HAV", "MEX"),
        ("MEX", "MTPP"), ("MTPP", "MEX"),
        ("PAP", "HAV"), ("HAV", "PAP"),
    }
    route_key = (origin.icao_code, destination.icao_code)
    caps.overwater_required = route_key in overwater_routes or distance_nm > 100
    caps.overwater_capable = aircraft.overwater_capable

    if caps.overwater_required and not caps.overwater_capable:
        caps.can_operate_leg = False
        caps.restrictions.append(
            "Overwater leg — aircraft not equipped for extended overwater operations"
        )

    # ── Known icing (simplified — altitudes above 12k ft in visible moisture) ──
    # Real check: SIGMET/AIRMET + temp profile. Here we flag based on route.
    icing_latitudes = route_key in {
        ("MYNN", "MIA"), ("MIA", "MYNN"),
        ("MYNN", "HAV"), ("HAV", "MYNN"),
    }
    caps.icing_possible = icing_latitudes
    caps.icing_certified = aircraft.known_icing_certified

    if caps.icing_possible and not caps.icing_certified:
        caps.restrictions.append(
            "Known icing possible — aircraft not certified"
        )

    # ── RNP approach ──────────────────────────────────────────────────────
    # Airports without ILS may require RNP approaches
    rnp_airports = {"HAV", "PAP", "MTPP", "MTBJ"}
    caps.rnp_required = destination.icao_code in rnp_airports
    caps.rnp_capable = aircraft.rnp_approach_capable

    if caps.rnp_required and not caps.rnp_capable:
        caps.can_operate_leg = False
        caps.restrictions.append(
            f"{destination.icao_code} requires RNP approach — aircraft not capable"
        )

    # ── Landing permit ────────────────────────────────────────────────────
    caps.landing_permit_required = destination.has_landing_permit_required

    # ── Runway length ─────────────────────────────────────────────────────
    if destination.longest_runway_ft and destination.longest_runway_ft < 3000:
        # Most Part 135 turboprops need at least 3000ft
        # TODO: per-aircraft takeoff/landing distance from POH
        caps.restrictions.append(
            f"Short runway ({destination.longest_runway_ft}ft) — verify aircraft takeoff/landing performance"
        )

    return caps
