#!/usr/bin/env python3
"""Seed the ParaRig Ops database with demo data for development/testing.

Usage:
    python scripts/seed-data.py               # Uses DATABASE_URL from .env
    python scripts/seed-data.py --db sqlite   # Force SQLite in CWD
    python scripts/seed-data.py --clear       # Drop all data first
"""

import asyncio, os, sys, argparse, uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# ── Demo Data ────────────────────────────────────────────────────

ORG_NAME = "ParaRig Dynamics Aviation"
ORG_SLUG = "pararig-aviation"
ADMIN_EMAIL = "admin@pararig.com"
ADMIN_PASSWORD = "changeme123"  # Dev only!

AIRCRAFT = [
    {
        "tail_number": "C6-PRD",
        "make": "Cessna",
        "model": "208B Grand Caravan",
        "year": 2018,
        "category": "turboprop",
        "mtow_kg": 3969,
        "max_seats": 14,
        "max_cargo_kg": 1400,
        "engines": 1,
        "engine_type": "turboprop",
        "current_cycles": 4523,
        "current_hours": 18732.5,
        "status": "active",
        "base": "MYNN",
        "home_airport": "MYNN",
        "country_reg": "BS",
        "registration_expiry": "2027-06-15",
    },
    {
        "tail_number": "C6-PRV",
        "make": "Cessna",
        "model": "208B Grand Caravan",
        "year": 2020,
        "category": "turboprop",
        "mtow_kg": 3969,
        "max_seats": 14,
        "max_cargo_kg": 1400,
        "engines": 1,
        "engine_type": "turboprop",
        "current_cycles": 2187,
        "current_hours": 8942.3,
        "status": "active",
        "base": "MYNN",
        "home_airport": "MYNN",
        "country_reg": "BS",
        "registration_expiry": "2028-03-20",
    },
]

CREW = [
    {
        "first_name": "James",
        "last_name": "Mitchell",
        "email": "james.mitchell@pararig.com",
        "role": "captain",
        "license_type": "atpl",
        "license_number": "ATP-12345",
        "license_country": "BS",
        "license_expiry": "2027-08-01",
        "medical_class": 1,
        "medical_expiry": "2026-12-15",
        "base_airport": "MYNN",
        "date_of_hire": "2023-01-15",
        "status": "active",
    },
    {
        "first_name": "Sarah",
        "last_name": "Williams",
        "email": "sarah.williams@pararig.com",
        "role": "first_officer",
        "license_type": "cpl",
        "license_number": "CPL-67890",
        "license_country": "BS",
        "license_expiry": "2027-11-20",
        "medical_class": 1,
        "medical_expiry": "2027-03-01",
        "base_airport": "MYNN",
        "date_of_hire": "2024-06-01",
        "status": "active",
    },
    {
        "first_name": "Miguel",
        "last_name": "Torres",
        "email": "miguel.torres@pararig.com",
        "role": "mechanic",
        "license_type": "mechanics",
        "license_number": "MECH-54321",
        "license_country": "BS",
        "license_expiry": "2027-05-10",
        "medical_class": 3,
        "medical_expiry": "2026-10-01",
        "base_airport": "MYNN",
        "date_of_hire": "2023-09-01",
        "status": "active",
    },
]

ROUTES = [
    {"departure": "MYNN", "arrival": "MTPP", "type": "international", "distance_nm": 530, "flight_time_mins": 150},
    {"departure": "MTPP", "arrival": "MYNN", "type": "international", "distance_nm": 530, "flight_time_mins": 140},
    {"departure": "MYNN", "arrival": "MYGF", "type": "domestic", "distance_nm": 93, "flight_time_mins": 35},
    {"departure": "MYNN", "arrival": "MYTK", "type": "domestic", "distance_nm": 42, "flight_time_mins": 20},
]


