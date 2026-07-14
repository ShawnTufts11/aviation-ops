#!/usr/bin/env python3
"""Seed test data for user's org — direct DB insert."""

import asyncio, uuid, sys
from datetime import date, datetime, timezone, timedelta
sys.path.insert(0, '/home/shawn/projects/pararig-ops/backend')

from app.core.database import async_session_factory
from app.models.organization import Organization
from app.models.user import User
from app.models.aircraft import Aircraft
from app.models.crew import CrewMember
from app.models.flight import Flight, Route, FlightType, FlightStatus
from app.models.maintenance import MaintenanceTask
from app.models.document import Document, DocumentType, DocumentStatus
from app.models.finance import FinancialRecord, RecordType, CostCategory
from sqlalchemy import select
from app.models.maintenance import MaintenanceTaskType, MaintenanceTaskStatus
from app.models.flight import FlightType

AIRCRAFT = [
    {"tail": "C6-BT67", "make": "Basler", "model": "BT-67", "year": 2008, "seats": 32, "range": 1200, "cruise": 195, "mtow": 12700, "hours": 12500, "cycles": 8400},
    {"tail": "C6-K35X", "make": "Beechcraft", "model": "Super King Air 350", "year": 2015, "seats": 11, "range": 1806, "cruise": 310, "mtow": 6800, "hours": 3400, "cycles": 2100},
    {"tail": "C6-K200", "make": "Beechcraft", "model": "Super King Air 200", "year": 2012, "seats": 9, "range": 1578, "cruise": 289, "mtow": 5670, "hours": 5800, "cycles": 3900},
    {"tail": "C6-T300", "make": "de Havilland Canada", "model": "DHC-6-300 Twin Otter", "year": 2010, "seats": 20, "range": 770, "cruise": 160, "mtow": 5670, "hours": 7200, "cycles": 6200},
]

CREW = [
    {"first": "James", "last": "Mitchell", "role": "captain", "license": "ATP-12345", "lic_exp": "2027-08-01", "med_exp": "2026-12-15"},
    {"first": "Sarah", "last": "Williams", "role": "captain", "license": "ATP-12346", "lic_exp": "2027-09-01", "med_exp": "2026-11-20"},
    {"first": "Michael", "last": "Thompson", "role": "captain", "license": "ATP-12347", "lic_exp": "2027-10-01", "med_exp": "2026-10-30"},
    {"first": "Carlos", "last": "Rodriguez", "role": "captain", "license": "ATP-12348", "lic_exp": "2027-11-01", "med_exp": "2026-09-15"},
    {"first": "David", "last": "Chen", "role": "captain", "license": "ATP-12349", "lic_exp": "2027-07-01", "med_exp": "2026-08-01"},
    {"first": "Emily", "last": "Johnson", "role": "first_officer", "license": "CPL-23451", "lic_exp": "2027-06-01", "med_exp": "2026-10-01"},
    {"first": "Andre", "last": "Baptiste", "role": "first_officer", "license": "CPL-23452", "lic_exp": "2027-05-01", "med_exp": "2027-01-15"},
    {"first": "Rebecca", "last": "Taylor", "role": "first_officer", "license": "CPL-23453", "lic_exp": "2027-04-01", "med_exp": "2026-12-01"},
    {"first": "Jean", "last": "Pierre", "role": "first_officer", "license": "CPL-23454", "lic_exp": "2027-03-01", "med_exp": "2026-11-01"},
    {"first": "Alex", "last": "Morgan", "role": "first_officer", "license": "CPL-23455", "lic_exp": "2026-12-01", "med_exp": "2026-10-15"},
    {"first": "Thomas", "last": "Knight", "role": "sic", "license": "CPL-23456", "lic_exp": "2027-02-01", "med_exp": "2026-09-01"},
    {"first": "Lisa", "last": "Park", "role": "sic", "license": "CPL-23457", "lic_exp": "2027-01-01", "med_exp": "2026-08-15"},
    {"first": "Miguel", "last": "Torres", "role": "mechanic", "license": "A&P-78901", "lic_exp": "2027-12-01", "med_exp": None},
    {"first": "Robert", "last": "Harris", "role": "mechanic", "license": "A&P-78902", "lic_exp": "2027-11-01", "med_exp": None},
    {"first": "Daniel", "last": "Sullivan", "role": "mechanic", "license": "A&P-78903", "lic_exp": "2027-10-01", "med_exp": None},
    {"first": "Maria", "last": "Cruz", "role": "dispatcher", "license": "DISP-001", "lic_exp": "2027-06-01", "med_exp": None},
    {"first": "Kevin", "last": "Brown", "role": "dispatcher", "license": "DISP-002", "lic_exp": "2027-05-01", "med_exp": None},
    {"first": "William", "last": "Stevens", "role": "captain", "license": "ATP-12350", "lic_exp": "2027-08-15", "med_exp": "2027-02-01", "notes": "Check airman"},
]

