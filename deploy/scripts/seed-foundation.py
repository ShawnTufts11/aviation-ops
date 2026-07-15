"""
Seed the foundation data: airports database and aircraft performance profiles.

This script populates the core reference data that everything else depends on:
  - ICAO airport database with coordinates, fuel, customs, and permit status
  - Extended aircraft performance profiles (phase-based estimates)

Usage:
    cd ~/projects/pararig-ops/backend
    uv run python ../deploy/scripts/seed-foundation.py

NOTE: Aircraft performance data here are PLANNING ESTIMATES based on POH
public data and type-club averages. The senior pilot / aircraft-specific
POH data should replace these when available.
"""

from __future__ import annotations

import asyncio
import sys
import uuid

sys.path.insert(0, ".")  # noqa: E402

from datetime import datetime, timezone

from app.core.config import settings
from app.core.database import Base, async_session_factory, engine, init_db
from app.models.airport import Airport
from app.models.aircraft import Aircraft, AircraftCategory, AircraftStatus


# ── Airport data ────────────────────────────────────────────────────────

AIRPORTS: list[dict] = [
    # ── Bahamas ──────────────────────────────────────────────────────────
    {
        "icao_code": "MYNN",
        "iata_code": "NAS",
        "name": "Lynden Pindling International Airport",
        "latitude": 25.0390,
        "longitude": -77.4661,
        "timezone": "America/Nassau",
        "elevation_ft": 16,
        "country_code": "BS",
        "region": "New Providence",
        "longest_runway_ft": 11000,
        "runway_surface": "asphalt",
        "has_jet_a": True,
        "has_avgas": True,
        "has_customs": True,
        "has_landing_permit_required": False,
        "has_overflight_permit_required": False,
        "operating_hours": "24hr",
        "notes": "Primary international gateway for Bahamas. Customs pre-clearance available for US-bound.",
    },
    {
        "icao_code": "MYGF",
        "iata_code": "FPO",
        "name": "Grand Bahama International Airport",
        "latitude": 26.5566,
        "longitude": -78.6957,
        "timezone": "America/Nassau",
        "elevation_ft": 7,
        "country_code": "BS",
        "region": "Grand Bahama",
        "longest_runway_ft": 11000,
        "runway_surface": "asphalt",
        "has_jet_a": True,
        "has_avgas": True,
        "has_customs": True,
        "has_landing_permit_required": False,
        "has_overflight_permit_required": False,
        "operating_hours": "24hr",
        "notes": "Freeport — major cargo and passenger hub.",
    },
    {
        "icao_code": "MYAT",
        "iata_code": "ATC",
        "name": "Arthur's Town Airport",
        "latitude": 24.6292,
        "longitude": -75.6736,
        "timezone": "America/Nassau",
        "elevation_ft": 20,
        "country_code": "BS",
        "region": "Cat Island",
        "longest_runway_ft": 5000,
        "runway_surface": "asphalt",
        "has_jet_a": False,
        "has_avgas": True,
        "has_customs": False,
        "has_landing_permit_required": False,
        "has_overflight_permit_required": False,
        "operating_hours": "Sunrise-Sunset",
        "notes": "Domestic — no CIQ facilities.",
    },
    {
        "icao_code": "MYSM",
        "iata_code": "ZSA",
        "name": "San Salvador International Airport",
        "latitude": 24.0633,
        "longitude": -74.5244,
        "timezone": "America/Nassau",
        "elevation_ft": 20,
        "country_code": "BS",
        "region": "San Salvador",
        "longest_runway_ft": 8000,
        "runway_surface": "asphalt",
        "has_jet_a": True,
        "has_avgas": True,
        "has_customs": True,
        "has_landing_permit_required": False,
        "has_overflight_permit_required": False,
        "operating_hours": "Daylight",
        "notes": "Entry point for eastern Bahamas. Customs available with notice.",
    },
    # ── United States ────────────────────────────────────────────────────
    {
        "icao_code": "KMIA",
        "iata_code": "MIA",
        "name": "Miami International Airport",
        "latitude": 25.7959,
        "longitude": -80.2870,
        "timezone": "America/New_York",
        "elevation_ft": 8,
        "country_code": "US",
        "region": "Florida",
        "longest_runway_ft": 13000,
        "runway_surface": "asphalt",
        "has_jet_a": True,
        "has_avgas": True,
        "has_customs": True,
        "has_landing_permit_required": False,
        "has_overflight_permit_required": False,
        "operating_hours": "24hr",
        "notes": "Major international hub. eAPIS required for GA/Part 135 arrivals. Customs pre-clearance available for returning from Bahamas.",
    },
    {
        "icao_code": "KFLL",
        "iata_code": "FLL",
        "name": "Fort Lauderdale-Hollywood International Airport",
        "latitude": 26.0742,
        "longitude": -80.1506,
        "timezone": "America/New_York",
        "elevation_ft": 9,
        "country_code": "US",
        "region": "Florida",
        "longest_runway_ft": 9000,
        "runway_surface": "asphalt",
        "has_jet_a": True,
        "has_avgas": True,
        "has_customs": True,
        "has_landing_permit_required": False,
        "has_overflight_permit_required": False,
        "operating_hours": "24hr",
        "notes": "Popular GA/FBO entry point. eAPIS required. Less congested than MIA.",
    },
    {
        "icao_code": "KOPF",
        "iata_code": "OPF",
        "name": "Miami-Opa Locka Executive Airport",
        "latitude": 25.9070,
        "longitude": -80.2784,
        "timezone": "America/New_York",
        "elevation_ft": 8,
        "country_code": "US",
        "region": "Florida",
        "longest_runway_ft": 8000,
        "runway_surface": "asphalt",
        "has_jet_a": True,
        "has_avgas": True,
        "has_customs": True,
        "has_landing_permit_required": False,
        "has_overflight_permit_required": False,
        "operating_hours": "24hr",
        "notes": "General aviation / reliever airport. Customs available. Good FBOs for Part 135.",
    },
    # ── Mexico ───────────────────────────────────────────────────────────
    {
        "icao_code": "MMUN",
        "iata_code": "CUN",
        "name": "Cancún International Airport",
        "latitude": 21.0364,
        "longitude": -86.8769,
        "timezone": "America/Cancun",
        "elevation_ft": 22,
        "country_code": "MX",
        "region": "Quintana Roo",
        "longest_runway_ft": 11600,
        "runway_surface": "asphalt",
        "has_jet_a": True,
        "has_avgas": True,
        "has_customs": True,
        "has_landing_permit_required": True,
        "has_overflight_permit_required": True,
        "operating_hours": "24hr",
        "notes": "Popular Caribbean entry into Mexico. Landing permit required. Overflight permit needed for Mexican airspace.",
    },
    {
        "icao_code": "MMMX",
        "iata_code": "MEX",
        "name": "Mexico City International Airport (Benito Juárez)",
        "latitude": 19.4363,
        "longitude": -99.0721,
        "timezone": "America/Mexico_City",
        "elevation_ft": 7316,
        "country_code": "MX",
        "region": "Mexico City",
        "longest_runway_ft": 12966,
        "runway_surface": "asphalt",
        "has_jet_a": True,
        "has_avgas": True,
        "has_customs": True,
        "has_landing_permit_required": True,
        "has_overflight_permit_required": True,
        "operating_hours": "24hr",
        "notes": "High elevation (7,300ft). Landing permit + slot required. Overflight permit needed.",
    },
    {
        "icao_code": "MMCZ",
        "iata_code": "CZM",
        "name": "Cozumel International Airport",
        "latitude": 20.5189,
        "longitude": -86.9256,
        "timezone": "America/Cancun",
        "elevation_ft": 15,
        "country_code": "MX",
        "region": "Quintana Roo",
        "longest_runway_ft": 10300,
        "runway_surface": "asphalt",
        "has_jet_a": True,
        "has_avgas": True,
        "has_customs": True,
        "has_landing_permit_required": True,
        "has_overflight_permit_required": True,
        "operating_hours": "0600-2200",
        "notes": "Island airport. Landing permit required for GA/Part 135.",
    },
    # ── Haiti ────────────────────────────────────────────────────────────
    {
        "icao_code": "MTPP",
        "iata_code": "PAP",
        "name": "Toussaint Louverture International Airport",
        "latitude": 18.5800,
        "longitude": -72.2925,
        "timezone": "America/Port-au-Prince",
        "elevation_ft": 122,
        "country_code": "HT",
        "region": "Ouest",
        "longest_runway_ft": 10000,
        "runway_surface": "asphalt",
        "has_jet_a": True,
        "has_avgas": False,
        "has_customs": True,
        "has_landing_permit_required": True,
        "has_overflight_permit_required": True,
        "operating_hours": "0600-1800",
        "notes": "Haiti main international gateway. MTTP landing permit required prior to arrival. PROFODA overflight clearance needed. Security briefing recommended.",
    },
    {
        "icao_code": "MTCH",
        "iata_code": "CAP",
        "name": "Hugo Chávez International Airport (Cap-Haïtien)",
        "latitude": 19.7331,
        "longitude": -72.1947,
        "timezone": "America/Port-au-Prince",
        "elevation_ft": 10,
        "country_code": "HT",
        "region": "Nord",
        "longest_runway_ft": 7600,
        "runway_surface": "asphalt",
        "has_jet_a": True,
        "has_avgas": False,
        "has_customs": True,
        "has_landing_permit_required": True,
        "has_overflight_permit_required": True,
        "operating_hours": "Sunrise-Sunset",
        "notes": "Second international airport. Landing permit required.",
    },
    # ── Cuba ─────────────────────────────────────────────────────────────
    {
        "icao_code": "MUHA",
        "iata_code": "HAV",
        "name": "José Martí International Airport",
        "latitude": 22.9892,
        "longitude": -82.4091,
        "timezone": "America/Havana",
        "elevation_ft": 210,
        "country_code": "CU",
        "region": "La Habana",
        "longest_runway_ft": 13000,
        "runway_surface": "asphalt",
        "has_jet_a": True,
        "has_avgas": True,
        "has_customs": True,
        "has_landing_permit_required": True,
        "has_overflight_permit_required": True,
        "operating_hours": "24hr",
        "notes": "Cuba main international airport. US Treasury OFAC license or specific authorization required. Landing permit + ground handling pre-arranged. Cash fuel only.",
    },
    {
        "icao_code": "MUVR",
        "iata_code": "VRA",
        "name": "Juan Gualberto Gómez Airport (Varadero)",
        "latitude": 23.0344,
        "longitude": -81.4353,
        "timezone": "America/Havana",
        "elevation_ft": 210,
        "country_code": "CU",
        "region": "Matanzas",
        "longest_runway_ft": 11500,
        "runway_surface": "asphalt",
        "has_jet_a": True,
        "has_avgas": True,
        "has_customs": True,
        "has_landing_permit_required": True,
        "has_overflight_permit_required": True,
        "operating_hours": "0700-2300",
        "notes": "Cuba tourist gateway. Same license/permit requirements as HAV.",
    },
    # ── Dominican Republic ──────────────────────────────────────────────
    {
        "icao_code": "MDPC",
        "iata_code": "PUJ",
        "name": "Punta Cana International Airport",
        "latitude": 18.5674,
        "longitude": -68.3634,
        "timezone": "America/Santo_Domingo",
        "elevation_ft": 29,
        "country_code": "DO",
        "region": "La Altagracia",
        "longest_runway_ft": 10000,
        "runway_surface": "asphalt",
        "has_jet_a": True,
        "has_avgas": False,
        "has_customs": True,
        "has_landing_permit_required": False,
        "has_overflight_permit_required": False,
        "operating_hours": "24hr",
        "notes": "Major Caribbean hub. Customs available.",
    },
    {
        "icao_code": "MDST",
        "iata_code": "STI",
        "name": "Cibao International Airport (Santiago)",
        "latitude": 19.4061,
        "longitude": -70.6047,
        "timezone": "America/Santo_Domingo",
        "elevation_ft": 565,
        "country_code": "DO",
        "region": "Santiago",
        "longest_runway_ft": 8200,
        "runway_surface": "asphalt",
        "has_jet_a": True,
        "has_avgas": False,
        "has_customs": True,
        "has_landing_permit_required": False,
        "has_overflight_permit_required": False,
        "operating_hours": "0600-0000",
        "notes": "Internal DR hub. Customs available.",
    },
    # ── Turks & Caicos ──────────────────────────────────────────────────
    {
        "icao_code": "MBPV",
        "iata_code": "PLS",
        "name": "Providenciales International Airport",
        "latitude": 21.7733,
        "longitude": -72.2656,
        "timezone": "America/Grand_Turk",
        "elevation_ft": 15,
        "country_code": "TC",
        "region": "Providenciales",
        "longest_runway_ft": 7600,
        "runway_surface": "asphalt",
        "has_jet_a": True,
        "has_avgas": True,
        "has_customs": True,
        "has_landing_permit_required": False,
        "has_overflight_permit_required": False,
        "operating_hours": "0700-2100",
        "notes": "Turks & Caicos gateway. Customs available.",
    },
    # ── Cayman Islands ──────────────────────────────────────────────────
    {
        "icao_code": "MWCR",
        "iata_code": "GCM",
        "name": "Owen Roberts International Airport (Grand Cayman)",
        "latitude": 19.2928,
        "longitude": -81.3575,
        "timezone": "America/Cayman",
        "elevation_ft": 8,
        "country_code": "KY",
        "region": "Grand Cayman",
        "longest_runway_ft": 7200,
        "runway_surface": "asphalt",
        "has_jet_a": True,
        "has_avgas": True,
        "has_customs": True,
        "has_landing_permit_required": False,
        "has_overflight_permit_required": False,
        "operating_hours": "0700-2100",
        "notes": "Cayman Islands gateway. Customs available. Advanced notice for GA.",
    },
    # ── Jamaica ──────────────────────────────────────────────────────────
    {
        "icao_code": "MKJP",
        "iata_code": "KIN",
        "name": "Norman Manley International Airport (Kingston)",
        "latitude": 17.9357,
        "longitude": -76.7875,
        "timezone": "America/Jamaica",
        "elevation_ft": 10,
        "country_code": "JM",
        "region": "Kingston",
        "longest_runway_ft": 8900,
        "runway_surface": "asphalt",
        "has_jet_a": True,
        "has_avgas": False,
        "has_customs": True,
        "has_landing_permit_required": False,
        "has_overflight_permit_required": False,
        "operating_hours": "24hr",
        "notes": "Jamaica main entry point. Overflight permit required for Jamaican airspace.",
    },
]


