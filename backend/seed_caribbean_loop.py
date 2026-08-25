"""
Seed script: Pre-load the Caribbean Loop Challenge demo mission with aircraft,
crew, and passenger data for the Flight Release V1 demo.

Run: python3 seed_caribbean_loop.py
"""

import json
import uuid
import sqlite3
from datetime import datetime, timezone, timedelta

DB_PATH = "/home/shawn/projects/pararig-ops/backend/pararig_ops.db"
ORG_ID = "00000000-0000-0000-0000-000000000001"  # Default org

# ── Aircraft ──────────────────────────────────────────────────────────

AIRCRAFT = [
    {
        "id": str(uuid.uuid4()),
        "organization_id": ORG_ID,
        "tail_number": "N101PB",
        "aircraft_type": "KA350",
        "make": "Beechcraft",
        "model": "King Air 350",
        "category": "multi_engine_turboprop",
        "year": 2018,
        "mtow_kg": 6800,
        "basic_empty_weight_kg": 3800,
        "max_payload_kg": 1500,
        "max_seats": 11,
        "max_range_nm": 1800,
        "cruise_speed_ktas": 310,
        "fuel_type": "jet_a",
        "fuel_capacity_gal": 530,
        "fuel_burn_gph": 130,
        "status": "active",
        "home_base": "MYNN",
        "notes": "Primary demo aircraft — Caribbean Loop Challenge",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "organization_id": ORG_ID,
        "tail_number": "N202PB",
        "aircraft_type": "T300",
        "make": "Cessna",
        "model": "208 Caravan",
        "category": "single_engine_turboprop",
        "year": 2020,
        "mtow_kg": 3960,
        "basic_empty_weight_kg": 2100,
        "max_payload_kg": 1300,
        "max_seats": 9,
        "max_range_nm": 1070,
        "cruise_speed_ktas": 185,
        "fuel_type": "jet_a",
        "fuel_capacity_gal": 335,
        "fuel_burn_gph": 65,
        "status": "active",
        "home_base": "MYNN",
        "notes": "Used for range-flag test leg",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "organization_id": ORG_ID,
        "tail_number": "N303PB",
        "aircraft_type": "K200",
        "make": "Beechcraft",
        "model": "King Air 200",
        "category": "multi_engine_turboprop",
        "year": 2015,
        "mtow_kg": 5670,
        "basic_empty_weight_kg": 3500,
        "max_payload_kg": 1200,
        "max_seats": 9,
        "max_range_nm": 1500,
        "cruise_speed_ktas": 290,
        "fuel_type": "jet_a",
        "fuel_capacity_gal": 470,
        "fuel_burn_gph": 110,
        "status": "active",
        "home_base": "MYNN",
        "notes": "Standby / spare",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "organization_id": ORG_ID,
        "tail_number": "N404PB",
        "aircraft_type": "BT-67",
        "make": "Basler Turbo Conversions",
        "model": "BT-67 (DC-3 conversion)",
        "category": "multi_engine_turboprop",
        "year": 2012,
        "mtow_kg": 13100,
        "basic_empty_weight_kg": 7100,
        "max_payload_kg": 4500,
        "max_seats": 30,
        "max_range_nm": 900,
        "cruise_speed_ktas": 180,
        "fuel_type": "jet_a",
        "fuel_capacity_gal": 900,
        "fuel_burn_gph": 180,
        "status": "in_maintenance",
        "home_base": "MYNN",
        "notes": "Heavy lift — currently in maintenance",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    },
]

# ── Crew ──────────────────────────────────────────────────────────────

