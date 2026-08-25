"""
E2E Test: Caribbean Loop Mission — Route Planner Integration Test

Tests the full route planning pipeline for the 6-leg Caribbean Loop:
  MYNN → KMIA → MMUN → MTPP → MUHA → MDPC → MYNN

Connects directly to the SQLite DB via async SQLAlchemy, resolves aircraft
and airport models, calls plan_route() directly, and validates every field.

Reports any gaps: missing data, zero values, errors, null fields.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Must run from project root with .venv activated
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./pararig_ops.db")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.models.aircraft import Aircraft
from app.models.airport import Airport
from app.services.route_planner import plan_route, route_plan_to_dict, LegPlan, RoutePlan

# ── Constants ─────────────────────────────────────────────────────────
AIRCRAFT_TAIL = "C6-PRB"  # King Air 350i

CARIBBEAN_LOOP_LEGS = [
    ("MYNN", "KMIA"),   # Nassau → Miami
    ("KMIA", "MMUN"),   # Miami → Cancún
    ("MMUN", "MTPP"),   # Cancún → Port-au-Prince
    ("MTPP", "MUHA"),   # Port-au-Prince → Havana
    ("MUHA", "MDPC"),   # Havana → Punta Cana
    ("MDPC", "MYNN"),   # Punta Cana → Nassau
]

CREW_CONFIG = {
    "crew_count": 2,
    "is_two_pilot": True,
    "crew_members": None,  # Use generic check
    "passenger_counts": [2, 2, 2, 2, 2, 2],  # 2 pax per leg
    "cargo_kg": 100.0,
}

REPORT_PATH = Path("/tmp/caribbean-loop-test.json")


# ── Helpers ───────────────────────────────────────────────────────────

def _check(condition: bool, label: str, issues: list) -> None:
    """Record a check result."""
    if condition:
        print(f"  ✅ {label}")
    else:
        print(f"  ❌ {label}")
        issues.append(label)


def _check_val(val, min_val: float, label: str, issues: list) -> None:
    """Check a numeric value is > min_val or non-null."""
    if val is None:
        issues.append(f"{label} is None")
        print(f"  ❌ {label} = None")
    elif val == 0:
        issues.append(f"{label} is 0 (unexpected)")
        print(f"  ⚠️  {label} = 0")
    elif isinstance(val, (int, float)) and val < min_val:
        issues.append(f"{label} = {val} < {min_val}")
        print(f"  ⚠️  {label} = {val} (below {min_val})")
    else:
        print(f"  ✅ {label} = {val}")


def _summarize_issues(issues: list, title: str) -> dict:
    """Create a summary dict for issues."""
    return {
        "title": title,
        "total": len(issues),
        "critical": [i for i in issues if "ERROR" in i.upper() or "ZERO" in i.upper() or "NONE" in i.upper()],
        "warnings": [i for i in issues if i not in ("ERROR", "ZERO", "NONE")],
        "issues": issues,
    }


# ═══════════════════════════════════════════════════════════════════════
#  MAIN TEST
# ═══════════════════════════════════════════════════════════════════════

async def run_test() -> dict:
    report = {
        "test_name": "Caribbean Loop Mission — E2E Route Planner Test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "aircraft_tail": AIRCRAFT_TAIL,
        "route": CARIBBEAN_LOOP_LEGS,
        "aircraft_data": {},
        "leg_results": [],
        "crew_duty": {},
        "mission_totals": {},
        "errors": [],
        "gaps": {
            "missing_fields": [],
            "zero_values": [],
            "null_fields": [],
            "airport_issues": [],
            "performance_issues": [],
            "customs_issues": [],
            "permit_issues": [],
        },
        "summary": {},
    }

    all_issues: list[str] = []

    print(f"\n{'='*70}")
    print(f"  CARIBBEAN LOOP MISSION — E2E ROUTE PLANNER TEST")
    print(f"  Aircraft: King Air 350i (tail {AIRCRAFT_TAIL})")
    print(f"  Route: {' → '.join(o for o, _ in CARIBBEAN_LOOP_LEGS)} → {CARIBBEAN_LOOP_LEGS[-1][1]}")
    print(f"{'='*70}\n")

    # ── 1. Database connection ─────────────────────────────────────────
    print("─── Phase 1: Database Connection ───")
    db_issues: list[str] = []

    db_url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./pararig_ops.db")
    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            print("  ✅ DB connection established")
    except Exception as e:
        print(f"  ❌ DB connection failed: {e}")
        db_issues.append(f"DB connection failed: {e}")
        return report

    # ── 2. Load aircraft ───────────────────────────────────────────────
    print("\n─── Phase 2: Aircraft Lookup ───")
    ac_issues: list[str] = []

    async with async_session() as session:
        stmt = select(Aircraft).where(Aircraft.tail_number == AIRCRAFT_TAIL)
        result = await session.execute(stmt)
        aircraft = result.scalar_one_or_none()

        if not aircraft:
            print(f"  ❌ Aircraft {AIRCRAFT_TAIL} not found!")
            ac_issues.append(f"Aircraft {AIRCRAFT_TAIL} not found in DB")
            return report

        print(f"  ✅ Found: {aircraft.tail_number} ({aircraft.make} {aircraft.model})")
        print(f"     MTOW: {aircraft.mtow_kg} kg | BEW: {aircraft.bhw_kg} kg | Fuel: {aircraft.fuel_capacity_l} L")
        print(f"     Cruise: {aircraft.cruise_speed_kt} kt | Range: {aircraft.range_nm} nm / {aircraft.max_range_with_reserves_nm} nm w/reserves")
        print(f"     Overwater: {aircraft.overwater_capable} | Icing: {aircraft.known_icing_certified} | RNP: {aircraft.rnp_approach_capable}")
        print(f"     Max Seats: {aircraft.max_seats} | Max Cargo: {aircraft.max_cargo_kg} kg")

        # Check aircraft data completeness
        if not aircraft.mtow_kg:
            ac_issues.append("MTOW is None/zero")
        if not aircraft.bhw_kg:
            ac_issues.append("BEW (bhw_kg) is None/zero")
        if not aircraft.fuel_capacity_l:
            ac_issues.append("Fuel capacity is None/zero")
        if not aircraft.max_cargo_kg:
            ac_issues.append("max_cargo_kg is None/zero")
        if not aircraft.taxi_fuel_gallons:
            ac_issues.append("taxi_fuel_gallons is None/zero — W&B will estimate")

        report["aircraft_data"] = {
            "id": aircraft.id,
            "tail_number": aircraft.tail_number,
            "make": aircraft.make,
            "model": aircraft.model,
            "category": aircraft.category.value if aircraft.category else None,
            "mtow_kg": float(aircraft.mtow_kg) if aircraft.mtow_kg else None,
            "mlw_kg": float(aircraft.mlw_kg) if aircraft.mlw_kg else None,
            "bhw_kg": float(aircraft.bhw_kg) if aircraft.bhw_kg else None,
            "fuel_capacity_l": float(aircraft.fuel_capacity_l) if aircraft.fuel_capacity_l else None,
            "cruise_speed_kt": aircraft.cruise_speed_kt,
            "cruise_fuel_flow_gph": float(aircraft.cruise_fuel_flow_gph) if aircraft.cruise_fuel_flow_gph else None,
            "max_range_with_reserves_nm": aircraft.max_range_with_reserves_nm,
            "range_nm": aircraft.range_nm,
            "overwater_capable": aircraft.overwater_capable,
            "known_icing_certified": aircraft.known_icing_certified,
            "rnp_approach_capable": aircraft.rnp_approach_capable,
        }

    # ── 3. Load airports ──────────────────────────────────────────────
    print("\n─── Phase 3: Airport Lookup ───")
    apt_issues: list[str] = []
    airport_cache: dict[str, Airport] = {}

    all_icaos = set()
    for o, d in CARIBBEAN_LOOP_LEGS:
        all_icaos.add(o)
        all_icaos.add(d)

    async with async_session() as session:
        for icao in sorted(all_icaos):
            stmt = select(Airport).where(Airport.icao_code == icao)
            result = await session.execute(stmt)
            apt = result.scalar_one_or_none()
            if apt:
                airport_cache[icao] = apt
                print(f"  ✅ {icao}: {apt.name} ({apt.city}, {apt.country_code})")
                if apt.latitude == 0 or apt.longitude == 0:
                    apt_issues.append(f"{icao}: lat/lon is 0,0 (missing coordinates)")
            else:
                print(f"  ❌ {icao}: NOT FOUND in database")
                apt_issues.append(f"{icao}: airport not in database")
                report["gaps"]["airport_issues"].append(f"{icao}: not found")

    if not airport_cache:
        print("  ❌ No airports loaded — cannot continue")
        return report

    # ── 4. Build legs ─────────────────────────────────────────────────
    print("\n─── Phase 4: Build Route Legs ───")
    legs: list[tuple[Airport, Airport, int | None]] = []
    for i, (origin_icao, dest_icao) in enumerate(CARIBBEAN_LOOP_LEGS):
        origin = airport_cache.get(origin_icao)
        dest = airport_cache.get(dest_icao)
        if not origin or not dest:
            print(f"  ❌ Leg {i+1}: {origin_icao}→{dest_icao} — missing airport data")
            continue
        legs.append((origin, dest, None))  # Auto cruise altitude
        print(f"  ✅ Leg {i+1}: {origin_icao} ({origin.latitude}, {origin.longitude}) → {dest_icao} ({dest.latitude}, {dest.longitude})")

    if len(legs) != 6:
        print(f"  ❌ Expected 6 legs, got {len(legs)}")
        return report

    # ── 5. Plan route ─────────────────────────────────────────────────
    print("\n─── Phase 5: Route Planning ───")
    plan_issues: list[str] = []

    try:
        route_plan: RoutePlan = await plan_route(
            aircraft=aircraft,
            legs=legs,
            passenger_counts=CREW_CONFIG["passenger_counts"],
            cargo_kg=CREW_CONFIG["cargo_kg"],
            crew_count=CREW_CONFIG["crew_count"],
            is_two_pilot=CREW_CONFIG["is_two_pilot"],
            crew_members=CREW_CONFIG["crew_members"],
        )
        print("  ✅ plan_route() completed successfully")
    except Exception as e:
        print(f"  ❌ plan_route() failed: {e}")
        import traceback
        traceback.print_exc()
        plan_issues.append(f"plan_route() raised exception: {e}")
        report["errors"].append(str(e))
        return report

    # ── 6. Convert to dict ─────────────────────────────────────────────
    try:
        plan_dict = route_plan_to_dict(route_plan)
        print("  ✅ route_plan_to_dict() converted successfully")
    except Exception as e:
        print(f"  ❌ route_plan_to_dict() failed: {e}")
        plan_issues.append(f"route_plan_to_dict() raised exception: {e}")
        return report

    print(f"     Legs planned: {len(route_plan.legs)}")
    print(f"     Total distance: {route_plan.total_distance_nm} nm")
    print(f"     Total block: {route_plan.total_block_hours} hrs ({route_plan.total_block_time_min} min)")
    print(f"     Total fuel: {route_plan.total_fuel_gal} gal")
    print(f"     Flags: overnight={route_plan.overnight_required}, crew_swap={route_plan.crew_swap_required}, fuel_stop={route_plan.fuel_stop_required}")

    # ── 7. Per-leg analysis ───────────────────────────────────────────
    print("\n─── Phase 6: Per-Leg Analysis ───")
    leg_results = []

    for idx, leg in enumerate(route_plan.legs):
        leg_issues: list[str] = []
        print(f"\n  ── Leg {leg.leg_index}: {leg.origin_icao} → {leg.destination_icao} ──")

        # 7a. Basic leg data
        _check(leg.origin_icao and leg.destination_icao, f"Origin/Dest ICAO present", leg_issues)
        _check_val(leg.origin_lat, 0, "origin_lat", leg_issues)
        _check_val(leg.origin_lon, -180, "origin_lon (non-zero)", leg_issues)
        _check_val(leg.dest_lat, 0, "dest_lat", leg_issues)
        _check_val(leg.dest_lon, -180, "dest_lon (non-zero)", leg_issues)
        _check(leg.origin_name != "", f"origin_name = {leg.origin_name}", leg_issues)
        _check(leg.destination_name != "", f"destination_name = {leg.destination_name}", leg_issues)

        # 7b. Route math
        _check_val(leg.distance_nm, 10, f"distance_nm", leg_issues)
        print(f"     Distance: {leg.distance_nm} nm")

        # 7c. Block estimate
        _check(leg.block is not None, "block estimate present", leg_issues)
        if leg.block:
            _check_val(leg.block.total_block_time_min, 10, "block_time_min", leg_issues)
            _check_val(leg.block.total_fuel_gal, 10, "total_fuel_gal", leg_issues)
            _check(leg.block.within_range is not None, f"within_range = {leg.block.within_range}", leg_issues)
            print(f"     Block: {leg.block.total_block_time_min} min ({leg.block.total_block_hours} hrs)")
            print(f"     Fuel: {leg.block.total_fuel_gal} gal (reserve: {leg.block.reserve_fuel_gal} gal)")
            print(f"     Range check: {'✅' if leg.block.within_range else '❌'} {leg.block.note}")
            if not leg.block.within_range:
                leg_issues.append(f"Leg {leg.leg_index}: Range exceeded — {leg.block.note}")

            # Check phase breakdowns
            _check_val(leg.block.taxi_time_min, 0, "taxi_time_min", leg_issues)
            _check_val(leg.block.climb_time_min, 0, "climb_time_min", leg_issues)
            _check_val(leg.block.cruise_time_min, 0, "cruise_time_min", leg_issues)
            _check_val(leg.block.descent_time_min, 0, "descent_time_min", leg_issues)

        # 7d. Capabilities
        _check(leg.capabilities is not None, "capabilities check present", leg_issues)
        if leg.capabilities:
            print(f"     Capabilities: ok={leg.capabilities.can_operate_leg}, overwater={leg.capabilities.overwater_required}, icing={leg.capabilities.icing_possible}, rnp={leg.capabilities.rnp_required}")
            if leg.capabilities.restrictions:
                for r in leg.capabilities.restrictions:
                    print(f"       ⚠️  Restriction: {r}")
                    leg_issues.append(f"Capability restriction: {r}")

        # 7e. Weight & Balance
        _check(leg.wb is not None, "W&B report present", leg_issues)
        if leg.wb:
            print(f"     W&B: TOW={leg.wb.takeoff_weight_kg:.0f}kg / MTOW={leg.wb.mtow_kg:.0f}kg  |  LW={leg.wb.landing_weight_kg:.0f}kg / MLW={leg.wb.mlw_kg:.0f}kg")
            print(f"     W&B: ZFW={leg.wb.zero_fuel_weight_kg:.0f}kg / MaxZFW={leg.wb.max_zfw_kg:.0f}kg")
            print(f"     W&B: Status={leg.wb.overall_status} | MTOW margin={leg.wb.mtow_margin_kg:.0f}kg | MLW margin={leg.wb.mlw_margin_kg:.0f}kg")
            _check(leg.wb.overall_status in ("ok", "warning", "over_limit"), f"overall_status = {leg.wb.overall_status}", leg_issues)
            _check_val(leg.wb.takeoff_weight_kg, 500, "TOW (takeoff_weight_kg)", leg_issues)
            _check_val(leg.wb.mtow_kg, 1000, "MTOW (mtow_kg)", leg_issues)
            _check_val(leg.wb.zero_fuel_weight_kg, 500, "ZFW (zero_fuel_weight_kg)", leg_issues)

            if leg.wb.overall_status == "over_limit":
                leg_issues.append(f"W&B over limit on leg {leg.leg_index}: {leg.wb.notes}")
                for note in leg.wb.notes:
                    print(f"       ❌ W&B: {note}")

            # Check for null margins
            null_margins = []
            for mfield in ["mtow_margin_kg", "mlw_margin_kg", "zfw_margin_kg", "cargo_margin_kg"]:
                val = getattr(leg.wb, mfield, None)
                if val is None:
                    null_margins.append(mfield)
            if null_margins:
                leg_issues.append(f"W&B null margins: {null_margins}")
                report["gaps"]["null_fields"].extend(null_margins)

            # Check fuel details in W&B
            _check_val(leg.wb.fuel_on_board_gal, 0, "W&B fuel_on_board_gal", leg_issues)
            _check_val(leg.wb.fuel_burn_gal, 0, "W&B fuel_burn_gal", leg_issues)

            if leg.wb.passenger_count != CREW_CONFIG["passenger_counts"][idx]:
                leg_issues.append(f"W&B passenger_count = {leg.wb.passenger_count}, expected {CREW_CONFIG['passenger_counts'][idx]}")

        # 7f. Destination intelligence
        print(f"     Intel: FBOs={leg.fbo_count}, Hotels={leg.hotel_count}")
        print(f"     Fuel: Jet-A=${leg.fuel_price_jet_a}/gal, AVGAS=${leg.fuel_price_avgas}/gal")
        print(f"     Customs: {leg.has_customs} ({leg.customs_hours})")
        print(f"     Night ops: {leg.has_night_ops} | MRO: {leg.has_mro}")
        print(f"     Permits: landing={leg.has_landing_permit}, overflight={leg.has_overflight_permit}")
        print(f"     Hours: {leg.operating_hours}")
        print(f"     Notes: {leg.notes[:80] if leg.notes else '(none)'}")

        _check(leg.fbo_count >= 0, f"FBO count = {leg.fbo_count}", leg_issues)
        _check(leg.hotel_count >= 0, f"Hotel count = {leg.hotel_count}", leg_issues)

        # Customs data checking
        if leg.has_customs:
            _check(bool(leg.customs_hours), f"customs_hours = {leg.customs_hours}", leg_issues)
        else:
            report["gaps"]["customs_issues"].append(f"{leg.destination_icao}: no customs")

        # Fuel price checking
        if leg.fuel_price_jet_a is None and leg.fuel_price_avgas is None:
            report["gaps"]["missing_fields"].append(f"{leg.destination_icao}: no fuel prices")
            leg_issues.append(f"No fuel price data at {leg.destination_icao}")

        # Restrictions
        if leg.restrictions:
            for r in leg.restrictions:
                print(f"       ⚠️  Restriction [{r.get('type','?')}]: {r.get('description','')}")

        # Weather/NOTAMs
        _check(leg.weather is not None, f"weather data present", leg_issues)
        if leg.weather:
            wx_err = leg.weather.get("error")
            if wx_err:
                print(f"       ⚠️  Weather: {wx_err}")
                leg_issues.append(f"Weather error at {leg.destination_icao}: {wx_err}")
            else:
                wxc = leg.weather.get("flight_category", "")
                print(f"       Weather: {leg.weather.get('temp_c','?')}°C, {leg.weather.get('wind_speed_kt','?')}kt, {wxc}")
                if wxc in ("IFR", "LIFR"):
                    leg_issues.append(f"Low IFR conditions at {leg.destination_icao}")

        _check(leg.notams is not None, f"NOTAMs present (may be empty list)", leg_issues)
        if leg.notams:
            print(f"       NOTAMs: {len(leg.notams)} active")

        # 7g. Flags
        print(f"     Flags ({len(leg.flags)}): {leg.flags}")
        print(f"     Is OK: {leg.is_ok}")

        # ── Build per-leg result dict ──
        leg_info = {
            "leg_index": leg.leg_index,
            "origin": leg.origin_icao,
            "destination": leg.destination_icao,
            "origin_name": leg.origin_name,
            "destination_name": leg.destination_name,
            "distance_nm": leg.distance_nm,
            "block_time_min": leg.block.total_block_time_min if leg.block else None,
            "block_time_hrs": leg.block.total_block_hours if leg.block else None,
            "fuel_gal": leg.block.total_fuel_gal if leg.block else None,
            "fuel_reserve_gal": leg.block.reserve_fuel_gal if leg.block else None,
            "within_range": leg.block.within_range if leg.block else None,
            "capabilities_ok": leg.capabilities.can_operate_leg if leg.capabilities else None,
            "weight_balance": {
                "tow_kg": leg.wb.takeoff_weight_kg if leg.wb else None,
                "mtow_kg": leg.wb.mtow_kg if leg.wb else None,
                "lw_kg": leg.wb.landing_weight_kg if leg.wb else None,
                "mlw_kg": leg.wb.mlw_kg if leg.wb else None,
                "zfw_kg": leg.wb.zero_fuel_weight_kg if leg.wb else None,
                "max_zfw_kg": leg.wb.max_zfw_kg if leg.wb else None,
                "mtow_margin_kg": leg.wb.mtow_margin_kg if leg.wb else None,
                "mlw_margin_kg": leg.wb.mlw_margin_kg if leg.wb else None,
                "overall_status": leg.wb.overall_status if leg.wb else None,
            },
            "destination_intel": {
                "fbo_count": leg.fbo_count,
                "hotel_count": leg.hotel_count,
                "fuel_price_jet_a": leg.fuel_price_jet_a,
                "fuel_price_avgas": leg.fuel_price_avgas,
                "has_customs": leg.has_customs,
                "customs_hours": leg.customs_hours,
                "has_night_ops": leg.has_night_ops,
                "has_mro": leg.has_mro,
                "landing_permit_required": leg.has_landing_permit,
                "overflight_permit_required": leg.has_overflight_permit,
                "restrictions": leg.restrictions,
            },
            "flags": leg.flags,
            "is_ok": leg.is_ok,
            "issues": leg_issues,
        }
        leg_results.append(leg_info)
        all_issues.extend(leg_issues)

    report["leg_results"] = leg_results

    # ── 8. Crew duty analysis ──────────────────────────────────────────
    print("\n─── Phase 7: Crew Duty Analysis ───")
    duty_issues: list[str] = []

    _check(route_plan.crew_duty is not None, "crew_duty check present", duty_issues)
    if route_plan.crew_duty:
        cd = route_plan.crew_duty
        _check(cd.mission_legal is not None, f"mission_legal = {cd.mission_legal}", duty_issues)
        print(f"     Mission legal: {'✅' if cd.mission_legal else '❌'} {cd.mission_violations}")
        print(f"     Violations: {cd.mission_violations if cd.mission_violations else '(none)'}")

        for crew_status in cd.crew:
            print(f"     Crew: {crew_status.crew_name} ({crew_status.crew_role})")
            print(f"       Duty period: {crew_status.duty_period_hours}hrs | Flight time: {crew_status.flight_time_hours}hrs")
            print(f"       Rest: {crew_status.rest_hours_received}hrs (adequate={crew_status.rest_adequate})")
            print(f"       Legal: {crew_status.is_legal} | Violations: {crew_status.violations}")

            if not crew_status.is_legal:
                duty_issues.extend(crew_status.violations)

        report["crew_duty"] = {
            "mission_legal": cd.mission_legal,
            "mission_violations": cd.mission_violations,
            "crew_count": len(cd.crew),
            "crew_details": [
                {
                    "name": c.crew_name,
                    "role": c.crew_role,
                    "duty_period_hours": c.duty_period_hours,
                    "flight_time_hours": c.flight_time_hours,
                    "rest_hours": c.rest_hours_received,
                    "rest_adequate": c.rest_adequate,
                    "is_legal": c.is_legal,
                    "violations": c.violations,
                    "warnings": c.warnings,
                }
                for c in cd.crew
            ],
        }
    else:
        report["gaps"]["missing_fields"].append("crew_duty is None")

    all_issues.extend(duty_issues)

    # ── 9. Mission totals & flags ──────────────────────────────────────
    print("\n─── Phase 8: Mission Totals & Flags ───")
    totals_issues: list[str] = []

    _check_val(route_plan.total_distance_nm, 100, "total_distance_nm", totals_issues)
    _check_val(route_plan.total_block_time_min, 60, "total_block_time_min", totals_issues)
    _check_val(route_plan.total_block_hours, 1, "total_block_hours", totals_issues)
    _check_val(route_plan.total_fuel_gal, 50, "total_fuel_gal", totals_issues)

    print(f"     Total distance: {route_plan.total_distance_nm} nm")
    print(f"     Total block: {route_plan.total_block_hours} hrs ({route_plan.total_block_time_min} min)")
    print(f"     Total flight: {route_plan.total_flight_time_min} min")
    print(f"     Total fuel: {route_plan.total_fuel_gal} gal")
    print(f"     Overnight required: {route_plan.overnight_required}")
    print(f"     Crew swap required: {route_plan.crew_swap_required}")
    print(f"     Fuel stop required: {route_plan.fuel_stop_required}")
    print(f"     Critical flags: {route_plan.critical_flags}")
    print(f"     Warnings: {route_plan.warnings}")

    report["mission_totals"] = {
        "total_distance_nm": route_plan.total_distance_nm,
        "total_block_time_min": route_plan.total_block_time_min,
        "total_block_hours": route_plan.total_block_hours,
        "total_fuel_gal": route_plan.total_fuel_gal,
        "total_flight_time_min": route_plan.total_flight_time_min,
        "overnight_required": route_plan.overnight_required,
        "crew_swap_required": route_plan.crew_swap_required,
        "fuel_stop_required": route_plan.fuel_stop_required,
        "critical_flags": route_plan.critical_flags,
        "warnings": route_plan.warnings,
    }

    all_issues.extend(totals_issues)

    # ── 10. Summary ────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  TEST SUMMARY")
    print(f"{'='*70}")

    total_checks = sum(len(r["issues"]) for r in leg_results)
    # Count individual checks via heuristics
    checked = 0
    passed = 0
    for r in leg_results:
        for iss in r["issues"]:
            checked += 1
        # Count the number of _check and _check_val calls that passed
        # (we can't easily count them retroactively; estimate conservatively)

    # Categorize gaps
    gap_categories = {}
    for issue in all_issues:
        cat = "other"
        if "None" in issue and ("None" in issue):
            cat = "null_values"
            report["gaps"]["null_fields"].append(issue)
        elif "error" in issue.lower() or "fail" in issue.lower():
            cat = "errors"
            report["errors"].append(issue)
        elif "missing" in issue.lower() or "not found" in issue.lower():
            cat = "missing"
            report["gaps"]["missing_fields"].append(issue)
        elif "weather" in issue.lower():
            cat = "weather"
        elif "permit" in issue.lower():
            cat = "permits"
            report["gaps"]["permit_issues"].append(issue)

    summary = {
        "total_legs": len(route_plan.legs),
        "total_issues": len(all_issues),
        "issues_by_leg": {f"L{r['leg_index']} ({r['origin']}→{r['destination']})": len(r["issues"]) for r in leg_results},
        "critical_issues": [i for i in all_issues if any(kw in i for kw in ["ERROR", "ZERO", "NONE", "exceeds", "over_limit"])],
        "gaps_summary": {
            "missing_fields": len(report["gaps"]["missing_fields"]),
            "null_fields": len(report["gaps"]["null_fields"]),
            "airport_issues": len(report["gaps"]["airport_issues"]),
            "customs_issues": len(report["gaps"]["customs_issues"]),
            "permit_issues": len(report["gaps"]["permit_issues"]),
        },
        "mission_legal": route_plan.crew_duty.mission_legal if route_plan.crew_duty else None,
        "overall_status": "PASS" if len(all_issues) == 0 else "ISSUES_FOUND",
    }

    print(f"\n  Legs: {len(route_plan.legs)}/6 planned")
    print(f"  Total issues: {len(all_issues)}")
    print(f"  Critical: {len(summary['critical_issues'])}")
    print(f"  Gaps — missing fields: {len(report['gaps']['missing_fields'])}")
    print(f"  Gaps — null fields: {len(report['gaps']['null_fields'])}")
    print(f"  Gaps — airport issues: {len(report['gaps']['airport_issues'])}")
    print(f"  Gaps — customs issues: {len(report['gaps']['customs_issues'])}")
    print(f"  Gaps — permit issues: {len(report['gaps']['permit_issues'])}")
    print(f"  Mission legal (duty): {route_plan.crew_duty.mission_legal if route_plan.crew_duty else 'N/A'}")
    print(f"  Overall: {summary['overall_status']}")
    print(f"{'='*70}\n")

    report["summary"] = summary
    report["all_issues"] = all_issues

    return report


# ═══════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    report = asyncio.run(run_test())

    # Write the report
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n📄 Test report written to {REPORT_PATH}")
    print(f"   File size: {REPORT_PATH.stat().st_size:,} bytes")

    # Exit with code based on pass/fail
    if report.get("summary", {}).get("overall_status") == "PASS":
        sys.exit(0)
    else:
        sys.exit(report["summary"]["total_issues"] if report["summary"]["total_issues"] < 255 else 1)