# ── Aircraft performance profiles ───────────────────────────────────────

AIRCRAFT_PROFILES: list[dict] = [
    {
        "tail_number": "N701BP",
        "make": "Basler Turbo Conversions",
        "model": "BT-67",
        "year": 2022,
        "serial_number": "BT-67-032",
        "category": AircraftCategory.MULTI_ENGINE_TURBOPROP,
        "mtow_kg": 13154.0,
        "max_seats": 28,
        "max_cargo_kg": 4000.0,
        "fuel_capacity_l": 3028.0,  # ~800 gal
        "base": "MYNN",
        "home_airport": "MYNN",
        "country_reg": "N",
        "status": AircraftStatus.ACTIVE,
        # Performance
        "cruise_speed_kt": 160,
        "cruise_fuel_flow_gph": 85.0,
        "typical_cruise_alt_ft": 10000,
        "climb_speed_kt": 120,
        "climb_rate_fpm": 800,
        "descent_speed_kt": 140,
        "taxi_fuel_gallons": 8.0,
        "range_nm": 1200,
        "max_range_with_reserves_nm": 1000,
        "service_ceiling_ft": 25000,
        "reserve_fuel_minutes": 60,
        # Capabilities
        "overwater_capable": False,
        "known_icing_certified": True,
        "rnp_approach_capable": False,
        "rvsm_capable": False,
        "autopilot_type": "basic",
        "deice_equipped": True,
        "total_airframe_hours": 850.0,
        "total_cycles": 620,
    },
    {
        "tail_number": "C6-PRB",
        "make": "Beechcraft",
        "model": "King Air 350i",
        "year": 2021,
        "serial_number": "KA-350-0123",
        "category": AircraftCategory.MULTI_ENGINE_TURBOPROP,
        "mtow_kg": 6804.0,
        "max_seats": 14,
        "max_cargo_kg": 500.0,
        "fuel_capacity_l": 2082.0,  # ~550 gal
        "base": "MYNN",
        "home_airport": "MYNN",
        "country_reg": "BS",
        "status": AircraftStatus.ACTIVE,
        # Performance
        "cruise_speed_kt": 310,
        "cruise_fuel_flow_gph": 85.0,
        "typical_cruise_alt_ft": 28000,
        "climb_speed_kt": 160,
        "climb_rate_fpm": 2400,
        "descent_speed_kt": 170,
        "taxi_fuel_gallons": 5.0,
        "range_nm": 1800,
        "max_range_with_reserves_nm": 1500,
        "service_ceiling_ft": 35000,
        "reserve_fuel_minutes": 45,
        # Capabilities
        "overwater_capable": True,
        "known_icing_certified": True,
        "rnp_approach_capable": True,
        "rvsm_capable": True,
        "autopilot_type": "fms",
        "deice_equipped": True,
        "total_airframe_hours": 2100.0,
        "total_cycles": 1450,
    },
    {
        "tail_number": "C6-PRV",
        "make": "Beechcraft",
        "model": "King Air 200GT",
        "year": 2019,
        "serial_number": "KA-200-GT045",
        "category": AircraftCategory.MULTI_ENGINE_TURBOPROP,
        "mtow_kg": 5670.0,
        "max_seats": 13,
        "max_cargo_kg": 400.0,
        "fuel_capacity_l": 1779.0,  # ~470 gal
        "base": "MYNN",
        "home_airport": "MYNN",
        "country_reg": "BS",
        "status": AircraftStatus.ACTIVE,
        # Performance
        "cruise_speed_kt": 295,
        "cruise_fuel_flow_gph": 75.0,
        "typical_cruise_alt_ft": 25000,
        "climb_speed_kt": 150,
        "climb_rate_fpm": 2000,
        "descent_speed_kt": 160,
        "taxi_fuel_gallons": 5.0,
        "range_nm": 1500,
        "max_range_with_reserves_nm": 1300,
        "service_ceiling_ft": 35000,
        "reserve_fuel_minutes": 45,
        # Capabilities
        "overwater_capable": True,
        "known_icing_certified": True,
        "rnp_approach_capable": False,  # Older panel, may not have RNP
        "rvsm_capable": True,
        "autopilot_type": "coupled",
        "deice_equipped": True,
        "total_airframe_hours": 4300.0,
        "total_cycles": 3200,
    },
    {
        "tail_number": "C6-PRD",
        "make": "Viking Air",
        "model": "DHC-6 Twin Otter Series 400",
        "year": 2020,
        "serial_number": "DHC6-400-987",
        "category": AircraftCategory.MULTI_ENGINE_TURBOPROP,
        "mtow_kg": 5670.0,
        "max_seats": 19,
        "max_cargo_kg": 1200.0,
        "fuel_capacity_l": 1287.0,  # ~340 gal
        "base": "MYNN",
        "home_airport": "MYNN",
        "country_reg": "BS",
        "status": AircraftStatus.ACTIVE,
        # Performance
        "cruise_speed_kt": 170,
        "cruise_fuel_flow_gph": 55.0,
        "typical_cruise_alt_ft": 10000,
        "climb_speed_kt": 130,
        "climb_rate_fpm": 1300,
        "descent_speed_kt": 140,
        "taxi_fuel_gallons": 4.0,
        "range_nm": 800,
        "max_range_with_reserves_nm": 700,
        "service_ceiling_ft": 25000,
        "reserve_fuel_minutes": 45,
        # Capabilities
        "overwater_capable": True,  # Float/combi config — has rafts
        "known_icing_certified": True,
        "rnp_approach_capable": False,
        "rvsm_capable": False,
        "autopilot_type": "basic",
        "deice_equipped": True,
        "total_airframe_hours": 3200.0,
        "total_cycles": 5800,
        # Short-field capable
        "extra_metadata": {
            "short_field_capable": True,
            "min_runway_landing_ft": 1200,
            "min_runway_takeoff_ft": 1500,
            "float_equipped": False,
            "cargo_door": True,
        },
    },
]