ROUTES_DATA = [
    ("MYNN", "MTPP", 530, 150), ("MTPP", "MYNN", 530, 140),
    ("MYNN", "MYGF", 93, 35), ("MYGF", "MYNN", 93, 30),
    ("MYNN", "MYTK", 42, 20), ("MYNN", "MYEH", 76, 30),
    ("MYNN", "MYSM", 58, 25), ("MYNN", "MYLS", 55, 25),
    ("MYNN", "MDPP", 410, 110), ("MYNN", "MUDD", 560, 150),
]

MX_TEMPLATES = [
    ("100-Hour Inspection", MaintenanceTaskType.INSPECTION, 100, None, "FAR 135.419"),
    ("Annual Inspection", MaintenanceTaskType.INSPECTION, None, 365, "FAR 135.421"),
    ("Oil Change", MaintenanceTaskType.OIL_CHANGE, 50, None, "Mfr spec"),
    ("Landing Gear Inspection", MaintenanceTaskType.INSPECTION, 200, 180, "FAR 135.421"),
    ("Pitot-Static Test", MaintenanceTaskType.INSPECTION, None, 365, "FAR 91.411"),
    ("Transponder Test", MaintenanceTaskType.INSPECTION, None, 730, "FAR 91.413"),
    ("ELT Battery", MaintenanceTaskType.REPAIR, None, 365, "FAR 91.207"),
    ("Emergency Equipment Check", MaintenanceTaskType.INSPECTION, None, 90, "FAR 135.179"),
    ("Engine Compressor Wash", MaintenanceTaskType.REPAIR, 100, None, "PT6A manual"),
    ("Hot Section Inspection", MaintenanceTaskType.INSPECTION, 600, None, "PT6A manual"),
    ("Propeller Governor Check", MaintenanceTaskType.INSPECTION, 300, None, "Hartzell spec"),
    ("Fuel Nozzle Inspection", MaintenanceTaskType.INSPECTION, 300, None, "Mfr spec"),
    ("Pressurization Check", MaintenanceTaskType.INSPECTION, 200, 365, "Beechcraft manual"),
    ("Bleed Air Valve Insp", MaintenanceTaskType.INSPECTION, 400, None, "Beechcraft manual"),
    ("Nose Gear Overhaul", MaintenanceTaskType.OVERHAUL, 1500, None, "Beechcraft manual"),
]

DOCS = [
    ("Air Operator Certificate", DocumentType.AOC, "BCAA", "2027-01-14"),
    ("Operations Specifications", DocumentType.OPERATING_SPECS, "BCAA", "2027-02-01"),
    ("Insurance — Fleet Liability", DocumentType.INSURANCE, "Lloyd's", "2027-03-01"),
    ("Bahamas Overflight Permit", DocumentType.OVERFLIGHT_PERMIT, "BCAA", "2026-12-31"),
    ("Haiti Landing Permit", DocumentType.LANDING_PERMIT, "ANAC Haiti", "2026-12-31"),
    ("US Customs Carrier Bond", DocumentType.CUSTOMS_CLEARANCE, "CBP", "2027-01-01"),
    ("FAA Part 135 OpSpecs", DocumentType.OPERATING_SPECS, "FAA", "2027-01-01"),
]

FLIGHTS_DATA = [
    ("C6-BT67", "MYNN", "MTPP", -5, 150, 28),
    ("C6-BT67", "MTPP", "MYNN", -2, 140, 28),
    ("C6-K35X", "MYNN", "MTPP", -4, 110, 8),
    ("C6-K35X", "MTPP", "MYNN", -1, 110, 8),
    ("C6-K200", "MYNN", "MYGF", -6, 35, 6),
    ("C6-T300", "MYNN", "MYEH", -8, 30, 15),
    ("C6-T300", "MYEH", "MYNN", -3, 30, 15),
    ("C6-BT67", "MYNN", "MTPP", -48, 150, 22),
    ("C6-BT67", "MTPP", "MYNN", -46, 140, 22),
    ("C6-K35X", "MYNN", "MDPP", -72, 110, 6),
]

