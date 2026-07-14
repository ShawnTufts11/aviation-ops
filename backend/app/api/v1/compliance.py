"""Compliance & document management endpoints — Module 6."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc, func as sa_func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.audit import log_action
from app.core.permissions import require_org_membership, require_role
from app.core.roles import Role
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.user import User
from app.schemas.document import DocumentCreate, DocumentResponse, DocumentUpdate

router = APIRouter(prefix="/compliance", tags=["compliance"])


# ── List documents ──────────────────────────────────────────────


@router.get("/documents")
async def list_documents(
    doc_type: str | None = Query(None, alias="type"),
    status_filter: str | None = Query(None, alias="status"),
    aircraft_id: str | None = Query(None),
    crew_id: str | None = Query(None),
    country: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List compliance documents with filtering."""
    conditions = [Document.organization_id == current_user.organization_id]

    if doc_type:
        conditions.append(Document.doc_type == doc_type)
    if status_filter:
        conditions.append(Document.status == status_filter)
    if aircraft_id:
        conditions.append(Document.aircraft_id == aircraft_id)
    if crew_id:
        conditions.append(Document.crew_id == crew_id)
    if country:
        conditions.append(Document.countries.ilike(f"%{country}%"))

    query = select(Document).where(and_(*conditions))

    count_q = select(sa_func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(Document.expiry_date.asc().nullslast())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    docs = result.scalars().all()

    return {
        "data": [DocumentResponse.model_validate(d) for d in docs],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ── Create document ─────────────────────────────────────────────


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def create_document(
    body: DocumentCreate,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.OPS_MANAGER])),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Upload a new compliance document."""
    doc = Document(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        aircraft_id=body.aircraft_id,
        crew_id=body.crew_id,
        title=body.title,
        doc_type=body.doc_type,
        doc_number=body.doc_number,
        issuing_authority=body.issuing_authority,
        issue_date=body.issue_date,
        expiry_date=body.expiry_date,
        reminder_days=body.reminder_days or 30,
        file_url=body.file_url,
        status=DocumentStatus.CURRENT,
        countries=body.countries,
        regulations=body.regulations,
        notes=body.notes,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    await log_action(
        db=db, org_id=current_user.organization_id, user_id=current_user.id,
        action="document.created", entity_type="document", entity_id=doc.id,
        new_values={"title": doc.title, "type": doc.doc_type.value},
    )

    return DocumentResponse.model_validate(doc)


# ── Get document ────────────────────────────────────────────────


@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Get a single document."""
    doc = await db.get(Document, doc_id)
    if not doc or doc.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(doc)


# ── Update document ─────────────────────────────────────────────


@router.patch("/documents/{doc_id}")
async def update_document(
    doc_id: str,
    body: DocumentUpdate,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.OPS_MANAGER])),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Update document fields."""
    doc = await db.get(Document, doc_id)
    if not doc or doc.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Document not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(doc, field, value)

    doc.updated_at = datetime.now(timezone.utc)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return DocumentResponse.model_validate(doc)


# ── Delete document ─────────────────────────────────────────────


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: str,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document."""
    doc = await db.get(Document, doc_id)
    if not doc or doc.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.delete(doc)
    await db.commit()


# ── Expiry dashboard ────────────────────────────────────────────


@router.get("/dashboard")
async def compliance_dashboard(
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Compliance overview: expiring docs, counts by type and status."""
    org_id = current_user.organization_id
    today = date.today()
    thirty_days = today + timedelta(days=30)

    # Counts by status
    status_query = await db.execute(
        select(Document.status, sa_func.count(Document.id))
        .where(Document.organization_id == org_id)
        .group_by(Document.status)
    )
    by_status = {row[0]: row[1] for row in status_query.all()}

    # Expiring soon (within 30 days)
    expiring = await db.execute(
        select(Document).where(
            Document.organization_id == org_id,
            Document.expiry_date >= today,
            Document.expiry_date <= thirty_days,
            Document.status != DocumentStatus.EXPIRED,
        ).order_by(Document.expiry_date.asc()).limit(10)
    )

    # Already expired
    expired = await db.execute(
        select(Document).where(
            Document.organization_id == org_id,
            Document.expiry_date < today,
        ).order_by(Document.expiry_date.asc()).limit(10)
    )

    # Counts by country
    country_result = await db.execute(
        select(Document.countries, sa_func.count(Document.id))
        .where(Document.organization_id == org_id)
        .group_by(Document.countries)
    )
    by_country = {}
    for row in country_result.all():
        if row[0]:
            for c in row[0].split(","):
                c = c.strip()
                by_country[c] = by_country.get(c, 0) + row[1]

    return {
        "total": sum(by_status.values()),
        "by_status": by_status,
        "expiring_soon": [DocumentResponse.model_validate(d) for d in expiring.scalars().all()],
        "expired": [DocumentResponse.model_validate(d) for d in expired.scalars().all()],
        "by_country": by_country,
        "current_count": by_status.get("current", 0),
        "expiring_count": by_status.get("expiring_soon", 0),
        "expired_count": by_status.get("expired", 0),
    }
