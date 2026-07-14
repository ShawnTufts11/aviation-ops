"""
Audit trail service — logs every state-changing action for compliance.

Part 135 operators must maintain records of changes to aircraft, crew,
flights, and maintenance. This module provides a simple structured log
backed by the AuditLog model.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def log_action(
    db: AsyncSession,
    org_id: str,
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    old_values: Optional[dict[str, Any]] = None,
    new_values: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Record an auditable action.

    Args:
        db: Active DB session.
        org_id: Organization the action belongs to.
        user_id: ID of the user who performed the action.
        action: Verb describing the action (e.g. ``created``, ``updated``, ``deleted``).
        entity_type: Type of entity affected (e.g. ``aircraft``, ``flight``).
        entity_id: ID of the affected entity.
        old_values: Snapshot of values before the change.
        new_values: Snapshot of values after the change.
        ip_address: Originating IP, if available.

    Returns:
        The persisted AuditLog row.
    """
    entry = AuditLog(
        organization_id=org_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=old_values or {},
        new_values=new_values or {},
        ip_address=ip_address,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(entry)
    await db.flush()
    return entry


async def get_audit_logs(
    db: AsyncSession,
    org_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[AuditLog]:
    """Fetch recent audit log entries for an organization, newest first."""
    stmt = (
        select(AuditLog)
        .where(AuditLog.organization_id == org_id)
        .order_by(AuditLog.timestamp.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
