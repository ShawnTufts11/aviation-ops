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
from app.models.aircraft import Aircraft
from app.models.crew import CrewMember
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.maintenance import MaintenanceTask
from app.models.user import User
from app.schemas.document import DocumentCreate, DocumentResponse, DocumentUpdate
from app.services.ad_compliance import check_aircraft_compliance, ad_status_to_dict

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
    current_user: User = Depends(require_role([Role.ACCOUNTABLE_EXECUTIVE, Role.DIRECTOR_OF_OPERATIONS])),
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
    current_user: User = Depends(require_role([Role.ACCOUNTABLE_EXECUTIVE, Role.DIRECTOR_OF_OPERATIONS])),
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
    current_user: User = Depends(require_role([Role.ACCOUNTABLE_EXECUTIVE])),
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


# ── Expiry Center — unified cross-source aggregation ────────────────
# Phase 1 (2026-08-25): read-only merge of aircraft / component / crew /
# qualification / document / AD-SB expiry data. No schema changes.
# See EXPIRY_CENTER_SCOPE.md.

_AIRCRAFT_EXPIRY_FIELDS = [
    ("registration_expiry", "Registration"),
    ("airworthiness_expiry", "Airworthiness"),
    ("coa_expiry", "COA"),
    ("insurance_expiry", "Insurance"),
]

_CREW_EXPIRY_FIELDS = [
    ("license_expiry", "License"),
    ("medical_expiry", "Medical"),
    ("passport_expiry", "Passport"),
]

_SOURCE_TIPS = {
    "aircraft": "Renew before the date — aircraft is not airworthy without it.",
    "component": "Schedule overhaul before the date.",
    "component_hours": "TBO hours reached — schedule overhaul now.",
    "crew": "Renew before the date — not current for operations.",
    "qualification": "Complete recurrent training before the date.",
    "document": "Renew/replace before the date.",
}


def _tip(source: str) -> str:
    return _SOURCE_TIPS.get(source, "Check before the date.")


