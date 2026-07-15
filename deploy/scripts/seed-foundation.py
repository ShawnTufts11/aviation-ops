"""
Seed the foundation data: airports database and aircraft performance profiles.

This script populates the core reference data that everything else depends on:
  - ICAO airport database with coordinates, FBOs, hotels, fuel, customs, maintenance
  - Extended aircraft performance profiles (phase-based estimates)

NOTE: Aircraft performance data here are PLANNING ESTIMATES based on POH
public data and type-club averages. The senior pilot / aircraft-specific
POH data should replace these when available.

Usage:
    cd ~/projects/pararig-ops/backend
    uv run python ../deploy/scripts/seed-foundation.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid

sys.path.insert(0, ".")  # noqa: E402

import sqlalchemy as sa
from app.core.database import Base, async_session_factory, engine, init_db
from app.models.airport import Airport
from app.models.aircraft import Aircraft, AircraftCategory, AircraftStatus


# ═══════════════════════════════════════════════════════════════════════════
# AIRPORT DATA — 19 airports across the Caribbean with rich operational info
# ═══════════════════════════════════════════════════════════════════════════

AIRPORTS: list[dict] = [
    # ── BAHAMAS ────────────────────────────────────────────────────────────
    {
        "icao_code": "MYNN", "iata_code": "NAS",
        "name": "Lynden Pindling International Airport", "city": "Nassau",
        "latitude": 25.0390, "longitude": -77.4661,
        "timezone": "America/Nassau", "elevation_ft": 16,
        "country_code": "BS", "region": "New Providence",
        "longest_runway_ft": 11000, "runway_surface": "asphalt",
        "runway_info": [{"ident": "14/32", "length_ft": 11000, "surface": "asphalt", "lighting": "HIRL", "width_ft": 150}, {"ident": "09/27", "length_ft": 8351, "surface": "asphalt", "lighting": "MIRL", "width_ft": 150}],
        "has_night_ops": True,
        "has_jet_a": True, "has_avgas": True, "fuel_price_jet_a_usd": 6.45, "fuel_price_avgas_usd": 7.80, "fuel_last_updated": "2026-07-01",
        "has_customs": True, "customs_hours": "24hr",
        "has_landing_permit_required": False, "has_overflight_permit_required": False,
        "operating_hours": "24hr",
        "fbo_options": [{"name": "Odyssey Aviation", "phone": "+1-242-377-1000", "frequency": "131.45", "services": ["Jet-A", "Avgas", "Catering", "Crew car", "Lounge", "Customs", "Immigration", "Hotel shuttle"], "fuel_prices": {"jet_a": 6.45, "avgas": 7.80}}, {"name": "Executive Flight Services", "phone": "+1-242-377-0200", "frequency": "131.45", "services": ["Jet-A", "Avgas", "Catering", "Crew car", "Lounge"], "fuel_prices": {"jet_a": 6.55, "avgas": 7.90}}],
        "hotel_options": [{"name": "The Royal at Atlantis", "distance_miles": 5, "shuttle": True, "phone": "+1-242-363-3000", "crew_rate": True, "notes": "Free shuttle, crew rates"}, {"name": "Comfort Suites Paradise Island", "distance_miles": 5, "shuttle": True, "phone": "+1-242-363-3680", "crew_rate": True, "notes": "Budget-friendly, includes breakfast"}, {"name": "TownePlace Suites Nassau", "distance_miles": 1, "shuttle": True, "phone": "+1-242-603-2200", "crew_rate": True, "notes": "Near airport"}],
        "ground_transport": {"rental_cars": ["Hertz", "Avis", "Budget", "Enterprise"], "taxi_available": True, "ride_share": False, "crew_car": True, "notes": "Taxis downtown ~$35"},
        "maintenance_capability": {"on_site_mro": True, "aircraft_types": ["King Air", "Citation", "Caravan", "Twin Otter", "BT-67"], "engine_shop": True, "avionics_shop": True, "aog_support": True, "contacts": [{"name": "MRO Desk", "phone": "+1-242-377-0205"}]},
        "restrictions": [{"type": "noise", "description": "Noise abatement 2300-0700 local", "source": "MYNN AIP"}],
        "notes": "Primary international gateway for Bahamas. Customs pre-clearance for US-bound.", "data_source": "manual", "last_verified": "2026-07-10",
    },
    {
        "icao_code": "MYGF", "iata_code": "FPO",
        "name": "Grand Bahama International Airport", "city": "Freeport",
        "latitude": 26.5566, "longitude": -78.6957,
        "timezone": "America/Nassau", "elevation_ft": 7,
        "country_code": "BS", "region": "Grand Bahama",
        "longest_runway_ft": 11000, "runway_surface": "asphalt",
        "runway_info": [{"ident": "06/24", "length_ft": 11000, "surface": "asphalt", "lighting": "HIRL", "width_ft": 150}],
        "has_night_ops": True,
        "has_jet_a": True, "has_avgas": True, "fuel_price_jet_a_usd": 6.30, "fuel_price_avgas_usd": 7.60, "fuel_last_updated": "2026-06-28",
        "has_customs": True, "customs_hours": "24hr",
        "has_landing_permit_required": False, "has_overflight_permit_required": False,
        "operating_hours": "24hr",
        "fbo_options": [{"name": "Freeport FBO / Bahamas Aviation", "phone": "+1-242-352-7100", "frequency": "122.95", "services": ["Jet-A", "Avgas", "Catering", "Crew car", "Customs"], "fuel_prices": {"jet_a": 6.30, "avgas": 7.60}}],
        "hotel_options": [{"name": "Grand Lucayan Resort", "distance_miles": 3, "shuttle": True, "phone": "+1-242-373-1333"}, {"name": "Pine Bay Suites", "distance_miles": 2, "shuttle": False, "phone": "+1-242-373-1000"}],
        "ground_transport": {"rental_cars": ["Hertz", "Avis"], "taxi_available": True, "crew_car": True, "ride_share": False},
        "maintenance_capability": {"on_site_mro": False, "notes": "Limited line maintenance only"},
        "notes": "Freeport — major cargo and passenger hub.", "data_source": "manual", "last_verified": "2026-06-28",
    },
    {
        "icao_code": "MYAT", "iata_code": "ATC",
        "name": "Arthur's Town Airport", "city": "Arthur's Town",
        "latitude": 24.6292, "longitude": -75.6736,
        "timezone": "America/Nassau", "elevation_ft": 20,
        "country_code": "BS", "region": "Cat Island",
        "longest_runway_ft": 5000, "runway_surface": "asphalt",
        "has_night_ops": False,
        "has_jet_a": False, "has_avgas": True,
        "has_customs": False,
        "has_landing_permit_required": False,
        "operating_hours": "Sunrise-Sunset",
        "notes": "Domestic — no CIQ facilities. Day VFR only.", "data_source": "manual",
    },
    {
        "icao_code": "MYSM", "iata_code": "ZSA",
        "name": "San Salvador International Airport", "city": "San Salvador",
        "latitude": 24.0633, "longitude": -74.5244,
        "timezone": "America/Nassau", "elevation_ft": 20,
        "country_code": "BS", "region": "San Salvador",
        "longest_runway_ft": 8000, "runway_surface": "asphalt",
        "has_night_ops": False,
        "has_jet_a": True, "has_avgas": True,
        "has_customs": True, "customs_hours": "Daylight (call for after-hours)",
        "has_landing_permit_required": False,
        "operating_hours": "Daylight",
        "notes": "Entry point for eastern Bahamas. Customs available with notice.", "data_source": "manual",
    },
    # ── UNITED STATES ──────────────────────────────────────────────────────
    {
        "icao_code": "KMIA", "iata_code": "MIA",
        "name": "Miami International Airport", "city": "Miami",
        "latitude": 25.7959, "longitude": -80.2870,
        "timezone": "America/New_York", "elevation_ft": 8,
        "country_code": "US", "region": "Florida",
        "longest_runway_ft": 13000, "runway_surface": "asphalt",
        "runway_info": [{"ident": "08L/26R", "length_ft": 8600, "surface": "asphalt", "lighting": "HIRL", "width_ft": 150}, {"ident": "08R/26L", "length_ft": 10606, "surface": "asphalt", "lighting": "HIRL", "width_ft": 150}, {"ident": "09/27", "length_ft": 13000, "surface": "asphalt", "lighting": "HIRL", "width_ft": 200}, {"ident": "12/30", "length_ft": 9400, "surface": "asphalt", "lighting": "HIRL", "width_ft": 200}],
        "has_night_ops": True,
        "has_jet_a": True, "has_avgas": True, "fuel_price_jet_a_usd": 5.90, "fuel_price_avgas_usd": 7.10, "fuel_last_updated": "2026-07-08",
        "has_customs": True, "customs_hours": "24hr",
        "has_landing_permit_required": False, "has_overflight_permit_required": False,
        "operating_hours": "24hr",
        "fbo_options": [{"name": "Signature Flight Support MIA", "phone": "+1-305-869-1300", "frequency": "131.75", "services": ["Jet-A", "Avgas", "Catering", "Crew car", "Lounge", "Customs", "Hotel shuttle"], "fuel_prices": {"jet_a": 7.50, "avgas": 8.90}}, {"name": "Jet Aviation MIA", "phone": "+1-305-876-7000", "frequency": "131.75", "services": ["Jet-A", "Avgas", "Catering", "Crew car", "Lounge", "Customs"], "fuel_prices": {"jet_a": 7.80, "avgas": 9.20}}],
        "hotel_options": [{"name": "Miami International Airport Hotel", "distance_miles": 0, "shuttle": False, "phone": "+1-305-871-4100", "notes": "Inside terminal"}, {"name": "Embassy Suites Miami Airport", "distance_miles": 1, "shuttle": True, "phone": "+1-305-634-5000", "crew_rate": True, "notes": "Free breakfast, shuttle"}],
        "ground_transport": {"rental_cars": ["Hertz", "Avis", "Enterprise", "Budget", "National"], "taxi_available": True, "ride_share": True, "crew_car": True},
        "maintenance_capability": {"on_site_mro": True, "aircraft_types": ["All"], "engine_shop": True, "avionics_shop": True, "aog_support": True},
        "notes": "Major international hub. eAPIS required for GA/Part 135 arrivals.", "data_source": "manual", "last_verified": "2026-07-08",
    },
    {
        "icao_code": "KFLL", "iata_code": "FLL",
        "name": "Fort Lauderdale-Hollywood International Airport", "city": "Fort Lauderdale",
        "latitude": 26.0742, "longitude": -80.1506,
        "timezone": "America/New_York", "elevation_ft": 9,
        "country_code": "US", "region": "Florida",
        "longest_runway_ft": 9000, "runway_surface": "asphalt",
        "has_night_ops": True,
        "has_jet_a": True, "has_avgas": True, "fuel_price_jet_a_usd": 5.80, "fuel_price_avgas_usd": 7.00, "fuel_last_updated": "2026-07-08",
        "has_customs": True, "customs_hours": "24hr",
        "has_landing_permit_required": False, "has_overflight_permit_required": False,
        "operating_hours": "24hr",
        "notes": "Popular GA/FBO entry point. eAPIS required. Less congested than MIA.", "data_source": "manual", "last_verified": "2026-07-08",
    },
    {
        "icao_code": "KOPF", "iata_code": "OPF",
        "name": "Miami-Opa Locka Executive Airport", "city": "Opa Locka",
        "latitude": 25.9070, "longitude": -80.2784,
        "timezone": "America/New_York", "elevation_ft": 8,
        "country_code": "US", "region": "Florida",
        "longest_runway_ft": 8000, "runway_surface": "asphalt",
        "runway_info": [{"ident": "09L/27R", "length_ft": 8000, "surface": "asphalt", "lighting": "HIRL", "width_ft": 150}, {"ident": "09R/27L", "length_ft": 4219, "surface": "asphalt", "lighting": "MIRL", "width_ft": 75}, {"ident": "12/30", "length_ft": 5008, "surface": "asphalt", "lighting": "MIRL", "width_ft": 100}],
        "has_night_ops": True,
        "has_jet_a": True, "has_avgas": True, "fuel_price_jet_a_usd": 5.45, "fuel_price_avgas_usd": 6.60, "fuel_last_updated": "2026-07-08",
        "has_customs": True, "customs_hours": "0800-2200 (call for after-hours)",
        "has_landing_permit_required": False, "has_overflight_permit_required": False,
        "operating_hours": "24hr",
        "fbo_options": [{"name": "Miami Jet Services", "phone": "+1-305-687-4500", "frequency": "122.95", "services": ["Jet-A", "Avgas", "Catering", "Crew car", "Lounge", "Customs"], "fuel_prices": {"jet_a": 5.45, "avgas": 6.60}}, {"name": "Castle Air FBO", "phone": "+1-305-685-9600", "frequency": "122.95", "services": ["Jet-A", "Avgas", "Catering", "Crew car"], "fuel_prices": {"jet_a": 5.55, "avgas": 6.70}}],
        "hotel_options": [{"name": "Days Inn by Wyndham Miami Airport North", "distance_miles": 2, "shuttle": True, "phone": "+1-305-769-2750", "crew_rate": True}],
        "ground_transport": {"rental_cars": ["Hertz", "Enterprise"], "taxi_available": True, "crew_car": True, "ride_share": True},
        "maintenance_capability": {"on_site_mro": True, "aircraft_types": ["Turboprop", "Light Jet", "Piston"], "engine_shop": True, "avionics_shop": True, "aog_support": True},
        "notes": "General aviation / reliever. Customs available. Preferred by Part 135 ops.", "data_source": "manual", "last_verified": "2026-07-08",
    },
    # ── MEXICO ─────────────────────────────────────────────────────────────
    {
        "icao_code": "MMUN", "iata_code": "CUN",
        "name": "Cancún International Airport", "city": "Cancún",
        "latitude": 21.0364, "longitude": -86.8769,
        "timezone": "America/Cancun", "elevation_ft": 22,
        "country_code": "MX", "region": "Quintana Roo",
        "longest_runway_ft": 11600, "runway_surface": "asphalt",
        "runway_info": [{"ident": "12R/30L", "length_ft": 11600, "surface": "asphalt", "lighting": "HIRL", "width_ft": 150}, {"ident": "12L/30R", "length_ft": 9200, "surface": "asphalt", "lighting": "HIRL", "width_ft": 150}],
        "has_night_ops": True,
        "has_jet_a": True, "has_avgas": True, "fuel_price_jet_a_usd": 4.80, "fuel_price_avgas_usd": 6.50, "fuel_last_updated": "2026-07-05",
        "has_customs": True, "customs_hours": "24hr",
        "has_landing_permit_required": True, "has_overflight_permit_required": True,
        "operating_hours": "24hr",
        "fbo_options": [{"name": "ASUR Aeropuertos / Servicios", "phone": "+52-998-848-7000", "frequency": "131.75", "services": ["Jet-A", "Avgas", "Catering", "Crew car", "Lounge"], "fuel_prices": {"jet_a": 4.80, "avgas": 6.50}}, {"name": "Universal Aviation Cancun", "phone": "+52-998-193-0290", "services": ["Handling", "Permits", "Crew car", "Hotel booking", "Fuel coordination"]}],
        "hotel_options": [{"name": "Fairfield Inn & Suites Cancun Airport", "distance_miles": 1, "shuttle": True, "phone": "+52-998-886-0600", "crew_rate": True}, {"name": "Hilton Garden Inn Cancun Airport", "distance_miles": 1, "shuttle": True, "phone": "+52-998-887-3000", "crew_rate": True}],
        "ground_transport": {"rental_cars": ["Hertz", "Avis", "Budget", "Europcar"], "taxi_available": True, "crew_car": True, "ride_share": False},
        "maintenance_capability": {"on_site_mro": True, "aircraft_types": ["Turboprop", "Jet", "Piston"], "engine_shop": True, "avionics_shop": False, "aog_support": True},
        "restrictions": [{"type": "permit", "description": "Landing permit required 24+ hrs prior. Overflight permit for Mexican airspace.", "source": "SENEAM/AFAC"}],
        "notes": "Popular Caribbean entry into Mexico. Fuel generally cheaper than Bahamas/US.", "data_source": "manual", "last_verified": "2026-07-05",
    },
    {
        "icao_code": "MMMX", "iata_code": "MEX",
        "name": "Mexico City International Airport (Benito Juárez)", "city": "Mexico City",
        "latitude": 19.4363, "longitude": -99.0721,
        "timezone": "America/Mexico_City", "elevation_ft": 7316,
        "country_code": "MX", "region": "Mexico City",
        "longest_runway_ft": 12966, "runway_surface": "asphalt",
        "runway_info": [{"ident": "05R/23L", "length_ft": 12966, "surface": "asphalt", "lighting": "HIRL", "width_ft": 200}, {"ident": "05L/23R", "length_ft": 12930, "surface": "asphalt", "lighting": "HIRL", "width_ft": 150}],
        "has_night_ops": True,
        "has_jet_a": True, "has_avgas": True, "fuel_price_jet_a_usd": 4.20, "fuel_price_avgas_usd": 5.80, "fuel_last_updated": "2026-07-02",
        "has_customs": True, "customs_hours": "24hr",
        "has_landing_permit_required": True, "has_overflight_permit_required": True,
        "operating_hours": "24hr (slot controlled)",
        "fbo_options": [{"name": "Servicios Aéreos Ejecutivos", "phone": "+52-55-5786-5500", "services": ["Jet-A", "Avgas", "Handling", "Permits", "Crew car", "Lounge"], "fuel_prices": {"jet_a": 4.20, "avgas": 5.80}}],
        "hotel_options": [{"name": "Camino Real Aeropuerto", "distance_miles": 0.5, "shuttle": True, "phone": "+52-55-3003-0101"}, {"name": "Hilton Mexico City Airport", "distance_miles": 0, "shuttle": False, "phone": "+52-55-5130-5300", "notes": "Connected to T1"}],
        "ground_transport": {"rental_cars": ["Hertz", "Avis", "Budget", "Europcar"], "taxi_available": True, "ride_share": True, "crew_car": False},
        "maintenance_capability": {"on_site_mro": True, "aircraft_types": ["All"], "engine_shop": True, "avionics_shop": True, "aog_support": True},
        "restrictions": [{"type": "permit", "description": "Landing permit + slot required. High elevation perf calculation mandatory.", "source": "AFAC/SENEAM"}],
        "notes": "High elevation (7,300ft) — requires performance calculation. Slot controlled.", "data_source": "manual", "last_verified": "2026-07-02",
    },
    {
        "icao_code": "MMCZ", "iata_code": "CZM",
        "name": "Cozumel International Airport", "city": "Cozumel",
        "latitude": 20.5189, "longitude": -86.9256,
        "timezone": "America/Cancun", "elevation_ft": 15,
        "country_code": "MX", "region": "Quintana Roo",
        "longest_runway_ft": 10300, "runway_surface": "asphalt",
        "has_night_ops": True,
        "has_jet_a": True, "has_avgas": True, "fuel_price_jet_a_usd": 4.70, "fuel_price_avgas_usd": 6.40, "fuel_last_updated": "2026-07-05",
        "has_customs": True, "customs_hours": "0600-2200",
        "has_landing_permit_required": True, "has_overflight_permit_required": True,
        "operating_hours": "0600-2200",
        "notes": "Island airport. Landing permit required for GA/Part 135.", "data_source": "manual", "last_verified": "2026-07-05",
    },
    # ── HAITI ──────────────────────────────────────────────────────────────
    {
        "icao_code": "MTPP", "iata_code": "PAP",
        "name": "Toussaint Louverture International Airport", "city": "Port-au-Prince",
        "latitude": 18.5800, "longitude": -72.2925,
        "timezone": "America/Port-au-Prince", "elevation_ft": 122,
        "country_code": "HT", "region": "Ouest",
        "longest_runway_ft": 10000, "runway_surface": "asphalt",
        "runway_info": [{"ident": "10/28", "length_ft": 10000, "surface": "asphalt", "lighting": "HIRL", "width_ft": 150}],
        "has_night_ops": True,
        "has_jet_a": True, "has_avgas": False, "fuel_price_jet_a_usd": 5.20, "fuel_price_avgas_usd": None, "fuel_last_updated": "2026-06-15",
        "has_customs": True, "customs_hours": "0600-1800 (call for after-hours)",
        "has_landing_permit_required": True, "has_overflight_permit_required": True,
        "operating_hours": "0600-1800",
        "fbo_options": [{"name": "National Aviation Services (NAS)", "phone": "+509-2940-0300", "services": ["Jet-A", "Handling", "Permits", "Crew car", "Security briefing"], "fuel_prices": {"jet_a": 5.20}}, {"name": "M&C Aviation Services", "phone": "+509-3701-4000", "services": ["Handling", "Permits", "Crew transport"]}],
        "hotel_options": [{"name": "Marriott Port-au-Prince", "distance_miles": 3, "shuttle": True, "phone": "+509-2816-9800", "notes": "Secure compound, crew rates, armed security"}, {"name": "Best Western Premier Petion-Ville", "distance_miles": 5, "shuttle": False, "phone": "+509-2813-0300", "notes": "Secure area"}],
        "ground_transport": {"rental_cars": ["Budget"], "taxi_available": True, "crew_car": True, "ride_share": False, "notes": "Pre-arranged transport strongly recommended"},
        "maintenance_capability": {"on_site_mro": True, "aircraft_types": ["Turboprop", "Light Jet"], "engine_shop": False, "avionics_shop": False, "aog_support": True, "contacts": [{"name": "MRO Hotline", "phone": "+509-2940-0310"}]},
        "restrictions": [{"type": "security", "description": "Security briefing mandatory. Armed escorts available.", "source": "US Embassy Haiti"}, {"type": "permit", "description": "MTTP landing permit + PROFODA overflight clearance 48hrs prior.", "source": "AAN Haiti"}],
        "notes": "Haiti main gateway. Security briefing recommended for all crew.", "data_source": "manual", "last_verified": "2026-06-15",
    },
    {
        "icao_code": "MTCH", "iata_code": "CAP",
        "name": "Hugo Chávez International Airport (Cap-Haïtien)", "city": "Cap-Haïtien",
        "latitude": 19.7331, "longitude": -72.1947,
        "timezone": "America/Port-au-Prince", "elevation_ft": 10,
        "country_code": "HT", "region": "Nord",
        "longest_runway_ft": 7600, "runway_surface": "asphalt",
        "has_night_ops": False,
        "has_jet_a": True, "has_avgas": False, "fuel_price_jet_a_usd": 5.40, "fuel_last_updated": "2026-06-15",
        "has_customs": True, "customs_hours": "Sunrise-Sunset",
        "has_landing_permit_required": True, "has_overflight_permit_required": True,
        "operating_hours": "Sunrise-Sunset",
        "notes": "Second international airport. Landing permit required.", "data_source": "manual", "last_verified": "2026-06-15",
    },
    # ── CUBA ───────────────────────────────────────────────────────────────
    {
        "icao_code": "MUHA", "iata_code": "HAV",
        "name": "José Martí International Airport", "city": "Havana",
        "latitude": 22.9892, "longitude": -82.4091,
        "timezone": "America/Havana", "elevation_ft": 210,
        "country_code": "CU", "region": "La Habana",
        "longest_runway_ft": 13000, "runway_surface": "asphalt",
        "runway_info": [{"ident": "06/24", "length_ft": 13000, "surface": "asphalt", "lighting": "HIRL", "width_ft": 150}],
        "has_night_ops": True,
        "has_jet_a": True, "has_avgas": True, "fuel_price_jet_a_usd": 4.50, "fuel_price_avgas_usd": 6.00, "fuel_last_updated": "2026-06-20",
        "has_customs": True, "customs_hours": "0700-2300",
        "has_landing_permit_required": True, "has_overflight_permit_required": True,
        "operating_hours": "24hr",
        "fbo_options": [{"name": "ECASA / Cuban Civil Aviation", "phone": "+53-7-266-4133", "services": ["Jet-A", "Avgas", "Handling", "Permits", "Ground transport"], "fuel_prices": {"jet_a": 4.50, "avgas": 6.00}}],
        "hotel_options": [{"name": "Hotel Presidente", "distance_miles": 5, "shuttle": False, "phone": "+53-7-860-8000", "notes": "Near Old Havana"}, {"name": "Melia Habana", "distance_miles": 6, "shuttle": False, "phone": "+53-7-204-8500", "notes": "Crew rates"}],
        "ground_transport": {"rental_cars": ["Cubacar", "Havanautos"], "taxi_available": True, "crew_car": False, "ride_share": False, "notes": "Official taxis only (yellow). Pre-book agent for transport."},
        "maintenance_capability": {"on_site_mro": False, "notes": "No on-site GA MRO. Nearest major maintenance in Cancun or Miami."},
        "restrictions": [{"type": "regulatory", "description": "OFAC license required for US operators. EAR/ITAR restrictions apply.", "source": "OFAC"}, {"type": "permit", "description": "Landing permit + ground handling pre-arranged.", "source": "IACC Cuba"}],
        "notes": "Cash fuel only. US operators require OFAC license. Pre-arrange ground handling.", "data_source": "manual", "last_verified": "2026-06-20",
    },
    {
        "icao_code": "MUVR", "iata_code": "VRA",
        "name": "Juan Gualberto Gómez Airport (Varadero)", "city": "Varadero",
        "latitude": 23.0344, "longitude": -81.4353,
        "timezone": "America/Havana", "elevation_ft": 210,
        "country_code": "CU", "region": "Matanzas",
        "longest_runway_ft": 11500, "runway_surface": "asphalt",
        "has_night_ops": True,
        "has_jet_a": True, "has_avgas": True, "fuel_price_jet_a_usd": 4.40, "fuel_price_avgas_usd": 5.90, "fuel_last_updated": "2026-06-20",
        "has_customs": True, "customs_hours": "0700-2300",
        "has_landing_permit_required": True, "has_overflight_permit_required": True,
        "operating_hours": "0700-2300",
        "notes": "Same license/permit requirements as HAV. Tourist gateway.", "data_source": "manual", "last_verified": "2026-06-20",
    },
    # ── DOMINICAN REPUBLIC ─────────────────────────────────────────────────
    {
        "icao_code": "MDPC", "iata_code": "PUJ",
        "name": "Punta Cana International Airport", "city": "Punta Cana",
        "latitude": 18.5674, "longitude": -68.3634,
        "timezone": "America/Santo_Domingo", "elevation_ft": 29,
        "country_code": "DO", "region": "La Altagracia",
        "longest_runway_ft": 10000, "runway_surface": "asphalt",
        "runway_info": [{"ident": "09/27", "length_ft": 10000, "surface": "asphalt", "lighting": "HIRL", "width_ft": 150}],
        "has_night_ops": True,
        "has_jet_a": True, "has_avgas": False, "fuel_price_jet_a_usd": 4.95, "fuel_price_avgas_usd": None, "fuel_last_updated": "2026-07-01",
        "has_customs": True, "customs_hours": "24hr",
        "has_landing_permit_required": False, "has_overflight_permit_required": False,
        "operating_hours": "24hr",
        "fbo_options": [{"name": "Universal Aviation Punta Cana", "phone": "+1-809-959-0364", "services": ["Jet-A", "Handling", "Permits", "Crew car", "Lounge", "Hotel booking"], "fuel_prices": {"jet_a": 4.95}}, {"name": "Punta Cana FBO / Aeropuertos Dominicanos", "phone": "+1-809-959-0122", "services": ["Jet-A", "Handling", "Crew car", "Customs coordination"], "fuel_prices": {"jet_a": 5.05}}],
        "hotel_options": [{"name": "Westin Punta Cana Resort", "distance_miles": 2, "shuttle": True, "phone": "+1-809-959-1000"}],
        "ground_transport": {"rental_cars": ["Hertz", "Avis", "Budget"], "taxi_available": True, "crew_car": True, "ride_share": False},
        "maintenance_capability": {"on_site_mro": False, "notes": "Limited line maintenance only"},
        "notes": "Major Caribbean hub. Customs available 24hr.", "data_source": "manual", "last_verified": "2026-07-01",
    },
    {
        "icao_code": "MDST", "iata_code": "STI",
        "name": "Cibao International Airport (Santiago)", "city": "Santiago de los Caballeros",
        "latitude": 19.4061, "longitude": -70.6047,
        "timezone": "America/Santo_Domingo", "elevation_ft": 565,
        "country_code": "DO", "region": "Santiago",
        "longest_runway_ft": 8200, "runway_surface": "asphalt",
        "has_night_ops": True,
        "has_jet_a": True, "has_avgas": False, "fuel_price_jet_a_usd": 5.00, "fuel_last_updated": "2026-07-01",
        "has_customs": True, "customs_hours": "0600-0000",
        "has_landing_permit_required": False,
        "operating_hours": "0600-0000",
        "notes": "Internal DR hub. Customs available.", "data_source": "manual", "last_verified": "2026-07-01",
    },
    # ── TURKS & CAICOS ─────────────────────────────────────────────────────
    {
        "icao_code": "MBPV", "iata_code": "PLS",
        "name": "Providenciales International Airport", "city": "Providenciales",
        "latitude": 21.7733, "longitude": -72.2656,
        "timezone": "America/Grand_Turk", "elevation_ft": 15,
        "country_code": "TC", "region": "Providenciales",
        "longest_runway_ft": 7600, "runway_surface": "asphalt",
        "runway_info": [{"ident": "10/28", "length_ft": 7600, "surface": "asphalt", "lighting": "MIRL", "width_ft": 150}],
        "has_night_ops": True,
        "has_jet_a": True, "has_avgas": True, "fuel_price_jet_a_usd": 5.80, "fuel_price_avgas_usd": 7.20, "fuel_last_updated": "2026-06-25",
        "has_customs": True, "customs_hours": "0700-2100",
        "has_landing_permit_required": False,
        "operating_hours": "0700-2100",
        "fbo_options": [{"name": "Provo Air Center", "phone": "+1-649-941-5112", "frequency": "122.95", "services": ["Jet-A", "Avgas", "Catering", "Crew car", "Customs"], "fuel_prices": {"jet_a": 5.80, "avgas": 7.20}}],
        "hotel_options": [{"name": "Grace Bay Club", "distance_miles": 4, "shuttle": True, "phone": "+1-649-946-5050"}, {"name": "Windsor Court", "distance_miles": 3, "shuttle": False, "phone": "+1-649-941-4607"}],
        "ground_transport": {"rental_cars": ["Hertz", "Avis", "Enterprise"], "taxi_available": True, "crew_car": True, "ride_share": False},
        "maintenance_capability": {"on_site_mro": False, "notes": "Line maintenance only"},
        "notes": "Turks & Caicos gateway.", "data_source": "manual", "last_verified": "2026-06-25",
    },
    # ── CAYMAN ISLANDS ─────────────────────────────────────────────────────
    {
        "icao_code": "MWCR", "iata_code": "GCM",
        "name": "Owen Roberts International Airport", "city": "George Town",
        "latitude": 19.2928, "longitude": -81.3575,
        "timezone": "America/Cayman", "elevation_ft": 8,
        "country_code": "KY", "region": "Grand Cayman",
        "longest_runway_ft": 7200, "runway_surface": "asphalt",
        "runway_info": [{"ident": "08/26", "length_ft": 7200, "surface": "asphalt", "lighting": "HIRL", "width_ft": 150}],
        "has_night_ops": True,
        "has_jet_a": True, "has_avgas": True, "fuel_price_jet_a_usd": 6.10, "fuel_price_avgas_usd": 7.50, "fuel_last_updated": "2026-06-22",
        "has_customs": True, "customs_hours": "0700-2100",
        "has_landing_permit_required": False,
        "operating_hours": "0700-2100",
        "fbo_options": [{"name": "Cayman Airways FBO", "phone": "+1-345-949-8200", "frequency": "131.45", "services": ["Jet-A", "Avgas", "Catering", "Crew car", "Customs"], "fuel_prices": {"jet_a": 6.10, "avgas": 7.50}}],
        "hotel_options": [{"name": "Grand Cayman Marriott Resort", "distance_miles": 2, "shuttle": False, "phone": "+1-345-949-0088"}],
        "ground_transport": {"rental_cars": ["Hertz", "Avis", "Budget"], "taxi_available": True, "crew_car": True, "ride_share": False},
        "maintenance_capability": {"on_site_mro": False, "notes": "Line maintenance only"},
        "notes": "Cayman Islands gateway. Advance notice for GA.", "data_source": "manual", "last_verified": "2026-06-22",
    },
    # ── JAMAICA ────────────────────────────────────────────────────────────
    {
        "icao_code": "MKJP", "iata_code": "KIN",
        "name": "Norman Manley International Airport", "city": "Kingston",
        "latitude": 17.9357, "longitude": -76.7875,
        "timezone": "America/Jamaica", "elevation_ft": 10,
        "country_code": "JM", "region": "Kingston",
        "longest_runway_ft": 8900, "runway_surface": "asphalt",
        "runway_info": [{"ident": "12/30", "length_ft": 8900, "surface": "asphalt", "lighting": "HIRL", "width_ft": 150}],
        "has_night_ops": True,
        "has_jet_a": True, "has_avgas": False, "fuel_price_jet_a_usd": 5.50, "fuel_price_avgas_usd": None, "fuel_last_updated": "2026-06-18",
        "has_customs": True, "customs_hours": "24hr",
        "has_landing_permit_required": False,
        "operating_hours": "24hr",
        "fbo_options": [{"name": "Jet Club Jamaica", "phone": "+1-876-924-8000", "frequency": "131.75", "services": ["Jet-A", "Handling", "Crew car", "Customs"], "fuel_prices": {"jet_a": 5.50}}],
        "hotel_options": [{"name": "The Jamaica Pegasus Hotel", "distance_miles": 4, "shuttle": False, "phone": "+1-876-926-3690", "notes": "Business hotel, near New Kingston"}],
        "ground_transport": {"rental_cars": ["Hertz", "Avis", "Budget", "Enterprise"], "taxi_available": True, "crew_car": True, "ride_share": False},
        "maintenance_capability": {"on_site_mro": False, "notes": "Line maintenance only"},
        "notes": "Jamaica main entry point. Overflight permit required.", "data_source": "manual", "last_verified": "2026-06-18",
    },
]


# ── Aircraft performance profiles (unchanged from previous seed) ─────────

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
        "fuel_capacity_l": 3028.0,
        "base": "MYNN",
        "home_airport": "MYNN",
        "country_reg": "N",
        "status": AircraftStatus.ACTIVE,
        "bhw_kg": 8000.0,
        "mlw_kg": 12000.0,
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
        "fuel_capacity_l": 2082.0,
        "base": "MYNN",
        "home_airport": "MYNN",
        "country_reg": "BS",
        "status": AircraftStatus.ACTIVE,
        "bhw_kg": 4500.0,
        "mlw_kg": 6350.0,
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
        "fuel_capacity_l": 1779.0,
        "base": "MYNN",
        "home_airport": "MYNN",
        "country_reg": "BS",
        "status": AircraftStatus.ACTIVE,
        "bhw_kg": 3800.0,
        "mlw_kg": 5400.0,
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
        "overwater_capable": True,
        "known_icing_certified": True,
        "rnp_approach_capable": False,
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
        "fuel_capacity_l": 1287.0,
        "base": "MYNN",
        "home_airport": "MYNN",
        "country_reg": "BS",
        "status": AircraftStatus.ACTIVE,
        "bhw_kg": 3250.0,
        "mlw_kg": 5300.0,
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
        "overwater_capable": True,
        "known_icing_certified": True,
        "rnp_approach_capable": False,
        "rvsm_capable": False,
        "autopilot_type": "basic",
        "deice_equipped": True,
        "total_airframe_hours": 3200.0,
        "total_cycles": 5800,
        "extra_metadata": {"short_field_capable": True, "min_runway_landing_ft": 1200, "min_runway_takeoff_ft": 1500, "float_equipped": False, "cargo_door": True},
    },
]


# ── Seed execution ──────────────────────────────────────────────────────

async def seed() -> None:
    """Run the seed — idempotent (upserts by ICAO code and tail number)."""
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

        org_result = await session.execute(sa.text("SELECT id FROM organizations LIMIT 1"))
        row = org_result.first()
        if row:
            org_id = row[0]

        for data in AIRCRAFT_PROFILES:
            tail = data.pop("tail_number")

            if tail in existing_tails:
                stmt = sa.update(Aircraft).where(Aircraft.tail_number == tail).values(**data)
                await session.execute(stmt)
                updated_aircraft += 1
            elif org_id:
                ac = Aircraft(id=str(uuid.uuid4()), organization_id=org_id, tail_number=tail, **data)
                session.add(ac)
                created_aircraft_count += 1
            else:
                print("⚠ No organization found — skipping aircraft seed")

        await session.commit()

    print(f"✓ Airports: {created_airports} created, {len(AIRPORTS) - created_airports} already exist")
    print(f"✓ Aircraft: {created_aircraft_count} created, {updated_aircraft} updated")
    print("Foundation data seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