CREW = [
    {
        "id": str(uuid.uuid4()),
        "organization_id": ORG_ID,
        "first_name": "James",
        "last_name": "Mitchell",
        "email": "jmitchell@pararig.aero",
        "role": "captain",
        "status": "active",
        "license_type": "atpl",
        "medical_class": "first_class",
        "medical_expiry": "2027-03-15",
        "type_ratings": json.dumps(["ka350", "k200", "b200"]),
        "total_hours": 8500,
        "pic_hours": 6200,
        "sic_hours": 2300,
        "last_flight_date": (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d"),
        "duty_today_minutes": 0,
        "duty_7day_minutes": 180,
        "notes": "Senior captain — Caribbean Loop PIC (inbound)",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "organization_id": ORG_ID,
        "first_name": "Maria",
        "last_name": "Rodriguez",
        "email": "mrodriguez@pararig.aero",
        "role": "first_officer",
        "status": "active",
        "license_type": "cpl",
        "medical_class": "first_class",
        "medical_expiry": "2026-11-20",
        "type_ratings": json.dumps(["ka350", "k200"]),
        "total_hours": 3200,
        "pic_hours": 1500,
        "sic_hours": 1700,
        "last_flight_date": (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d"),
        "duty_today_minutes": 0,
        "duty_7day_minutes": 420,
        "notes": "Caribbean Loop SIC (inbound)",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "organization_id": ORG_ID,
        "first_name": "Robert",
        "last_name": "Chen",
        "email": "rchen@pararig.aero",
        "role": "captain",
        "status": "active",
        "license_type": "atpl",
        "medical_class": "first_class",
        "medical_expiry": "2027-06-01",
        "type_ratings": json.dumps(["ka350", "k200"]),
        "total_hours": 7200,
        "pic_hours": 5000,
        "sic_hours": 2200,
        "last_flight_date": (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d"),
        "duty_today_minutes": 0,
        "duty_7day_minutes": 0,
        "notes": "Relief captain — commercially flown to KMIA, hotel overnight, picks up at Miami",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "organization_id": ORG_ID,
        "first_name": "Ana",
        "last_name": "Torres",
        "email": "atorres@pararig.aero",
        "role": "first_officer",
        "status": "active",
        "license_type": "cpl",
        "medical_class": "first_class",
        "medical_expiry": "2026-08-15",
        "type_ratings": json.dumps(["ka350"]),
        "total_hours": 2800,
        "pic_hours": 1200,
        "sic_hours": 1600,
        "last_flight_date": (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d"),
        "duty_today_minutes": 0,
        "duty_7day_minutes": 0,
        "notes": "Relief SIC — commercially flown to KMIA, hotel overnight",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    },
]


def seed():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Check tables exist
    tables = [row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

    # Seed aircraft
    if "aircraft" in tables:
        existing = cur.execute("SELECT COUNT(*) FROM aircraft").fetchone()[0]
        if existing == 0:
            for ac in AIRCRAFT:
                cur.execute(
                    """INSERT INTO aircraft
                    (id, organization_id, tail_number, aircraft_type, make, model, category,
                     year, mtow_kg, basic_empty_weight_kg, max_payload_kg, max_seats,
                     max_range_nm, cruise_speed_ktas, fuel_type, fuel_capacity_gal,
                     fuel_burn_gph, status, home_base, notes, created_at, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (ac["id"], ac["organization_id"], ac["tail_number"], ac["aircraft_type"],
                     ac["make"], ac["model"], ac["category"], ac["year"],
                     ac["mtow_kg"], ac["basic_empty_weight_kg"], ac["max_payload_kg"],
                     ac["max_seats"], ac["max_range_nm"], ac["cruise_speed_ktas"],
                     ac["fuel_type"], ac["fuel_capacity_gal"], ac["fuel_burn_gph"],
                     ac["status"], ac["home_base"], ac["notes"],
                     ac["created_at"], ac["updated_at"])
                )
            print(f"✅ Seeded {len(AIRCRAFT)} aircraft")
        else:
            print(f"⏩ {existing} aircraft already exist — skipping")
    else:
        print("⚠️  aircraft table not found — skipping")

    # Seed crew
    if "crew_members" in tables:
        existing = cur.execute("SELECT COUNT(*) FROM crew_members").fetchone()[0]
        if existing == 0:
            for c in CREW:
                cur.execute(
                    """INSERT INTO crew_members
                    (id, organization_id, first_name, last_name, email, role, status,
                     license_type, medical_class, medical_expiry, type_ratings,
                     total_hours, pic_hours, sic_hours, last_flight_date,
                     duty_today_minutes, duty_7day_minutes, notes, created_at, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (c["id"], c["organization_id"], c["first_name"], c["last_name"],
                     c["email"], c["role"], c["status"], c["license_type"],
                     c["medical_class"], c["medical_expiry"], c["type_ratings"],
                     c["total_hours"], c["pic_hours"], c["sic_hours"],
                     c["last_flight_date"], c["duty_today_minutes"],
                     c["duty_7day_minutes"], c["notes"], c["created_at"],
                     c["updated_at"])
                )
            print(f"✅ Seeded {len(CREW)} crew members")
        else:
            print(f"⏩ {existing} crew members already exist — skipping")
    else:
        print("⚠️  crew_members table not found — skipping")

    conn.commit()
    conn.close()
    print("\n📋 Caribbean Loop Challenge seed data ready!")
    print("   Route: MYNN → KMIA → MMUN → MTPP → MUHA → MDPC → MYNN")
    print("   Primary: N101PB (King Air 350)")
    print(f"   Crew PIC (inbound): {CREW[0]['first_name']} {CREW[0]['last_name']}")
    print(f"   Relief crew at KMIA: {CREW[2]['first_name']} {CREW[2]['last_name']}")


if __name__ == "__main__":
    seed()
