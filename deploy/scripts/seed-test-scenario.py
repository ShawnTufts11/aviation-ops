#!/usr/bin/env python3
"""
ParaRig Ops — Full Test Scenario Seed

Generates a complete test fleet for Shawn's 4-aircraft Part 135 operation
(Nassau ↔ Haiti). Creates:

  - 4 aircraft with accurate specs
  - 18 crew members (pilots, mechanics, dispatchers)
  - 10+ routes (Nassau, Haiti, Family Islands)
  - 50+ maintenance tasks with realistic intervals
  - 10 sample flights
  - Compliance documents per aircraft
  - Initial financial records

Usage:
  python3 scripts/seed-test-scenario.py [--url http://localhost:8100]
"""

import argparse, json, os, sys, uuid, urllib.request
from datetime import date, datetime, timedelta
from typing import Any

BASE_URL = "http://127.0.0.1:8100"

# ── Org credentials ─────────────────────────────────────────────
ORG_NAME = "ParaRig Dynamics Aviation"
ORG_SLUG = "pararig-dynamics-2026"
ADMIN_EMAIL = "shawn@pararig.aero"
ADMIN_PASSWORD = "ParaRigOps2026!"

# ── Helper ──────────────────────────────────────────────────────

def api(method: str, path: str, data: dict | None = None, token: str | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method,
        headers={"Content-Type": "application/json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read()) if resp.status != 204 else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"  ⚠ {method} {path} → {e.code}: {err[:120]}")
        return {}

def api_patch(path: str, data: dict, token: str) -> dict:
    """PATCH via http.client"""
    import http.client
    conn = http.client.HTTPConnection("127.0.0.1", 8100, timeout=15)
    conn.request("PATCH", path, body=json.dumps(data).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    resp = conn.getresponse()
    body = resp.read().decode()
    conn.close()
    try:
        return json.loads(body) if body else {}
    except json.JSONDecodeError:
        return {}

# ═══════════════════════════════════════════════════════════════
# 1. REGISTER ORG
# ═══════════════════════════════════════════════════════════════

def step1_register() -> str:
    print("\n=== 1. Register Organization ===")
    result = api("POST", "/api/v1/auth/register", {
        "org_name": ORG_NAME,
        "org_slug": ORG_SLUG,
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
        "display_name": "Shawn (Ops VP)",
        "invite_code": "SEED-TEST-2026",
    })
    if "access_token" in result:
        print(f"  ✅ Org: {ORG_NAME}")
        print(f"  ✅ Admin: {ADMIN_EMAIL}")
        return result["access_token"]
    # Already exists — try login
    print("  ⚠ Org may already exist — logging in...")
    result = api("POST", "/api/v1/auth/login", {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
    })
    if "access_token" in result:
        print(f"  ✅ Logged in as {ADMIN_EMAIL}")
        return result["access_token"]
    print("  ❌ Could not register or login")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════
# 2. AIRCRAFT
# ═══════════════════════════════════════════════════════════════

AIRCRAFT = [
    {
        "tail": "C6-BT67",
        "make": "Basler",
        "model": "BT-67",
        "year": 2008,
        "serial": "BT-67-045",
        "category": "multi_engine_turboprop",
        "mtow_kg": 12700,
        "max_seats": 36,
        "max_cargo_kg": 5000,
        "engines": 2,
        "engine_type": "turboprop",
        "hours": 18450,
        "cycles": 12450,
        "base": "MYNN",
        "cruise_kt": 195,
        "range_nm": 1200,
        "fuel_cap_l": 5300,
        "notes": "Converted DC-3 with PT6A-67R engines. Primary cargo/personnel transport.",
    },
    {
        "tail": "C6-K35X",
        "make": "Beechcraft",
        "model": "Super King Air 350",
        "year": 2015,
        "serial": "BK-350-1234",
        "category": "multi_engine_turboprop",
        "mtow_kg": 6800,
        "max_seats": 11,
        "max_cargo_kg": 1400,
        "engines": 2,
        "engine_type": "turboprop",
        "hours": 5230,
        "cycles": 3890,
        "base": "MYNN",
        "cruise_kt": 310,
        "range_nm": 1800,
        "fuel_cap_l": 1900,
        "notes": "Pressurized cabin. PT6A-60A engines. Executive charter / medevac.",
    },
    {
        "tail": "C6-K200",
        "make": "Beechcraft",
        "model": "Super King Air 200",
        "year": 2012,
        "serial": "BK-200-0892",
        "category": "multi_engine_turboprop",
        "mtow_kg": 5670,
        "max_seats": 9,
        "max_cargo_kg": 1100,
        "engines": 2,
        "engine_type": "turboprop",
        "hours": 7890,
        "cycles": 6210,
        "base": "MYNN",
        "cruise_kt": 289,
        "range_nm": 1580,
        "fuel_cap_l": 1650,
        "notes": "PT6A-42 engines. Cargo variant with large cargo door.",
    },
    {
        "tail": "C6-T300",
        "make": "de Havilland Canada",
        "model": "DHC-6-300 Twin Otter",
        "year": 2010,
        "serial": "DHC-6-456",
        "category": "multi_engine_turboprop",
        "mtow_kg": 5670,
        "max_seats": 20,
        "max_cargo_kg": 2100,
        "engines": 2,
        "engine_type": "turboprop",
        "hours": 12340,
        "cycles": 14200,
        "base": "MYNN",
        "cruise_kt": 160,
        "range_nm": 770,
        "fuel_cap_l": 1380,
        "notes": "STOL capable. PT6A-27 engines. Short/rough field specialist. Family Islands.",
    },
]

def step2_aircraft(token: str) -> dict[str, str]:
    """Create all 4 aircraft, return {tail: id} map."""
    print("\n=== 2. Create Aircraft ===")
    ids = {}
    for ac in AIRCRAFT:
        result = api("POST", "/api/v1/aircraft", {
            "tail_number": ac["tail"],
            "make": ac["make"],
            "model": ac["model"],
            "year": ac["year"],
            "serial_number": ac["serial"],
            "category": ac["category"],
            "mtow_kg": ac["mtow_kg"],
            "max_seats": ac["max_seats"],
            "max_cargo_kg": ac["max_cargo_kg"],
            "engines": ac["engines"],
            "engine_type": ac["engine_type"],
            "base": ac["base"],
            "home_airport": ac["base"],
        }, token)
        if "id" in result:
            ids[ac["tail"]] = result["id"]
            print(f"  ✅ {ac['tail']:8s} — {ac['make']:15s} {ac['model']:22s} ({ac['year']})")
            # Update hours and cycles
            api_patch(f"/api/v1/aircraft/{result['id']}", {
                "total_airframe_hours": ac["hours"],
                "total_cycles": ac["cycles"],
            }, token)
        else:
            print(f"  ❌ {ac['tail']:8s} — failed to create")
    return ids

# ═══════════════════════════════════════════════════════════════
# 3. CREW
# ═══════════════════════════════════════════════════════════════

CREW = [
    # Pilots (15 — covers 4 aircraft round-the-clock with reserves)
    {"first": "James", "last": "Mitchell", "role": "captain", "license": "ATP-12345", "lic_exp": "2027-08-01", "med_exp": "2026-12-15", "hours_90d": 185, "hours_12m": 720},
    {"first": "Sarah", "last": "Williams", "role": "captain", "license": "ATP-12346", "lic_exp": "2027-11-20", "med_exp": "2027-03-01", "hours_90d": 210, "hours_12m": 840},
    {"first": "Michael", "last": "Thompson", "role": "captain", "license": "ATP-12347", "lic_exp": "2028-02-15", "med_exp": "2027-06-01", "hours_90d": 165, "hours_12m": 680},
    {"first": "Carlos", "last": "Rodriguez", "role": "captain", "license": "ATP-12348", "lic_exp": "2027-05-10", "med_exp": "2026-11-01", "hours_90d": 195, "hours_12m": 780},
    {"first": "David", "last": "Chen", "role": "captain", "license": "ATP-12349", "lic_exp": "2027-09-30", "med_exp": "2027-04-15", "hours_90d": 175, "hours_12m": 710},
    {"first": "Emily", "last": "Johnson", "role": "first_officer", "license": "CPL-23451", "lic_exp": "2028-01-10", "med_exp": "2027-08-01", "hours_90d": 145, "hours_12m": 560},
    {"first": "Andre", "last": "Baptiste", "role": "first_officer", "license": "CPL-23452", "lic_exp": "2027-07-15", "med_exp": "2027-02-01", "hours_90d": 130, "hours_12m": 520},
    {"first": "Rebecca", "last": "Taylor", "role": "first_officer", "license": "CPL-23453", "lic_exp": "2028-03-20", "med_exp": "2027-09-01", "hours_90d": 155, "hours_12m": 600},
    {"first": "Jean", "last": "Pierre", "role": "first_officer", "license": "CPL-23454", "lic_exp": "2027-10-05", "med_exp": "2027-05-01", "hours_90d": 140, "hours_12m": 540},
    {"first": "Alex", "last": "Morgan", "role": "first_officer", "license": "CPL-23455", "lic_exp": "2028-04-12", "med_exp": "2027-10-01", "hours_90d": 120, "hours_12m": 480},
    # Shared second-in-command / SIC
    {"first": "Thomas", "last": "Knight", "role": "sic", "license": "CPL-34561", "lic_exp": "2027-12-01", "med_exp": "2027-07-01", "hours_90d": 90, "hours_12m": 360},
    {"first": "Lisa", "last": "Park", "role": "sic", "license": "CPL-34562", "lic_exp": "2028-05-15", "med_exp": "2027-11-01", "hours_90d": 80, "hours_12m": 320},
    # Mechanics (3 — lead + 2 A&Ps)
    {"first": "Miguel", "last": "Torres", "role": "mechanic", "license": "MECH-54321", "lic_exp": "2027-05-10", "med_exp": "2026-10-01", "hours_90d": 0, "hours_12m": 0},
    {"first": "Robert", "last": "Harris", "role": "mechanic", "license": "MECH-54322", "lic_exp": "2027-08-20", "med_exp": "2027-01-15", "hours_90d": 0, "hours_12m": 0},
    {"first": "Daniel", "last": "Sullivan", "role": "mechanic", "license": "MECH-54323", "lic_exp": "2028-02-28", "med_exp": "2027-06-01", "hours_90d": 0, "hours_12m": 0},
    # Dispatchers (2)
    {"first": "Maria", "last": "Cruz", "role": "dispatcher", "license": None, "lic_exp": None, "med_exp": None},
    {"first": "Kevin", "last": "Brown", "role": "dispatcher", "license": None, "lic_exp": None, "med_exp": None},
    # Check airman / training captain
    {"first": "William", "last": "Stevens", "role": "captain", "license": "ATP-12350", "lic_exp": "2028-06-15", "med_exp": "2027-08-01", "hours_90d": 110, "hours_12m": 450},
]

def step3_crew(token: str) -> dict[str, str]:
    """Create all crew members, return {name: id} map."""
    print("\n=== 3. Create Crew (%d members) ===" % len(CREW))
    ids = {}
    for c in CREW:
        result = api("POST", "/api/v1/crew", {
            "first_name": c["first"],
            "last_name": c["last"],
            "role": c["role"],
            "email": f"{c['first'].lower()}.{c['last'].lower()}@pararig.aero",
            "phone": f"+1-242-555-{1000 + CREW.index(c):04d}",
            "license_number": c["license"],
            "license_expiry": c["lic_exp"],
            "medical_expiry": c["med_exp"],
            "base_airport": "MYNN",
            "notes": f"{c['role'].replace('_', ' ').title()} — {'FAR 135 qualified' if c['role'] in ('captain', 'first_officer', 'sic') else 'Ground staff'}",
        }, token)
        if "id" in result:
            name = f"{c['first']} {c['last']}"
            ids[name] = result["id"]
            print(f"  ✅ {c['first']:10s} {c['last']:12s} — {c['role']:15s}")
    return ids

# ═══════════════════════════════════════════════════════════════
# 4. ROUTES
# ═══════════════════════════════════════════════════════════════

ROUTES = [
    ("MYNN", "MTPP", "international", 530, 150, "Nassau → Port-au-Prince (primary)"),
    ("MTPP", "MYNN", "international", 530, 140, "Port-au-Prince → Nassau (primary)"),
    ("MYNN", "MYGF", "domestic", 93, 35, "Nassau → Freeport (Grand Bahama)"),
    ("MYGF", "MYNN", "domestic", 93, 30, "Freeport → Nassau"),
    ("MYNN", "MYTK", "domestic", 42, 20, "Nassau → Treasure Cay (Abaco)"),
    ("MYNN", "MYEH", "domestic", 76, 30, "Nassau → North Eleuthera"),
    ("MYNN", "MYSM", "domestic", 58, 25, "Nassau → San Salvador"),
    ("MYNN", "MYLS", "domestic", 55, 25, "Nassau → Stella Maris (Long Island)"),
    ("MYNN", "MDPP", "international", 410, 110, "Nassau → Puerto Plata (DR)"),
    ("MYNN", "MUDD", "international", 560, 150, "Nassau → Varadero (Cuba) — charter"),
]

def step4_routes(token: str):
    """Create route library."""
    print("\n=== 4. Create Routes ===")
    for dep, arr, rtype, dist, mins, desc in ROUTES:
        result = api("POST", "/api/v1/flights/routes", {
            "departure": dep, "arrival": arr,
            "route_type": rtype,
            "distance_nm": dist, "flight_time_mins": mins,
        }, token)
        if "id" in result:
            print(f"  ✅ {dep} → {arr:4s}  {dist:3d}nm  {mins:2d}min  ({desc})")

# ═══════════════════════════════════════════════════════════════
# 5. MAINTENANCE TASKS
# ═══════════════════════════════════════════════════════════════

MAINTENANCE_TEMPLATES = {
    # Template: (title, task_type, interval_hours, interval_days, is_recurring)
    "common": [
        ("100-Hour Inspection", "100hr", 100, None),
        ("Annual Inspection", "annual", None, 365),
        ("Oil Change (Engines)", "oil_change", 50, None),
        ("Oil Change (APU/GTC)", "oil_change", 100, None),
        ("Landing Gear Inspection", "inspection", 200, None),
        ("Brake Pad Inspection", "inspection", 100, None),
        ("Tire Replacement / Check", "inspection", 150, None),
        ("Pilot Static System Check", "inspection", None, 365),
        ("Transponder Certification", "inspection", None, 730),
        ("ELT Battery Replacement", "inspection", None, 365),
        ("Life Vest Inspection", "inspection", None, 365),
        ("Fire Extinguisher Check", "inspection", None, 365),
        ("Emergency Exit Inspection", "inspection", 200, None),
    ],
    "pt6a": [
        ("Hot Section Inspection (PT6A)", "inspection", 750, None),
        ("Engine Compressor Wash", "inspection", 100, None),
        ("Engine Oil Filter Change", "oil_change", 50, None),
        ("Propeller Governor Check", "inspection", 500, None),
        ("Propeller Overhaul Due", "overhaul", 3600, None),
    ],
    "bt67_specific": [
        ("AD 2023-05-12: DC-3 Wing Spar Inspection", "ad", None, 180),
        ("Cargo Door Latch Inspection", "inspection", 100, None),
        ("Tail Section Inspection (BT-67 mod)", "inspection", 200, None),
    ],
    "kingair_specific": [
        ("Pressurization System Check", "inspection", 200, None),
        ("Cabin Door Seal Inspection", "inspection", 200, None),
        ("Bleed Air Valve Check", "inspection", 300, None),
    ],
    "twinotter_specific": [
        ("STOL Kit Inspection", "inspection", 100, None),
        ("Float / Amphibious Gear Check", "inspection", 50, None),
        ("Cable Tension Check (Flight Controls)", "inspection", 100, None),
    ],
}

def _days_from_now(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()

def step5_maintenance(token: str, aircraft_ids: dict[str, str]):
    """Create maintenance tasks for each aircraft."""
    print("\n=== 5. Create Maintenance Tasks ===")
    total = 0

    for tail, ac_id in aircraft_ids.items():
        templates = list(MAINTENANCE_TEMPLATES["common"])

        if "BT-67" in tail or "PRD" in tail:
            templates += MAINTENANCE_TEMPLATES["pt6a"] + MAINTENANCE_TEMPLATES["bt67_specific"]
        elif "K35" in tail:
            templates += MAINTENANCE_TEMPLATES["pt6a"] + MAINTENANCE_TEMPLATES["kingair_specific"]
        elif "K200" in tail:
            templates += MAINTENANCE_TEMPLATES["pt6a"] + MAINTENANCE_TEMPLATES["kingair_specific"]
        elif "T300" in tail:
            templates += MAINTENANCE_TEMPLATES["pt6a"] + MAINTENANCE_TEMPLATES["twinotter_specific"]

        for title, task_type, interval_hrs, interval_days in templates:
            # Stagger due dates — some overdue, some current
            days_offset = 0
            if total % 3 == 0:
                days_offset = -15  # overdue!
            elif total % 3 == 1:
                days_offset = 14   # due soon
            else:
                days_offset = 60   # coming up

            result = api("POST", "/api/v1/maintenance", {
                "aircraft_id": ac_id,
                "title": title,
                "task_type": task_type,
                "interval_hours": interval_hrs,
                "interval_days": interval_days,
                "scheduled_date": _days_from_now(days_offset),
            }, token)
            if "id" in result:
                total += 1

        print(f"  ✅ {tail:8s} — {len(templates)} tasks created")

    print(f"  Total: {total} maintenance tasks")

# ═══════════════════════════════════════════════════════════════
# 6. SAMPLE FLIGHTS
# ═══════════════════════════════════════════════════════════════

SAMPLE_FLIGHTS = [
    # (tail, dep, arr, dep_time_offset_hours, flight_time_mins, pax, type, status)
    ("C6-BT67", "MYNN", "MTPP", -5, 150, 28, "charter", "completed"),
    ("C6-BT67", "MTPP", "MYNN", -2, 140, 28, "charter", "completed"),
    ("C6-K35X", "MYNN", "MTPP", -4, 110, 8, "charter", "completed"),
    ("C6-K35X", "MTPP", "MYNN", -1, 110, 8, "charter", "completed"),
    ("C6-K200", "MYNN", "MYGF", -6, 35, 6, "cargo", "completed"),
    ("C6-T300", "MYNN", "MYEH", -8, 30, 15, "passenger", "completed"),
    ("C6-T300", "MYEH", "MYNN", -3, 30, 15, "passenger", "completed"),
    ("C6-BT67", "MYNN", "MTPP", -48, 150, 22, "charter", "completed"),
    ("C6-BT67", "MTPP", "MYNN", -46, 140, 22, "charter", "completed"),
    ("C6-K35X", "MYNN", "MDPP", -72, 110, 6, "charter", "completed"),
]

def step6_flights(token: str, aircraft_ids: dict[str, str]):
    """Create sample flights with completion for auto-finance."""
    print("\n=== 6. Create Sample Flights ===")
    now = datetime.utcnow()

    for tail, dep, arr, dep_offset, mins, pax, ftype, status in SAMPLE_FLIGHTS:
        dep_time = now + timedelta(hours=dep_offset)
        arr_time = dep_time + timedelta(minutes=mins)

        result = api("POST", "/api/v1/flights", {
            "aircraft_id": aircraft_ids[tail],
            "flight_type": ftype,
            "departure_airport": dep,
            "arrival_airport": arr,
            "scheduled_departure": dep_time.isoformat() + "Z",
            "scheduled_arrival": arr_time.isoformat() + "Z",
            "passengers_count": pax,
        }, token)

        if "id" in result:
            fid = result["id"]
            # Complete the flight to trigger auto-finance
            if status == "completed":
                actual_dep = dep_time + timedelta(minutes=5)
                actual_arr = actual_dep + timedelta(minutes=mins)
                # Estimate fuel
                fuel_l = round(mins * 8, 1)  # rough estimate
                api_patch(f"/api/v1/flights/{fid}", {
                    "status": "completed",
                    "actual_departure": actual_dep.isoformat() + "Z",
                    "actual_arrival": actual_arr.isoformat() + "Z",
                    "fuel_burned_liters": fuel_l,
                }, token)
            print(f"  ✅ {tail:8s} {dep}→{arr:4s}  {mins:2d}min  {pax}pax  {status}")

# ═══════════════════════════════════════════════════════════════
# 7. COMPLIANCE DOCUMENTS
# ═══════════════════════════════════════════════════════════════

COMPLIANCE_DOCS = [
    ("Air Operator Certificate", "aoc", "BCAA/AOC/2026-001", "BCAA", "2026-01-15", "2027-01-14", "BS"),
    ("Operations Specifications", "operating_specs", "OPSPEC-PRD-001", "FAA/BCAA", "2026-02-01", "2027-02-01", "BS,HT,US"),
    ("Insurance — Fleet Liability", "insurance", "POL-28374-2026", "Lloyd's of London", "2026-03-01", "2027-03-01", "BS,HT,US"),
    ("Bahamas Overflight Permit", "overflight_permit", "BFO-2026-112", "BCAA", "2026-01-01", "2026-12-31", "BS"),
    ("Haiti Landing Permit", "landing_permit", "MTTP-2026-089", "PROFODA (Haiti)", "2026-01-15", "2026-12-31", "HT"),
    ("US Customs Carrier Bond", "customs_clearance", "CBP-2026-4452", "CBP", "2026-01-01", "2027-01-01", "US"),
    ("FAA Part 135 OpSpecs", "operating_specs", "FAA-OPSPEC-135-7721", "FAA", "2026-01-01", "2027-01-01", "US"),
]

def step7_compliance(token: str, aircraft_ids: dict[str, str]):
    """Create compliance documents."""
    print("\n=== 7. Create Compliance Documents ===")
    for title, doc_type, doc_num, authority, issue, expiry, countries in COMPLIANCE_DOCS:
        result = api("POST", "/api/v1/compliance/documents", {
            "title": title,
            "doc_type": doc_type,
            "doc_number": doc_num,
            "issuing_authority": authority,
            "issue_date": issue,
            "expiry_date": expiry,
            "countries": countries,
        }, token)
        if "id" in result:
            print(f"  ✅ {title[:50]:50s} — expires {expiry}")

    # Per-aircraft documents
    for tail, ac_id in aircraft_ids.items():
        api("POST", "/api/v1/compliance/documents", {
            "title": f"Airworthiness Certificate — {tail}",
            "doc_type": "airworthiness_cert",
            "doc_number": f"AW-{tail}-2026",
            "issuing_authority": "BCAA",
            "issue_date": "2026-01-01",
            "expiry_date": "2027-01-01",
            "aircraft_id": ac_id,
            "countries": "BS",
        }, token)
        print(f"  ✅ Airworthiness Cert — {tail}")

# ═══════════════════════════════════════════════════════════════
# 8. SUMMARY
# ═══════════════════════════════════════════════════════════════

def print_summary(creds: dict):
    print("\n" + "=" * 62)
    print("  🎯 ParaRig Ops — TEST SCENARIO SEEDED")
    print("=" * 62)
    print(f"  Organization: {ORG_NAME}")
    print(f"  Login:        {ADMIN_EMAIL}")
    print(f"  Password:     {ADMIN_PASSWORD}")
    print(f"  Dashboard:    http://100.110.158.76:5173")
    print()
    print(f"  Aircraft:     {len(AIRCRAFT)} (BT-67, K350, K200, Twin Otter)")
    print(f"  Crew:         {len(CREW)} (10 pilots, 3 mechanics, 2 dispatchers, 3 captains)")
    print(f"  Routes:       {len(ROUTES)}")
    print(f"  Flights:      {len(SAMPLE_FLIGHTS)} (with auto-finance entries)")
    print()
    print(f"  FAR 135 Staffing:")
    print(f"  — 10 pilots for 4 aircraft: 2 crews per aircraft for 24h ops")
    print(f"  — 3 A&P mechanics: 1 lead + 2 line mx (covers 4 tails)")
    print(f"  — 2 dispatchers for 12h shift coverage")
    print(f"  — Check airman: William Stevens (training/proficiency)")
    print()
    print(f"  ⚠  Some maintenance tasks are OVERDUE — check the Maintenance page")
    print("=" * 62)

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    global BASE_URL
    parser = argparse.ArgumentParser(description="Seed ParaRig Ops test scenario")
    parser.add_argument("--url", default=BASE_URL, help="Backend URL")
    args = parser.parse_args()
    BASE_URL = args.url

    print("🚀 ParaRig Ops — Test Scenario Seeder")
    print(f"   Target: {BASE_URL}")

    token = step1_register()
    ac_ids = step2_aircraft(token)
    step3_crew(token)
    step4_routes(token)
    step5_maintenance(token, ac_ids)
    step6_flights(token, ac_ids)
    step7_compliance(token, ac_ids)

    print_summary({
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
    })

if __name__ == "__main__":
    main()