def seed_database(db_url: str, clear: bool = False):
    print(f"🌱 Seeding database: {db_url}")
    engine = create_engine(db_url)

    # ── Build SQL manually (works with both SQLite and PG) ──
    # We import models after setting up the DB to ensure they're connected

    with engine.begin() as conn:
        if clear:
            print("  Clearing existing data...")
            tables = [
                "financial_records", "audit_logs", "flight_documents",
                "flight_crew", "flights", "maintenance_tasks",
                "aircraft_components", "crew_qualifications", "crew_members",
                "aircraft", "users", "organizations",
            ]
            for table in tables:
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))

    # Import models and create tables
    from app.core.database import Base, init_db
    from app.core.security import hash_password

    asyncio.run(init_db())

    with Session(engine) as session:
        # ── Organization ──
        org_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        org = type("Org", (), {
            "id": org_id, "name": ORG_NAME, "slug": ORG_SLUG,
            "timezone": "America/Nassau", "currency": "USD", "country": "BS",
            "regs": '["FAR-135", "BCAA", "OTAR"]',
            "is_active": True, "settings": "{}",
            "created_at": now, "updated_at": now,
        })
        session.execute(text("""
            INSERT INTO organizations (id, name, slug, timezone, currency, country, regs, is_active, settings, created_at, updated_at)
            VALUES (:id, :name, :slug, :tz, :cur, :country, :regs, :active, :settings, :now, :now)
        """), {
            "id": str(org_id), "name": ORG_NAME, "slug": ORG_SLUG,
            "tz": "America/Nassau", "cur": "USD", "country": "BS",
            "regs": '["FAR-135", "BCAA", "OTAR"]',
            "active": True, "settings": "{}", "now": now,
        })

        # ── Admin User ──
        user_id = uuid.uuid4()
        pwd_hash = hash_password(ADMIN_PASSWORD)
        session.execute(text("""
            INSERT INTO users (id, organization_id, email, password_hash, display_name, phone, role, is_active, mfa_enabled, created_at, updated_at)
            VALUES (:id, :org_id, :email, :pwd, :name, :phone, :role, :active, :mfa, :now, :now)
        """), {
            "id": str(user_id), "org_id": str(org_id),
            "email": ADMIN_EMAIL, "pwd": pwd_hash, "name": "Shawn (Admin)",
            "phone": "+1-242-555-0100", "role": "super_admin",
            "active": True, "mfa": False, "now": now,
        })

        # ── Aircraft ──
        for ac in AIRCRAFT:
            ac_id = uuid.uuid4()
            session.execute(text("""
                INSERT INTO aircraft (id, organization_id, tail_number, make, model, year, category, mtow_kg, max_seats, max_cargo_kg, engines, engine_type, current_cycles, current_hours, status, base, home_airport, country_reg, registration_expiry, is_active, created_at, updated_at)
                VALUES (:id, :org_id, :tail, :make, :model, :year, :cat, :mtow, :seats, :cargo, :eng, :eng_type, :cycles, :hours, :status, :base, :home, :country, :reg_exp, :active, :now, :now)
            """), {
                "id": str(ac_id), "org_id": str(org_id),
                "tail": ac["tail_number"], "make": ac["make"],
                "model": ac["model"], "year": ac["year"],
                "cat": ac["category"], "mtow": ac["mtow_kg"],
                "seats": ac["max_seats"], "cargo": ac["max_cargo_kg"],
                "eng": ac["engines"], "eng_type": ac["engine_type"],
                "cycles": ac["current_cycles"], "hours": ac["current_hours"],
                "status": ac["status"], "base": ac["base"],
                "home": ac["home_airport"], "country": ac["country_reg"],
                "reg_exp": ac["registration_expiry"],
                "active": True, "now": now,
            })

        # ── Crew ──
        for c in CREW:
            crew_id = uuid.uuid4()
            session.execute(text("""
                INSERT INTO crew_members (id, organization_id, first_name, last_name, email, role, license_type, license_number, license_country, license_expiry, medical_class, medical_expiry, base_airport, date_of_hire, status, created_at, updated_at)
                VALUES (:id, :org_id, :first, :last, :email, :role, :lic_type, :lic_num, :lic_country, :lic_exp, :med_class, :med_exp, :base, :hire, :status, :now, :now)
            """), {
                "id": str(crew_id), "org_id": str(org_id),
                "first": c["first_name"], "last": c["last_name"],
                "email": c["email"], "role": c["role"],
                "lic_type": c["license_type"], "lic_num": c["license_number"],
                "lic_country": c["license_country"], "lic_exp": c["license_expiry"],
                "med_class": c["medical_class"], "med_exp": c["medical_expiry"],
                "base": c["base_airport"],
                "hire": c["date_of_hire"], "status": c["status"],
                "now": now,
            })

        # ── Routes ──
        for r in ROUTES:
            route_id = uuid.uuid4()
            session.execute(text("""
                INSERT INTO routes (id, organization_id, departure, arrival, route_type, distance_nm, flight_time_mins, is_active, created_at, updated_at)
                VALUES (:id, :org_id, :dep, :arr, :type, :dist, :time, :active, :now, :now)
            """), {
                "id": str(route_id), "org_id": str(org_id),
                "dep": r["departure"], "arr": r["arrival"],
                "type": r["type"], "dist": r["distance_nm"],
                "time": r["flight_time_mins"],
                "active": True, "now": now,
            })

        session.commit()

    print()
    print("✅ Database seeded successfully!")
    print(f"   Organization: {ORG_NAME} ({ORG_SLUG})")
    print(f"   Admin login:  {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print(f"   Aircraft:     {len(AIRCRAFT)}")
    print(f"   Crew:         {len(CREW)}")
    print(f"   Routes:       {len(ROUTES)}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed ParaRig Ops database")
    parser.add_argument("--db", default=None, help="Database URL (overrides .env)")
    parser.add_argument("--clear", action="store_true", help="Drop all data first")
    args = parser.parse_args()

    db_url = args.db
    if not db_url:
        from app.core.config import settings
        db_url = settings.DATABASE_URL

    # SQLite in CWD if no DB specified and no .env
    if not db_url or db_url == "sqlite+aiosqlite:///./pararig_ops.db":
        project_root = Path(__file__).resolve().parent.parent
        db_path = project_root / "backend" / "pararig_ops.db"
        db_url = f"sqlite+aiosqlite:///{db_path}"

    seed_database(db_url, clear=args.clear)
