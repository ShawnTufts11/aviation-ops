"""
Weight & Balance calculator — per-leg loading analysis using aircraft weight
limits, passenger manifest data, cargo, and fuel.

Uses standard FAA passenger weights (AC 120-27F) as fallback when actual
passenger weights aren't recorded. All weights in kilograms.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models.aircraft import Aircraft

# ── Constants ──────────────────────────────────────────────────────────

JET_A_KG_PER_GAL = 3.0  # ~6.7 lb/gal → 3.0 kg/gal (rounded for Jet-A)
JET_A_KG_PER_L = 0.79   # Jet-A density in kg/liter

# Standard passenger weights (FAA AC 120-27F, averaged)
STD_PASSENGER_KG = 90   # kg (including carry-on, conservative)
STD_BAGGAGE_KG = 14     # kg per bag (checked, average)

# Weight classes for reporting
WEIGHT_OK = "ok"
WEIGHT_WARN = "warning"
WEIGHT_CRITICAL = "over_limit"


@dataclass
class WeightBalanceReport:
    """Per-leg weight & balance result."""

    leg_index: int
    origin: str
    destination: str

    # Weights (kg)
    basic_empty_weight_kg: float = 0.0
    crew_weight_kg: float = 0.0
    passenger_weight_kg: float = 0.0
    cargo_weight_kg: float = 0.0
    zero_fuel_weight_kg: float = 0.0
    fuel_weight_kg: float = 0.0
    ramp_weight_kg: float = 0.0
    takeoff_weight_kg: float = 0.0  # Ramp - taxi fuel
    landing_weight_kg: float = 0.0   # Takeoff - cruise fuel burn

    # Limits
    mtow_kg: float = 0.0
    mlw_kg: float = 0.0
    max_zfw_kg: float = 0.0
    max_cargo_kg: float = 0.0

    # Margins
    mtow_margin_kg: float = 0.0
    mlw_margin_kg: float = 0.0
    zfw_margin_kg: float = 0.0
    cargo_margin_kg: float = 0.0

    # Status per limit
    mtow_status: str = WEIGHT_OK
    mlw_status: str = WEIGHT_OK
    zfw_status: str = WEIGHT_OK
    cargo_status: str = WEIGHT_OK
    overall_status: str = WEIGHT_OK

    # Details
    passenger_count: int = 0
    crew_count: int = 0
    fuel_on_board_gal: float = 0.0
    fuel_burn_gal: float = 0.0
    taxi_fuel_gal: float = 0.0

    notes: list[str] = field(default_factory=list)


def _status_for_margin(margin_kg: float, total_kg: float) -> str:
    """Return status based on margin as percentage of limit."""
    if margin_kg < 0:
        return WEIGHT_CRITICAL
    pct = (margin_kg / max(total_kg, 1)) * 100
    if pct < 3:
        return WEIGHT_WARN
    return WEIGHT_OK


async def calculate_leg_wb(
    aircraft: Aircraft,
    origin: str,
    destination: str,
    leg_index: int,
    passenger_count: int = 0,
    passenger_weights: list[float] | None = None,
    cargo_kg: float = 0.0,
    fuel_gal: float = 0.0,
    fuel_burn_gal: float = 0.0,
    taxi_fuel_gal: float | None = None,
    crew_count: int = 2,
    standard_passenger_kg: float = STD_PASSENGER_KG,
) -> WeightBalanceReport:
    """
    Calculate weight & balance for a single leg.

    Args:
        aircraft: Aircraft model (uses bhw_kg, mtow_kg, mlw_kg, max_cargo_kg, fuel_capacity_l)
        origin/destination: ICAO codes (for reporting only)
        leg_index: Leg number in the mission
        passenger_count: Number of passengers on this leg
        passenger_weights: Actual weights if available (list of kg per passenger)
        cargo_kg: Cargo weight in kg
        fuel_gal: Fuel on board in gallons
        fuel_burn_gal: Estimated fuel burn for this leg in gallons
        taxi_fuel_gal: Taxi fuel in gallons (defaults to aircraft taxi_fuel_gallons)
        crew_count: Number of crew (default 2)
        standard_passenger_kg: Fallback weight when actual weights unavailable

    Returns:
        WeightBalanceReport with all calculated values and margin status
    """
    report = WeightBalanceReport(
        leg_index=leg_index,
        origin=origin,
        destination=destination,
    )

    # ── Aircraft limits ──────────────────────────────────────────────────
    report.basic_empty_weight_kg = float(aircraft.bhw_kg or 0)
    report.mtow_kg = float(aircraft.mtow_kg or 0)
    report.mlw_kg = float(aircraft.mlw_kg or 0) or report.mtow_kg * 0.9  # Estimate MLW at 90% MTOW if missing
    report.max_cargo_kg = float(aircraft.max_cargo_kg or 0)

    # Estimate max ZFW: typically MTOW minus ~60% of max fuel weight
    max_fuel_kg = (float(aircraft.fuel_capacity_l or 0) * JET_A_KG_PER_L)
    report.max_zfw_kg = max(0, report.mtow_kg - (max_fuel_kg * 0.6))

    # ── Crew weight ──────────────────────────────────────────────────────
    report.crew_count = crew_count
    crew_kg = crew_count * 85  # Standard 85kg per crew member (uniform + kit)
    report.crew_weight_kg = crew_kg

    # ── Passenger weight ─────────────────────────────────────────────────
    report.passenger_count = passenger_count
    if passenger_weights:
        actual_sum = sum(passenger_weights)
        remaining = passenger_count - len(passenger_weights)
        if remaining > 0:
            actual_sum += remaining * standard_passenger_kg
        report.passenger_weight_kg = actual_sum
    else:
        report.passenger_weight_kg = passenger_count * standard_passenger_kg

    # ── Cargo ────────────────────────────────────────────────────────────
    report.cargo_weight_kg = cargo_kg
    report.cargo_margin_kg = report.max_cargo_kg - cargo_kg
    report.cargo_status = _status_for_margin(report.cargo_margin_kg, report.max_cargo_kg)
    if report.cargo_status == WEIGHT_CRITICAL:
        report.notes.append(f"Cargo {cargo_kg}kg exceeds limit {report.max_cargo_kg}kg")

    # ── Fuel weight ──────────────────────────────────────────────────────
    report.fuel_on_board_gal = fuel_gal
    report.fuel_burn_gal = fuel_burn_gal
    report.taxi_fuel_gal = taxi_fuel_gal or float(aircraft.taxi_fuel_gallons or 5.0)
    report.fuel_weight_kg = fuel_gal * JET_A_KG_PER_GAL  # Total fuel weight at ramp

    # ── Weight calculations ──────────────────────────────────────────────
    report.zero_fuel_weight_kg = (
        report.basic_empty_weight_kg
        + report.crew_weight_kg
        + report.passenger_weight_kg
        + report.cargo_weight_kg
    )

    report.ramp_weight_kg = report.zero_fuel_weight_kg + report.fuel_weight_kg

    # Takeoff weight = ramp weight minus taxi fuel
    taxi_fuel_kg = report.taxi_fuel_gal * JET_A_KG_PER_GAL
    report.takeoff_weight_kg = report.ramp_weight_kg - taxi_fuel_kg

    # Landing weight = takeoff weight minus fuel burned in flight
    burn_fuel_kg = fuel_burn_gal * JET_A_KG_PER_GAL
    report.landing_weight_kg = report.takeoff_weight_kg - burn_fuel_kg

    # ── Margins ──────────────────────────────────────────────────────────
    report.zfw_margin_kg = report.max_zfw_kg - report.zero_fuel_weight_kg
    report.zfw_status = _status_for_margin(report.zfw_margin_kg, report.max_zfw_kg)

    report.mtow_margin_kg = report.mtow_kg - report.takeoff_weight_kg
    report.mtow_status = _status_for_margin(report.mtow_margin_kg, report.mtow_kg)

    report.mlw_margin_kg = report.mlw_kg - report.landing_weight_kg
    report.mlw_status = _status_for_margin(report.mlw_margin_kg, report.mlw_kg)

    # ── Overall status ──────────────────────────────────────────────────
    statuses = [report.mtow_status, report.mlw_status, report.zfw_status, report.cargo_status]
    if WEIGHT_CRITICAL in statuses:
        report.overall_status = WEIGHT_CRITICAL
    elif WEIGHT_WARN in statuses:
        report.overall_status = WEIGHT_WARN

    # ── Notes for warnings ──────────────────────────────────────────────
    if report.mtow_status == WEIGHT_WARN:
        report.notes.append(f"TOW ({report.takeoff_weight_kg:.0f}kg) close to MTOW ({report.mtow_kg:.0f}kg)")
    if report.mlw_status == WEIGHT_WARN:
        report.notes.append(f"LW ({report.landing_weight_kg:.0f}kg) close to MLW ({report.mlw_kg:.0f}kg)")
    if report.zfw_status == WEIGHT_WARN:
        report.notes.append(f"ZFW ({report.zero_fuel_weight_kg:.0f}kg) close to max ZFW ({report.max_zfw_kg:.0f}kg)")

    return report


def wb_to_dict(report: WeightBalanceReport) -> dict[str, Any]:
    """Convert report to JSON-serializable dict."""
    return {
        "leg_index": report.leg_index,
        "origin": report.origin,
        "destination": report.destination,
        "passenger_count": report.passenger_count,
        "crew_count": report.crew_count,
        "cargo_kg": report.cargo_weight_kg,
        "fuel_on_board_gal": report.fuel_on_board_gal,
        "fuel_burn_gal": report.fuel_burn_gal,
        "weights": {
            "basic_empty_kg": round(report.basic_empty_weight_kg, 1),
            "crew_kg": round(report.crew_weight_kg, 1),
            "passengers_kg": round(report.passenger_weight_kg, 1),
            "cargo_kg": round(report.cargo_weight_kg, 1),
            "zero_fuel_kg": round(report.zero_fuel_weight_kg, 1),
            "fuel_kg": round(report.fuel_weight_kg, 1),
            "ramp_kg": round(report.ramp_weight_kg, 1),
            "takeoff_kg": round(report.takeoff_weight_kg, 1),
            "landing_kg": round(report.landing_weight_kg, 1),
        },
        "limits": {
            "mtow_kg": report.mtow_kg,
            "mlw_kg": report.mlw_kg,
            "max_zfw_kg": round(report.max_zfw_kg, 1),
            "max_cargo_kg": report.max_cargo_kg,
        },
        "margins": {
            "mtow_margin_kg": round(report.mtow_margin_kg, 1),
            "mtow_status": report.mtow_status,
            "mlw_margin_kg": round(report.mlw_margin_kg, 1),
            "mlw_status": report.mlw_status,
            "zfw_margin_kg": round(report.zfw_margin_kg, 1),
            "zfw_status": report.zfw_status,
            "cargo_margin_kg": round(report.cargo_margin_kg, 1),
            "cargo_status": report.cargo_status,
        },
        "overall_status": report.overall_status,
        "notes": report.notes,
    }
