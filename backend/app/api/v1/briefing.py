"""Briefing Dashboard — FAA Part 135 consolidated operational picture.

POST /api/v1/briefing/dashboard — returns all briefing card data,
filtered by the requesting user's role.
"""

from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_org_membership
from app.core.roles import Role
from app.models.aircraft import Aircraft, AircraftStatus
from app.models.maintenance import MaintenanceTask
from app.models.mission import Mission, MissionStatus
from app.models.finance import FinancialRecord, RecordType
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.services.weather import get_metar, weather_to_dict

router = APIRouter(prefix="/briefing", tags=["briefing"])

# ── Card visibility by role (minimum privilege level) ───────────────────
# Each card is visible if the user's privilege >= the card's requirement.

CARD_VISIBILITY: dict[str, Role] = {
    "active_missions": Role.VIEWER,             # Everyone
    "fleet_health": Role.VIEWER,                # Everyone
    "upcoming_maintenance": Role.VIEWER,        # Everyone sees the count
    "current_missions": Role.PILOT,             # Pilots, dispatchers, and above
    "weather_notams": Role.PILOT,               # Pilots, dispatchers, mgmt
    "financials_overview": Role.VP_FINANCE,     # VP Finance+
    "compliance_snapshot": Role.DIRECTOR_OF_OPERATIONS,  # DoO+
}


def _card_visible(user_role: Role, min_role: Role) -> bool:
    """Check whether a user's role meets the visibility threshold."""
    return user_role.has_privilege(min_role)


def _visible_cards(user_role: Role) -> dict[str, bool]:
    """Return a map of card_id → visible for this user."""
    return {
        card_id: _card_visible(user_role, min_role)
        for card_id, min_role in CARD_VISIBILITY.items()
    }


# ── Dashboard endpoint ──────────────────────────────────────────────────


