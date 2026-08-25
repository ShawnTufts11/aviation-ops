"""
Seed test crew with qualifications for 24/7 ops across 4 aircraft.

Run: python3 -m app.scripts.seed_crew
"""
import asyncio, uuid, sys
from datetime import date, timedelta
sys.path.insert(0, 'backend')

from app.core.database import AsyncSession
from app.core.security import hash_password
from app.models.crew import CrewMember, CrewQualification, CrewRole, LicenseType, MedicalClass, QualificationType
from app.models.user import User, Role
from sqlalchemy import select

ORG_ID = "63ff4eec-3c0e-44d0-b140-4e11d89611f1"

CREW = [
    # ── BT-67 crew ──
    {"first":"Marcus","last":"Reeves","role":"captain","license":"atpl","medical":"class_1",
     "email":"marcus@pararig.com","base":"MYNN","quals":[("type_rating","BT67",2025,2027),("proficiency_check","BT67",2025,2026)]},
    {"first":"Diego","last":"Vasquez","role":"captain","license":"atpl","medical":"class_1",
     "email":"diego@pararig.com","base":"MYNN","quals":[("type_rating","BT67",2024,2027),("proficiency_check","BT67",2025,2026)]},
    {"first":"Andre","last":"Fontaine","role":"first_officer","license":"cpl","medical":"class_1",
     "email":"andre@pararig.com","base":"MYNN","quals":[("type_rating","BT67",2025,2026),("type_rating","K35X",2025,2026)]},
    # ── King Air 350 crew ──
    {"first":"Sarah","last":"Chen","role":"captain","license":"atpl","medical":"class_1",
     "email":"sarah@pararig.com","base":"MYNN","quals":[("type_rating","K35X",2024,2027),("proficiency_check","K35X",2025,2026)]},
    {"first":"James","last":"Okonkwo","role":"captain","license":"atpl","medical":"class_1",
     "email":"james@pararig.com","base":"MYNN","quals":[("type_rating","K35X",2024,2026),("type_rating","K200",2025,2027)]},
    {"first":"Elena","last":"Rossi","role":"first_officer","license":"cpl","medical":"class_1",
     "email":"elena@pararig.com","base":"MYNN","quals":[("type_rating","K35X",2025,2026),("type_rating","BT67",2025,2026)]},
    # ── King Air 200 crew ──
    {"first":"Tom","last":"Brennan","role":"captain","license":"atpl","medical":"class_1",
     "email":"tom@pararig.com","base":"MYNN","quals":[("type_rating","K200",2024,2027),("proficiency_check","K200",2025,2026)]},
    {"first":"Kofi","last":"Adjei","role":"first_officer","license":"cpl","medical":"class_1",
     "email":"kofi@pararig.com","base":"MYNN","quals":[("type_rating","K200",2025,2026),("type_rating","T300",2025,2026)]},
    # ── Caravan crew ──
    {"first":"Luis","last":"Martinez","role":"captain","license":"atpl","medical":"class_1",
     "email":"luis@pararig.com","base":"MYNN","quals":[("type_rating","T300",2024,2027),("proficiency_check","T300",2025,2026)]},
    {"first":"Hannah","last":"Berg","role":"first_officer","license":"cpl","medical":"class_1",
     "email":"hannah@pararig.com","base":"MYNN","quals":[("type_rating","T300",2025,2026),("type_rating","K200",2025,2026)]},
    # ── Chief Pilot ──
    {"first":"Shawn","last":"Tufts","role":"captain","license":"atpl","medical":"class_1",
     "email":"shawn.tufts@pararig.com","base":"MYNN",
     "quals":[("type_rating","BT67",2024,2027),("type_rating","K35X",2024,2027),("type_rating","K200",2024,2027),("type_rating","T300",2024,2027),
              ("proficiency_check","BT67",2025,2026),("proficiency_check","K35X",2025,2026),("proficiency_check","K200",2025,2026),("proficiency_check","T300",2025,2026)]},
    # ── Support ──
    {"first":"Maria","last":"Santos","role":"dispatcher","license":None,"medical":None,
     "email":"maria@pararig.com","base":"MYNN","quals":[("hazmat",None,2025,2026),("dgr",None,2025,2026)]},
    {"first":"David","last":"Kim","role":"mechanic","license":"mechanics","medical":None,
     "email":"david@pararig.com","base":"MYNN","quals":[("type_rating","BT67",2024,2027),("type_rating","K35X",2024,2027)]},
]

async def seed():
    async with AsyncSession() as db:
        existing = await db.execute(select(CrewMember).where(CrewMember.organization_id == ORG_ID))
        if existing.scalars().first():
            print("Crew already seeded. Delete crew_members + crew_qualifications tables to re-seed.")
            return

        for c in CREW:
            member = CrewMember(
                id=str(uuid.uuid4()),
                organization_id=ORG_ID,
                first_name=c["first"],
                last_name=c["last"],
                email=c.get("email"),
                role=CrewRole(c["role"]),
                license_type=LicenseType(c["license"]) if c.get("license") else None,
                license_number=f"{c['first'][0]}{c['last'][0]}-{c['role'][:2].upper()}-{hash(c['first']+c['last'])%10000:04d}",
                license_country="US",
                license_expiry=date.today() + timedelta(days=365 * 2),
                medical_class=MedicalClass(c["medical"]) if c.get("medical") else None,
                medical_expiry=date.today() + timedelta(days=180) if c.get("medical") else None,
                base_airport=c.get("base", "MYNN"),
                status="active",
                date_of_hire=date.today() - timedelta(days=365 * 2),
                last_proficiency_date=date.today() - timedelta(days=30),
                last_90d_hours=120.0,
                last_12m_hours=480.0,
            )
            db.add(member)
            await db.flush()

            for qtype, acft, issue_y, exp_y in c["quals"]:
                issued = date(issue_y, 1, 15)
                expiry = date(exp_y, 1, 15) if exp_y else issued + timedelta(days=365)
                qual = CrewQualification(
                    id=str(uuid.uuid4()),
                    crew_id=member.id,
                    qual_type=QualificationType(qtype),
                    aircraft_type=acft,
                    issued_date=issued,
                    expiry_date=expiry,
                    notes="",
                )
                db.add(qual)

        await db.commit()
        print(f"Seeded {len(CREW)} crew members with qualifications.")

asyncio.run(seed())
