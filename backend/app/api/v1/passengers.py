"""Passenger database CRUD — repeat client profiles."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc, or_, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_org_membership, require_role, require_pii_clearance, has_pii_clearance
from app.core.roles import Role
from app.models.passenger import Passenger
from app.models.user import User
from app.schemas.passenger import PassengerCreate, PassengerResponse, PassengerUpdate

router = APIRouter(prefix="/passengers", tags=["passengers"])


@router.get("")
async def list_passengers(
    search: str | None = Query(None, alias="q"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List passengers with search. Used for manifest auto-complete."""
    conditions = [Passenger.organization_id == current_user.organization_id]

    if search:
        like = f"%{search}%"
        conditions.append(
            Passenger.full_name.ilike(like)
            | Passenger.passport_number.ilike(like)
            | Passenger.nationality.ilike(like)
        )

    query = select(Passenger).where(*conditions).order_by(Passenger.full_name.asc())

    count_q = select(sa_func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)

    def _redact(p: Passenger) -> dict:
        """Strip PII for users without clearance."""
        d = PassengerResponse.model_validate(p).model_dump()
        if not has_pii_clearance(current_user):
            d["passport_number"] = "****"
            d["passport_expiry"] = None
            d["ssn"] = None
            d["id_number"] = "****"
            d["email"] = None
            d["phone"] = None
            d["date_of_birth"] = None
            d["gender"] = None
            d["notes"] = None
        return d

    return {
        "data": [_redact(p) for p in result.scalars().all()],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_passenger(
    body: PassengerCreate,
    current_user: User = Depends(require_pii_clearance()),
    db: AsyncSession = Depends(get_db),
) -> PassengerResponse:
    """Add a new passenger profile. Enforces unique passport/SSN."""
    # Check duplicates
    if body.passport_number:
        dup = await db.execute(
            select(Passenger).where(
                Passenger.passport_number == body.passport_number,
                Passenger.organization_id == current_user.organization_id,
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail="Passport number already exists in your database",
            )

    passenger = Passenger(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        full_name=body.full_name,
        date_of_birth=body.date_of_birth,
        gender=body.gender,
        nationality=body.nationality,
        passport_number=body.passport_number,
        passport_expiry=body.passport_expiry,
        id_number=body.id_number,
        ssn=body.ssn,
        email=body.email,
        phone=body.phone,
        weight_kg=body.weight_kg,
        notes=body.notes,
        first_flight=date.today(),
        last_flight=date.today(),
        total_flights=0,
    )
    db.add(passenger)
    await db.commit()
    await db.refresh(passenger)
    return PassengerResponse.model_validate(passenger)


@router.get("/{passenger_id}")
async def get_passenger(
    passenger_id: str,
    current_user: User = Depends(require_pii_clearance()),
    db: AsyncSession = Depends(get_db),
) -> PassengerResponse:
    """Get a single passenger profile."""
    p = await db.get(Passenger, passenger_id)
    if not p or p.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Passenger not found")
    return PassengerResponse.model_validate(p)


@router.patch("/{passenger_id}")
async def update_passenger(
    passenger_id: str,
    body: PassengerUpdate,
    current_user: User = Depends(require_pii_clearance()),
    db: AsyncSession = Depends(get_db),
) -> PassengerResponse:
    """Update a passenger profile."""
    p = await db.get(Passenger, passenger_id)
    if not p or p.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Passenger not found")

    update_data = body.model_dump(exclude_unset=True)

    # Check passport uniqueness before updating
    if "passport_number" in update_data and update_data["passport_number"]:
        dup = await db.execute(
            select(Passenger).where(
                Passenger.passport_number == update_data["passport_number"],
                Passenger.organization_id == current_user.organization_id,
                Passenger.id != passenger_id,
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Passport number already exists")

    for field, value in update_data.items():
        if value is not None:
            setattr(p, field, value)

    p.updated_at = datetime.now(timezone.utc)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return PassengerResponse.model_validate(p)


@router.delete("/{passenger_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_passenger(
    passenger_id: str,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """Delete a passenger profile."""
    p = await db.get(Passenger, passenger_id)
    if not p or p.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Passenger not found")
    await db.delete(p)
    await db.commit()


@router.get("/search/quick")
async def quick_search(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Quick search for auto-complete dropdowns (mission builder)."""
    like = f"%{q}%"
    result = await db.execute(
        select(Passenger).where(
            Passenger.organization_id == current_user.organization_id,
            or_(
                Passenger.full_name.ilike(like),
                Passenger.passport_number.ilike(like),
            ),
        ).order_by(Passenger.full_name.asc()).limit(10)
    )
    return [
        {
            "id": p.id,
            "full_name": p.full_name,
            "nationality": p.nationality,
            "passport_number": p.passport_number[:4] + "****" if p.passport_number else None,
            "weight_kg": p.weight_kg,
        }
        for p in result.scalars().all()
    ]