async def main():
    async with async_session_factory() as db:
        r = await db.execute(select(User).where(User.email == "shawn.tufts@pararigdynamicsllc.com"))
        user = r.scalar_one_or_none()
        if not user:
            print("❌ User not found")
            return
        oid = user.organization_id
        print(f"✅ Org: {oid[:8]}")

        r = await db.execute(select(Aircraft).where(Aircraft.organization_id == oid).limit(1))
        if r.scalar_one_or_none():
            print("⚠ Data already exists — delete DB or skip")
            return

        today = date.today()
        now = datetime.now(timezone.utc)
        ac_ids = {}

        for a in AIRCRAFT:
            ac = Aircraft(id=str(uuid.uuid4()), organization_id=oid,
                tail_number=a["tail"], make=a["make"], model=a["model"],
                serial_number=f"{a['make'][:3].upper()}-{a['year']}-{uuid.uuid4().hex[:6].upper()}",
                category="multi_engine_turboprop",
                year=a["year"], max_seats=a["seats"], range_nm=a["range"],
                cruise_speed_kt=a["cruise"], mtow_kg=a["mtow"],
                total_airframe_hours=a["hours"], total_cycles=a["cycles"],
                base="MYNN", home_airport="MYNN", status="active")
            db.add(ac)
            ac_ids[a["tail"]] = ac.id
            print(f"  ✈️  {a['tail']}")

        for c in CREW:
            le = datetime.strptime(c["lic_exp"], "%Y-%m-%d").date() if c.get("lic_exp") else None
            me = datetime.strptime(c["med_exp"], "%Y-%m-%d").date() if c.get("med_exp") else None
            db.add(CrewMember(id=str(uuid.uuid4()), organization_id=oid,
                first_name=c["first"], last_name=c["last"],
                email=f"{c['first'].lower()}.{c['last'].lower()}@pararig.aero",
                role=c["role"], license_number=c.get("license"),
                license_expiry=le, medical_expiry=me, base_airport="MYNN",
                status="active", notes=c.get("notes","")))
        print(f"  👥 {len(CREW)} crew")

        for dep, arr, dist, mins in ROUTES_DATA:
            db.add(Route(id=str(uuid.uuid4()), organization_id=oid,
                departure=dep, arrival=arr, distance_nm=dist,
                flight_time_mins=mins, is_active=True))
        print(f"  🗺️  {len(ROUTES_DATA)} routes")
        await db.flush()

        tcount = 0
        for tail, aid in ac_ids.items():
            for i, (title, tp, ih, idy, ref) in enumerate(MX_TEMPLATES):
                doff = [-15, 10, 60, 30, 90, 0, 45, 120][i % 8]
                st = MaintenanceTaskStatus.OVERDUE if doff < 0 else MaintenanceTaskStatus.SCHEDULED
                db.add(MaintenanceTask(id=str(uuid.uuid4()), organization_id=oid,
                    aircraft_id=aid, title=title, task_type=tp,
                    status=st, interval_hours=ih, interval_days=idy,
                    reference=ref, scheduled_date=today + timedelta(days=doff)))
                tcount += 1
        print(f"  🔧 {tcount} mx tasks")
        await db.flush()

        fcount = 0
        crew_ids = []
        r = await db.execute(select(CrewMember).where(CrewMember.organization_id == oid).limit(1))
        pic = r.scalar_one_or_none()
        pic_id = pic.id if pic else None
        for tail, dep, arr, hoff, mins, pax in FLIGHTS_DATA:
            sd = now + timedelta(hours=hoff)
            sa = sd + timedelta(minutes=mins)
            db.add(Flight(id=str(uuid.uuid4()), organization_id=oid,
                aircraft_id=ac_ids[tail], flight_number=f"PRG-{1000+fcount}",
                departure_airport=dep, arrival_airport=arr,
                flight_type=FlightType.CHARTER, status=FlightStatus.COMPLETED,
                scheduled_departure=sd, scheduled_arrival=sa,
                actual_departure=sd + timedelta(minutes=5),
                actual_arrival=sa + timedelta(minutes=3),
                flight_time_hours=mins / 60.0, passengers_count=pax,
                fuel_burned_liters=mins * 2.5, pilot_in_command=pic_id))
            fcount += 1
        print(f"  ✈️  {fcount} flights")
        await db.flush()

        for title, dt, auth, exp_str in DOCS:
            exp = datetime.strptime(exp_str, "%Y-%m-%d").date()
            db.add(Document(id=str(uuid.uuid4()), organization_id=oid,
                title=title, doc_type=dt, issuing_authority=auth,
                issue_date=today, expiry_date=exp, status=DocumentStatus.CURRENT))
        for a in AIRCRAFT:
            db.add(Document(id=str(uuid.uuid4()), organization_id=oid,
                title=f"Airworthiness Cert — {a['tail']}", doc_type=DocumentType.AIRWORTHINESS_CERT,
                issuing_authority="BCAA", issue_date=today,
                expiry_date=today + timedelta(days=365), status=DocumentStatus.CURRENT))
        print(f"  📄 Documents")

        r = await db.execute(select(Flight).where(Flight.organization_id == oid, Flight.status == FlightStatus.COMPLETED))
        for fl in r.scalars().all():
            rev = (fl.passengers_count or 6) * 350
            cost = (fl.flight_time_hours or 1) * 15 * 60
            d = (fl.actual_arrival.date() if fl.actual_arrival else today)
            db.add(FinancialRecord(id=str(uuid.uuid4()), organization_id=oid,
                aircraft_id=fl.aircraft_id, flight_id=fl.id,
                record_type=RecordType.REVENUE, amount=rev, currency="USD",
                category=CostCategory.CHARTER_REVENUE, description=f"Flight {fl.flight_number}", entry_date=d))
            db.add(FinancialRecord(id=str(uuid.uuid4()), organization_id=oid,
                aircraft_id=fl.aircraft_id, flight_id=fl.id,
                record_type=RecordType.COST, amount=cost, currency="USD",
                category=CostCategory.FUEL, description=f"Cost {fl.flight_number}", entry_date=d))
        print(f"  💰 Finance")

        await db.commit()
        print(f"\n✅ Seeded: {len(AIRCRAFT)} aircraft, {len(CREW)} crew, {tcount} mx tasks, {fcount} flights")

asyncio.run(main())