@router.post("/dashboard")
async def briefing_dashboard(
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return all briefing cards with data filtered by the user's role.

    Each card has:
      - id: str
      - title: str
      - data: dict (card-specific payload)
      - visible: bool

    Also returns a ``visibility`` map so the frontend knows which cards
    are available without checking each individually.
    """
    org_id = current_user.organization_id
    user_role = current_user.role
    visibility = _visible_cards(user_role)
    cards: list[dict[str, Any]] = []

    # ── 1. Active missions count ──────────────────────────────────────────
    if visibility["active_missions"]:
        count_q = select(sa_func.count(Mission.id)).where(
            Mission.organization_id == org_id,
            Mission.status == MissionStatus.ACTIVE,
        )
        active_count = (await db.execute(count_q)).scalar() or 0
        cards.append({
            "id": "active_missions",
            "title": "Active Missions",
            "data": {"active_count": active_count},
            "visible": True,
        })

    # ── 2. Fleet health summary ───────────────────────────────────────────
    if visibility["fleet_health"]:
        total = await db.execute(
            select(sa_func.count(Aircraft.id)).where(
                Aircraft.organization_id == org_id
            )
        )
        total_fleet = total.scalar() or 0

        active = await db.execute(
            select(sa_func.count(Aircraft.id)).where(
                Aircraft.organization_id == org_id,
                Aircraft.status == AircraftStatus.ACTIVE,
            )
        )
        in_mx = await db.execute(
            select(sa_func.count(Aircraft.id)).where(
                Aircraft.organization_id == org_id,
                Aircraft.status == AircraftStatus.IN_MAINTENANCE,
            )
        )
        grounded = await db.execute(
            select(sa_func.count(Aircraft.id)).where(
                Aircraft.organization_id == org_id,
                Aircraft.status == AircraftStatus.GROUNDED,
            )
        )

        cards.append({
            "id": "fleet_health",
            "title": "Fleet Health",
            "data": {
                "total_aircraft": total_fleet,
                "active": active.scalar() or 0,
                "in_maintenance": in_mx.scalar() or 0,
                "grounded": grounded.scalar() or 0,
            },
            "visible": True,
        })

    # ── 3. Upcoming maintenance / parts needed ─────────────────────────---
    if visibility["upcoming_maintenance"]:
        due_q = select(sa_func.count(MaintenanceTask.id)).where(
            MaintenanceTask.organization_id == org_id,
            MaintenanceTask.status.in_(["scheduled", "overdue"]),
        )
        due_count = (await db.execute(due_q)).scalar() or 0

        # Fetch a few upcoming tasks
        tasks_query = (
            select(MaintenanceTask)
            .where(
                MaintenanceTask.organization_id == org_id,
                MaintenanceTask.status.in_(["scheduled", "overdue"]),
            )
            .order_by(MaintenanceTask.scheduled_date.asc().nullslast())
            .limit(5)
        )
        tasks = (await db.execute(tasks_query)).scalars().all()

        cards.append({
            "id": "upcoming_maintenance",
            "title": "Upcoming Maintenance",
            "data": {
                "due_count": due_count,
                "tasks": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "task_type": t.task_type.value if t.task_type else None,
                        "status": t.status.value if t.status else None,
                        "scheduled_date": (
                            t.scheduled_date.isoformat()
                            if t.scheduled_date
                            else None
                        ),
                        "aircraft_id": t.aircraft_id,
                    }
                    for t in tasks
                ],
            },
            "visible": True,
        })

    # ── 4. Current & upcoming missions ────────────────────────────────────
    if visibility["current_missions"]:
        missions_query = (
            select(Mission)
            .where(
                Mission.organization_id == org_id,
                Mission.status.in_(
                    [MissionStatus.DRAFT, MissionStatus.ACTIVE]
                ),
            )
            .order_by(Mission.mission_date.asc().nullslast())
            .limit(5)
        )
        missions = (await db.execute(missions_query)).scalars().all()

        cards.append({
            "id": "current_missions",
            "title": "Current & Upcoming Missions",
            "data": {
                "missions": [
                    {
                        "id": m.id,
                        "status": m.status.value if m.status else None,
                        "aircraft_id": m.aircraft_id,
                        "pilot_in_command": m.pilot_in_command,
                        "mission_date": (
                            m.mission_date.isoformat()
                            if m.mission_date
                            else None
                        ),
                        "home_base": m.home_base,
                        "leg_count": len(m.legs) if m.legs else 0,
                    }
                    for m in missions
                ],
            },
            "visible": True,
        })

    # ── 5. Financials overview (VP_FINANCE+) ──────────────────────────────
    if visibility["financials_overview"]:
        today = date.today()
        month_start = today.replace(day=1)

        mtd_rev = await db.execute(
            select(sa_func.sum(FinancialRecord.amount)).where(
                FinancialRecord.organization_id == org_id,
                FinancialRecord.record_type == RecordType.REVENUE,
                FinancialRecord.entry_date >= month_start,
            )
        )
        mtd_cost = await db.execute(
            select(sa_func.sum(FinancialRecord.amount)).where(
                FinancialRecord.organization_id == org_id,
                FinancialRecord.record_type == RecordType.COST,
                FinancialRecord.entry_date >= month_start,
            )
        )

        mtd_revenue = float(mtd_rev.scalar() or 0)
        mtd_costs = float(mtd_cost.scalar() or 0)

        cards.append({
            "id": "financials_overview",
            "title": "Financials Overview",
            "data": {
                "mtd_revenue": mtd_revenue,
                "mtd_costs": mtd_costs,
                "mtd_net": round(mtd_revenue - mtd_costs, 2),
            },
            "visible": True,
        })

    # ── 6. Compliance snapshot (DIRECTOR_OF_OPERATIONS+) ──────────────────
    if visibility["compliance_snapshot"]:
        today = date.today()
        thirty_days = today + timedelta(days=30)

        total_docs_q = select(sa_func.count(Document.id)).where(
            Document.organization_id == org_id
        )
        total_docs = (await db.execute(total_docs_q)).scalar() or 0

        expiring_q = select(sa_func.count(Document.id)).where(
            Document.organization_id == org_id,
            Document.expiry_date >= today,
            Document.expiry_date <= thirty_days,
            Document.status != DocumentStatus.EXPIRED,
        )
        expiring = (await db.execute(expiring_q)).scalar() or 0

        expired_q = select(sa_func.count(Document.id)).where(
            Document.organization_id == org_id,
            Document.expiry_date < today,
        )
        expired = (await db.execute(expired_q)).scalar() or 0

        cards.append({
            "id": "compliance_snapshot",
            "title": "Compliance Snapshot",
            "data": {
                "total_documents": total_docs,
                "expiring_within_30_days": expiring,
                "expired": expired,
                "healthy": total_docs > 0 and expired == 0,
            },
            "visible": True,
        })

    # ── 7. Weather & NOTAMs (PILOT+) ─────────────────────────────────────
    if visibility["weather_notams"]:
        # Use the user's org base from first active aircraft, or fallback
        base_q = (
            select(Aircraft.base)
            .where(
                Aircraft.organization_id == org_id,
                Aircraft.status == AircraftStatus.ACTIVE,
            )
            .limit(1)
        )
        base_result = await db.execute(base_q)
        base_icao = base_result.scalar() or "MYNN"  # Fallback

        metar = await get_metar(base_icao)
        weather_data = weather_to_dict(metar) if not metar.error else {
            "icao": base_icao,
            "error": metar.error,
        }

        cards.append({
            "id": "weather_notams",
            "title": f"Weather — {base_icao}",
            "data": {
                "station": base_icao,
                "metar": weather_data,
                "taf": "TAF data requires FAA NMS OAuth — see weather service",
                "notams": "NOTAM retrieval requires FAA NMS API credentials — see settings",
            },
            "visible": True,
        })

    return {
        "cards": cards,
        "visibility": visibility,
    }
