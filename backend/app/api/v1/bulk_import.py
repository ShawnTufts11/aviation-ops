"""Bulk CSV import endpoints — passengers, crew, aircraft."""

from __future__ import annotations

import csv
import io
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_role
from app.core.roles import Role
from app.models.user import User
from app.schemas.passenger import PassengerCreate

router = APIRouter(prefix="/bulk-import", tags=["bulk-import"])

REQUIRED_COLUMNS = {
    "passengers": ["full_name"],
    "crew": ["first_name", "last_name", "email", "role"],
    "aircraft": ["tail_number", "make", "model"],
}


def _read_csv(file: UploadFile) -> tuple[list[dict[str, str]], list[str]]:
    """Parse CSV upload, returning (rows, errors)."""
    content = file.file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)
    if not rows:
        return [], ["CSV file is empty"]
    return rows, []


@router.post("/passengers")
async def import_passengers(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role([Role.ACCOUNTABLE_EXECUTIVE, Role.DIRECTOR_OF_OPERATIONS])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Bulk import passengers from CSV.

    Required column: full_name
    Optional columns: date_of_birth, gender, nationality, passport_number,
                      passport_expiry, email, phone, weight_kg, notes
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    from app.models.passenger import Passenger
    import uuid

    rows, errors = _read_csv(file)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    created = 0
    skipped = 0

    for row in rows:
        name = row.get("full_name", "").strip()
        if not name:
            skipped += 1
            continue

        # Parse optional fields
        dob = None
        if row.get("date_of_birth"):
            try:
                dob = date.fromisoformat(row["date_of_birth"].strip())
            except ValueError:
                pass

        p_expiry = None
        if row.get("passport_expiry"):
            try:
                p_expiry = date.fromisoformat(row["passport_expiry"].strip())
            except ValueError:
                pass

        weight = None
        if row.get("weight_kg"):
            try:
                weight = float(row["weight_kg"].strip())
            except ValueError:
                pass

        # Check for duplicate passport
        passport = row.get("passport_number", "").strip() or None
        if passport:
            from sqlalchemy import select
            dup = await db.execute(
                select(Passenger).where(
                    Passenger.passport_number == passport,
                    Passenger.organization_id == current_user.organization_id,
                )
            )
            if dup.scalar_one_or_none():
                skipped += 1
                continue

        passenger = Passenger(
            id=str(uuid.uuid4()),
            organization_id=current_user.organization_id,
            full_name=name,
            date_of_birth=dob,
            gender=row.get("gender", "").strip() or None,
            nationality=row.get("nationality", "").strip().upper() or None,
            passport_number=passport,
            passport_expiry=p_expiry,
            email=row.get("email", "").strip() or None,
            phone=row.get("phone", "").strip() or None,
            weight_kg=weight,
            notes=row.get("notes", "").strip() or None,
        )
        db.add(passenger)
        created += 1

    await db.commit()

    return {
        "imported": created,
        "skipped": skipped,
        "total": created + skipped,
    }


@router.post("/crew")
async def import_crew(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role([Role.ACCOUNTABLE_EXECUTIVE, Role.DIRECTOR_OF_OPERATIONS])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Bulk import crew from CSV.

    Required: first_name, last_name, email, role
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    from app.models.crew import CrewMember
    import uuid

    rows, errors = _read_csv(file)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    created = 0
    skipped = 0

    for row in rows:
        first = row.get("first_name", "").strip()
        last = row.get("last_name", "").strip()
        email = row.get("email", "").strip()
        role = row.get("role", "").strip().lower()

        if not first or not last or not email or not role:
            skipped += 1
            continue

        license_expiry = None
        if row.get("license_expiry"):
            try:
                license_expiry = date.fromisoformat(row["license_expiry"].strip())
            except ValueError:
                pass

        medical_expiry = None
        if row.get("medical_expiry"):
            try:
                medical_expiry = date.fromisoformat(row["medical_expiry"].strip())
            except ValueError:
                pass

        member = CrewMember(
            id=str(uuid.uuid4()),
            organization_id=current_user.organization_id,
            first_name=first,
            last_name=last,
            email=email,
            role=role,
            phone=row.get("phone", "").strip() or None,
            license_type=row.get("license_type", "").strip() or None,
            license_number=row.get("license_number", "").strip() or None,
            license_expiry=license_expiry,
            medical_expiry=medical_expiry,
            base_airport=row.get("base_airport", "").strip().upper() or None,
            notes=row.get("notes", "").strip() or None,
        )
        db.add(member)
        created += 1

    await db.commit()

    return {"imported": created, "skipped": skipped, "total": created + skipped}


@router.post("/aircraft")
async def import_aircraft(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role([Role.ACCOUNTABLE_EXECUTIVE, Role.DIRECTOR_OF_OPERATIONS])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Bulk import aircraft from CSV.

    Required: tail_number, make, model
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    from app.models.aircraft import Aircraft
    import uuid

    rows, errors = _read_csv(file)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    created = 0
    skipped = 0

    for row in rows:
        tail = row.get("tail_number", "").strip().upper()
        make = row.get("make", "").strip()
        model = row.get("model", "").strip()

        if not tail or not make or not model:
            skipped += 1
            continue

        year = None
        if row.get("year"):
            try:
                year = int(row["year"].strip())
            except ValueError:
                pass

        max_seats = 9
        if row.get("max_seats"):
            try:
                max_seats = int(row["max_seats"].strip())
            except ValueError:
                pass

        aircraft = Aircraft(
            id=str(uuid.uuid4()),
            organization_id=current_user.organization_id,
            tail_number=tail,
            make=make,
            model=model,
            year=year,
            max_seats=max_seats,
            base=row.get("base", "").strip().upper() or "MYNN",
            home_airport=row.get("home_airport", "").strip().upper() or "MYNN",
            status="active",
        )
        db.add(aircraft)
        created += 1

    await db.commit()

    return {"imported": created, "skipped": skipped, "total": created + skipped}