@router.get("/expiry-center")
async def expiry_center(
    window_days: int = Query(30, ge=7, le=365),
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Unified expiry view: aircraft, components, crew, quals, documents, AD/SB.

    Returns `expiring` (within window_days) and `expired` lists sorted by
    days_left ascending, per-source counts, and a per-aircraft AD/SB summary
    (hours-based, kept separate from date-based items).
    """
    org_id = current_user.organization_id
    today = date.today()

    items: list[dict[str, Any]] = []

    # ── Aircraft date-based expiries ──────────────────────────────────
    ac_result = await db.execute(
        select(Aircraft).where(Aircraft.organization_id == org_id)
    )
    aircraft_list = list(ac_result.scalars().all())

    for ac in aircraft_list:
        for field, label in _AIRCRAFT_EXPIRY_FIELDS:
            exp = getattr(ac, field)
            if exp:
                items.append({
                    "source": "aircraft",
                    "entity": ac.tail_number,
                    "entity_id": ac.id,
                    "item": label,
                    "expiry_date": exp,
                    "reminder_days": 30,
                    "tip": _tip("aircraft"),
                })

        # ── Component TBO limits ──────────────────────────────────────
        for comp in ac.components:
            if comp.tbo_calendar_days and comp.installed_date:
                due = comp.installed_date + timedelta(days=comp.tbo_calendar_days)
                items.append({
                    "source": "component",
                    "entity": ac.tail_number,
                    "entity_id": comp.id,
                    "item": f"{comp.name} calendar TBO ({comp.tbo_calendar_days}d)",
                    "expiry_date": due,
                    "reminder_days": 30,
                    "tip": _tip("component"),
                })
            if comp.tbo_hours is not None and comp.hours_since_overhaul is not None:
                hours_remain = float(comp.tbo_hours) - float(comp.hours_since_overhaul)
                if hours_remain <= 0:
                    items.append({
                        "source": "component_hours",
                        "entity": ac.tail_number,
                        "entity_id": comp.id,
                        "item": f"{comp.name} TBO ({float(comp.tbo_hours):.0f} hr)",
                        "expiry_date": None,  # hours-based, not a date
                        "hours_overdue": round(-hours_remain, 1),
                        "days_left": None,
                        "reminder_days": 0,
                        "tip": _tip("component_hours"),
                    })

    # ── Crew date-based expiries ─────────────────────────────────────
    crew_result = await db.execute(
        select(CrewMember).where(CrewMember.organization_id == org_id)
    )
    for c in crew_result.scalars().all():
        for field, label in _CREW_EXPIRY_FIELDS:
            exp = getattr(c, field)
            if exp:
                items.append({
                    "source": "crew",
                    "entity": c.display_name,
                    "entity_id": c.id,
                    "item": label,
                    "expiry_date": exp,
                    "reminder_days": 45 if label == "Medical" else 60 if label == "Passport" else 30,
                    "tip": _tip("crew"),
                })
        for q in c.qualifications:
            if q.expiry_date:
                items.append({
                    "source": "qualification",
                    "entity": c.display_name,
                    "entity_id": q.id,
                    "item": f"{q.qual_type.value} {q.aircraft_type or ''}".strip(),
                    "expiry_date": q.expiry_date,
                    "reminder_days": 30,
                    "tip": _tip("qualification"),
                })

    # ── Documents ─────────────────────────────────────────────────────
    doc_result = await db.execute(
        select(Document).where(
            Document.organization_id == org_id,
            Document.expiry_date.is_not(None),
        )
    )
    for d in doc_result.scalars().all():
        items.append({
            "source": "document",
            "entity": d.title,
            "entity_id": d.id,
            "item": d.doc_type.value,
            "expiry_date": d.expiry_date,
            "reminder_days": d.reminder_days or 30,
            "tip": _tip("document"),
        })

    # ── Partition into expiring / expired (date-based only) ───────────
    expiring: list[dict[str, Any]] = []
    expired: list[dict[str, Any]] = []
    hours_overdue: list[dict[str, Any]] = []
    for it in items:
        if it.get("expiry_date") is None:
            if it.get("hours_overdue"):
                hours_overdue.append(it)
            continue
        days_left = (it["expiry_date"] - today).days
        it["days_left"] = days_left
        if days_left < 0:
            expired.append(it)
        elif days_left <= window_days:
            expiring.append(it)

    expiring.sort(key=lambda x: x["days_left"])
    expired.sort(key=lambda x: x["days_left"])
    hours_overdue.sort(key=lambda x: x["hours_overdue"], reverse=True)

    # ── AD/SB summary per aircraft (hours-based, separate section) ────
    ad_summary: list[dict[str, Any]] = []
    for ac in aircraft_list:
        tasks_result = await db.execute(
            select(MaintenanceTask).where(
                MaintenanceTask.aircraft_id == ac.id,
                MaintenanceTask.task_type.in_(["ad", "sb"]),
                MaintenanceTask.organization_id == org_id,
            )
        )
        compliance_records = []
        for task in tasks_result.scalars().all():
            compliance_records.append({
                "reference": task.reference or "",
                "status": task.status.value if hasattr(task.status, "value") else task.status,
                "completed_date": task.completed_date,
                "completed_hours": task.completed_hours,
                "completed_cycles": task.completed_cycles,
            })
        ad_status = await check_aircraft_compliance(ac, compliance_records)
        ad_summary.append(ad_status_to_dict(ad_status))

    by_source: dict[str, int] = {}
    for it in expiring + expired + hours_overdue:
        by_source[it["source"]] = by_source.get(it["source"], 0) + 1

    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "window_days": window_days,
        "summary": {
            "expiring": len(expiring),
            "expired": len(expired),
            "hours_overdue": len(hours_overdue),
            "by_source": by_source,
        },
        "expiring": expiring,
        "expired": expired,
        "hours_overdue": hours_overdue,
        "ad_summary": ad_summary,
    }