async def seed() -> None:
    """Run the seed — idempotent (upserts by ICAO code and tail number)."""
    import sqlalchemy as sa

    await init_db()

    async with async_session_factory() as session:
        # ── Airports ──────────────────────────────────────────────────────
        existing_airports = set()
        result = await session.execute(sa.select(Airport.icao_code))
        for row in result:
            existing_airports.add(row[0])

        created_airports = 0
        for data in AIRPORTS:
            if data["icao_code"] not in existing_airports:
                apt = Airport(**data)
                session.add(apt)
                created_airports += 1

        await session.commit()

        # ── Aircraft performance ──────────────────────────────────────────
        existing_tails = set()
        result = await session.execute(sa.select(Aircraft.tail_number))
        for row in result:
            existing_tails.add(row[0])

        updated_aircraft = 0
        created_aircraft_count = 0
        org_id = None

        # We need an org — grab the first one
        org_result = await session.execute(
            sa.select(sa.text("id FROM organizations LIMIT 1"))
        )
        row = org_result.first()
        if row:
            org_id = row[0]

        for data in AIRCRAFT_PROFILES:
            tail = data.pop("tail_number")

            if tail in existing_tails:
                # Update performance fields
                stmt = (
                    sa.update(Aircraft)
                    .where(Aircraft.tail_number == tail)
                    .values(**data)
                )
                await session.execute(stmt)
                updated_aircraft += 1
            elif org_id:
                # Create with organization
                ac = Aircraft(
                    id=str(uuid.uuid4()),
                    organization_id=org_id,
                    tail_number=tail,
                    **data,
                )
                session.add(ac)
                created_aircraft_count += 1
            else:
                print("⚠ No organization found — skipping aircraft seed")

        await session.commit()

    # ── Report ────────────────────────────────────────────────────────────
    print(f"✓ Airports: {created_airports} created, {len(AIRPORTS) - created_airports} already exist")
    print(f"✓ Aircraft: {created_aircraft_count} created, {updated_aircraft} updated")
    print("Foundation data seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
