"""Comms & Emergency Alerting endpoints — Module 9."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.audit import log_action
from app.core.permissions import require_org_membership, require_role
from app.core.roles import Role
from app.models.notification import (
    Notification,
    EmergencyAlert,
    AlertSeverity,
    AlertStatus,
)
from app.models.user import User

router = APIRouter(prefix="/comms", tags=["comms"])


# ── Notifications ───────────────────────────────────────────────


@router.get("/notifications")
async def list_notifications(
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List notifications for the current user."""
    conditions = [Notification.organization_id == current_user.organization_id]

    # Show user-specific + org-wide notifications
    conditions.append(
        (Notification.user_id == current_user.id) | (Notification.user_id.is_(None))
    )
    if unread_only:
        conditions.append(Notification.is_read == False)

    query = select(Notification).where(*conditions).order_by(
        Notification.created_at.desc()
    ).offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)

    # Count unread
    unread_q = select(sa_func.count()).where(
        Notification.organization_id == current_user.organization_id,
        Notification.is_read == False,
        (Notification.user_id == current_user.id) | (Notification.user_id.is_(None)),
    )
    unread_count = (await db.execute(unread_q)).scalar() or 0

    return {
        "data": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "severity": n.severity.value,
                "category": n.category,
                "is_read": n.is_read,
                "link": n.link,
                "created_at": n.created_at.isoformat(),
            }
            for n in result.scalars().all()
        ],
        "unread_count": unread_count,
        "page": page,
        "per_page": per_page,
    }


@router.post("/notifications/{notif_id}/read")
async def mark_read(
    notif_id: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Mark a notification as read."""
    notif = await db.get(Notification, notif_id)
    if not notif or notif.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.is_read = True
    db.add(notif)
    await db.commit()
    return {"status": "ok"}


@router.post("/notifications/read-all")
async def mark_all_read(
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Mark all notifications as read for the current user."""
    await db.execute(
        select(Notification).where(
            Notification.organization_id == current_user.organization_id,
            Notification.is_read == False,
            (Notification.user_id == current_user.id) | (Notification.user_id.is_(None)),
        )
    )
    # Bulk update
    from sqlalchemy import update
    stmt = (
        update(Notification)
        .where(
            Notification.organization_id == current_user.organization_id,
            Notification.is_read == False,
            (Notification.user_id == current_user.id) | (Notification.user_id.is_(None)),
        )
        .values(is_read=True)
    )
    await db.execute(stmt)
    await db.commit()
    return {"status": "ok"}


# ── Emergency Alerts ────────────────────────────────────────────


@router.post("/emergency")
async def trigger_emergency(
    title: str,
    description: str | None = None,
    aircraft_id: str | None = None,
    flight_id: str | None = None,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.OPS_MANAGER, Role.ADMIN, Role.PILOT])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Trigger an emergency alert. Creates dashboard banner + notifications."""
    alert = EmergencyAlert(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        triggered_by=current_user.id,
        title=title,
        description=description,
        severity=AlertSeverity.EMERGENCY,
        status=AlertStatus.ACTIVE,
        aircraft_id=aircraft_id,
        flight_id=flight_id,
    )
    db.add(alert)

    # Create notifications for all active org users
    from app.models.user import User as UserModel
    users = await db.execute(
        select(UserModel).where(
            UserModel.organization_id == current_user.organization_id,
            UserModel.is_active == True,
        )
    )
    for u in users.scalars().all():
        notif = Notification(
            id=str(uuid.uuid4()),
            organization_id=current_user.organization_id,
            user_id=u.id,
            title=f"🚨 EMERGENCY: {title}",
            message=description,
            severity=AlertSeverity.EMERGENCY,
            category="emergency",
            link="/",
        )
        db.add(notif)

    await db.commit()

    await log_action(
        db=db, org_id=current_user.organization_id, user_id=current_user.id,
        action="emergency.triggered", entity_type="emergency_alert", entity_id=alert.id,
        new_values={"title": title or "", "severity": "emergency"},
    )

    return {
        "id": alert.id,
        "title": title,
        "severity": "emergency",
        "status": "active",
        "notifications_created": True,
    }


@router.get("/emergency/active")
async def active_emergencies(
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Get all active/unacknowledged emergency alerts."""
    result = await db.execute(
        select(EmergencyAlert).where(
            EmergencyAlert.organization_id == current_user.organization_id,
            EmergencyAlert.status.in_([AlertStatus.ACTIVE, AlertStatus.ESCALATED]),
        ).order_by(EmergencyAlert.created_at.desc())
    )
    return [
        {
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "severity": a.severity.value,
            "status": a.status.value,
            "aircraft_id": a.aircraft_id,
            "created_at": a.created_at.isoformat(),
        }
        for a in result.scalars().all()
    ]


@router.post("/emergency/{alert_id}/acknowledge")
async def acknowledge_emergency(
    alert_id: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Acknowledge an emergency alert (clears dashboard banner)."""
    alert = await db.get(EmergencyAlert, alert_id)
    if not alert or alert.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.add(alert)
    await db.commit()
    return {"status": "acknowledged"}


@router.post("/emergency/{alert_id}/resolve")
async def resolve_emergency(
    alert_id: str,
    notes: str = "",
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.OPS_MANAGER])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Resolve an emergency alert."""
    alert = await db.get(EmergencyAlert, alert_id)
    if not alert or alert.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = AlertStatus.RESOLVED
    alert.resolved_by = current_user.id
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolution_notes = notes or None
    db.add(alert)
    await db.commit()
    return {"status": "resolved"}
