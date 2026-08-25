"""Crew management endpoints — Module 5."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc, asc, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.audit import log_action
from app.core.permissions import require_org_membership, require_role, require_pii_clearance
from app.core.roles import Role
from app.models.crew import CrewMember, CrewQualification
from app.models.user import User
from app.schemas.crew import (
    CrewCreate,
    CrewResponse,
    CrewUpdate,
    QualificationCreate,
    QualificationResponse,
)

router = APIRouter(prefix="/crew", tags=["crew"])


# ── List crew ───────────────────────────────────────────────────


@router.get("")
async def list_crew(
    role_filter: str | None = Query(None, alias="role"),
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None, alias="q"),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List crew members with filtering."""
    conditions = [CrewMember.organization_id == current_user.organization_id]

    if role_filter:
        conditions.append(CrewMember.role == role_filter)
    if status_filter:
        conditions.append(CrewMember.status == status_filter)
    if search:
        like = f"%{search}%"
        conditions.append(
            CrewMember.first_name.ilike(like)
            | CrewMember.last_name.ilike(like)
            | CrewMember.email.ilike(like)
        )

    query = select(CrewMember).where(*conditions)

    count_q = select(sa_func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(CrewMember.last_name.asc(), CrewMember.first_name.asc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    crew = result.scalars().all()

    return {
        "data": [CrewResponse.model_validate(c) for c in crew],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ── Create crew ─────────────────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_crew(
    body: CrewCreate,
    current_user: User = Depends(require_role([Role.ACCOUNTABLE_EXECUTIVE, Role.DIRECTOR_OF_OPERATIONS])),
    db: AsyncSession = Depends(get_db),
) -> CrewResponse:
    """Add a new crew member."""
    member = CrewMember(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        phone=body.phone,
        role=body.role,
        license_type=body.license_type,
        license_number=body.license_number,
        license_country=body.license_country,
        license_expiry=body.license_expiry,
        medical_class=body.medical_class,
        medical_expiry=body.medical_expiry,
        passport_number=body.passport_number,
        passport_expiry=body.passport_expiry,
        base_airport=body.base_airport,
        date_of_hire=body.date_of_hire,
        notes=body.notes,
        status="active",
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)

    await log_action(
        db=db, org_id=current_user.organization_id, user_id=current_user.id,
        action="crew.created", entity_type="crew", entity_id=member.id,
        new_values={"name": member.display_name, "role": member.role.value},
    )

    return CrewResponse.model_validate(member)


# ── Get crew detail ─────────────────────────────────────────────


@router.get("/{crew_id}")
async def get_crew(
    crew_id: str,
    current_user: User = Depends(require_pii_clearance()),
    db: AsyncSession = Depends(get_db),
) -> CrewResponse:
    """Get crew member with qualifications."""
    member = await db.get(CrewMember, crew_id)
    if not member or member.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Crew member not found")
    return CrewResponse.model_validate(member)


# ── Update crew ─────────────────────────────────────────────────


@router.patch("/{crew_id}")
async def update_crew(
    crew_id: str,
    body: CrewUpdate,
    current_user: User = Depends(require_role([Role.ACCOUNTABLE_EXECUTIVE, Role.DIRECTOR_OF_OPERATIONS])),
    db: AsyncSession = Depends(get_db),
) -> CrewResponse:
    """Update crew member details."""
    member = await db.get(CrewMember, crew_id)
    if not member or member.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Crew member not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(member, field, value)

    member.updated_at = datetime.now(timezone.utc)
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return CrewResponse.model_validate(member)


# ── Qualifications ──────────────────────────────────────────────


@router.get("/{crew_id}/qualifications")
async def list_qualifications(
    crew_id: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> list[QualificationResponse]:
    """List qualifications for a crew member."""
    member = await db.get(CrewMember, crew_id)
    if not member or member.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Crew member not found")
    return [QualificationResponse.model_validate(q) for q in member.qualifications]


@router.post("/{crew_id}/qualifications", status_code=status.HTTP_201_CREATED)
async def add_qualification(
    crew_id: str,
    body: QualificationCreate,
    current_user: User = Depends(require_role([Role.ACCOUNTABLE_EXECUTIVE, Role.DIRECTOR_OF_OPERATIONS])),
    db: AsyncSession = Depends(get_db),
) -> QualificationResponse:
    """Add a qualification for a crew member."""
    member = await db.get(CrewMember, crew_id)
    if not member or member.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Crew member not found")

    qual = CrewQualification(
        id=str(uuid.uuid4()),
        crew_id=crew_id,
        qual_type=body.qual_type,
        aircraft_type=body.aircraft_type,
        issued_date=body.issued_date,
        expiry_date=body.expiry_date,
        notes=body.notes,
    )
    db.add(qual)
    await db.commit()
    await db.refresh(qual)
    return QualificationResponse.model_validate(qual)


# ── Dashboard summary ───────────────────────────────────────────


@router.get("/summary/counts")
async def crew_summary(
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Crew counts by role and status."""
    org_id = current_user.organization_id
    result = await db.execute(
        select(CrewMember.role, sa_func.count(CrewMember.id))
        .where(CrewMember.organization_id == org_id, CrewMember.status == "active")
        .group_by(CrewMember.role)
    )
    by_role = {row[0]: row[1] for row in result.all()}

    result2 = await db.execute(
        select(CrewMember.status, sa_func.count(CrewMember.id))
        .where(CrewMember.organization_id == org_id)
        .group_by(CrewMember.status)
    )
    by_status = {row[0]: row[1] for row in result2.all()}

    # Expiring items
    from sqlalchemy import func as f
    from datetime import date, timedelta
    thirty_days = date.today() + timedelta(days=30)

    expiring_medical = await db.execute(
        select(sa_func.count()).where(
            CrewMember.organization_id == org_id,
            CrewMember.medical_expiry <= thirty_days,
        )
    )
    expiring_license = await db.execute(
        select(sa_func.count()).where(
            CrewMember.organization_id == org_id,
            CrewMember.license_expiry <= thirty_days,
        )
    )

    return {
        "total_active": sum(by_role.values()),
        "by_role": by_role,
        "by_status": by_status,
        "expiring_medical": expiring_medical.scalar() or 0,
        "expiring_license": expiring_license.scalar() or 0,
    }
