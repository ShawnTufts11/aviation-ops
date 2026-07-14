"""Maintenance tracking endpoints — Module 3."""

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
from app.models.maintenance import MaintenanceTask
from app.models.user import User
from app.schemas.maintenance import (
    MaintenanceCreate,
    MaintenanceResponse,
    MaintenanceUpdate,
)

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


async def _get_aircraft_in_org(
    aircraft_id: str, org_id: str, db: AsyncSession
) -> Aircraft:
    """Verify aircraft belongs to org and return it."""
    ac = await db.get(Aircraft, aircraft_id)
    if not ac or ac.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Aircraft not found")
    return ac


# ── List maintenance ─────────────────────────────────────────────


@router.get("")
async def list_maintenance(
    aircraft_id: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    task_type: str | None = Query(None, alias="type"),
    overdue: bool | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List maintenance tasks with filtering."""
    org_id = current_user.organization_id
    conditions = [MaintenanceTask.organization_id == org_id]

    if aircraft_id:
        # Verify aircraft belongs to org
        await _get_aircraft_in_org(aircraft_id, org_id, db)
        conditions.append(MaintenanceTask.aircraft_id == aircraft_id)

    if status_filter:
        conditions.append(MaintenanceTask.status == status_filter)

    if task_type:
        conditions.append(MaintenanceTask.task_type == task_type)

    if overdue is not None:
        today = date.today()
        if overdue:
            conditions.append(
                MaintenanceTask.status.in_(["scheduled", "overdue"])
                & (MaintenanceTask.scheduled_date < today)
            )
        else:
            conditions.append(
                MaintenanceTask.status.in_(["scheduled", "overdue"])
                & (MaintenanceTask.scheduled_date >= today)
            )

    query = select(MaintenanceTask).where(and_(*conditions))

    # Count
    count_q = select(sa_func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Count overdue and due-soon separately
    today = date.today()
    thirty_days = today + timedelta(days=30)

    overdue_count_q = select(sa_func.count()).where(
        MaintenanceTask.organization_id == org_id,
        MaintenanceTask.status.in_(["scheduled", "overdue"]),
        MaintenanceTask.scheduled_date < today,
    )
    overdue_count = (await db.execute(overdue_count_q)).scalar() or 0

    due_soon_q = select(sa_func.count()).where(
        MaintenanceTask.organization_id == org_id,
        MaintenanceTask.status.in_(["scheduled", "overdue"]),
        MaintenanceTask.scheduled_date >= today,
        MaintenanceTask.scheduled_date <= thirty_days,
    )
    due_soon_count = (await db.execute(due_soon_q)).scalar() or 0

    # Paginate
    query = query.order_by(
        MaintenanceTask.scheduled_date.asc().nullsfirst(),
        MaintenanceTask.updated_at.desc(),
    )
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    tasks = result.scalars().all()

    return {
        "data": [MaintenanceResponse.model_validate(t) for t in tasks],
        "total": total,
        "page": page,
        "per_page": per_page,
        "overdue_count": overdue_count,
        "due_soon_count": due_soon_count,
    }


# ── Create maintenance task ──────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_maintenance(
    body: MaintenanceCreate,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.OPS_MANAGER, Role.ADMIN, Role.MECHANIC])),
    db: AsyncSession = Depends(get_db),
) -> MaintenanceResponse:
    """Create a new maintenance task for an aircraft.
    """
    await _get_aircraft_in_org(body.aircraft_id, current_user.organization_id, db)

    task = MaintenanceTask(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        aircraft_id=body.aircraft_id,
        title=body.title,
        description=body.description,
        task_type=body.task_type,
        reference=body.reference,
        interval_hours=body.interval_hours,
        interval_days=body.interval_days,
        scheduled_date=body.scheduled_date,
        status="scheduled",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    await log_action(
        db=db, org_id=current_user.organization_id, user_id=current_user.id,
        action="maintenance.created", entity_type="maintenance", entity_id=task.id,
        new_values={"title": task.title, "aircraft_id": task.aircraft_id},
    )

    return MaintenanceResponse.model_validate(task)


# ── Get task detail ──────────────────────────────────────────────


@router.get("/{task_id}")
async def get_maintenance(
    task_id: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> MaintenanceResponse:
    """Get a single maintenance task."""
    task = await db.get(MaintenanceTask, task_id)
    if not task or task.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Maintenance task not found")
    return MaintenanceResponse.model_validate(task)


# ── Update task (complete, defer, etc.) ──────────────────────────


@router.patch("/{task_id}")
async def update_maintenance(
    task_id: str,
    body: MaintenanceUpdate,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN, Role.OPS_MANAGER, Role.MECHANIC])),
    db: AsyncSession = Depends(get_db),
) -> MaintenanceResponse:
    """Update a maintenance task (status, completion, notes)."""
    task = await db.get(MaintenanceTask, task_id)
    if not task or task.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Maintenance task not found")

    old_values = {"status": task.status, "title": task.title}
    update_data = body.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if value is not None:
            setattr(task, field, value)

    # Auto-set completed_date when status changes to completed
    if update_data.get("status") == "completed" and not task.completed_date:
        task.completed_date = datetime.now(timezone.utc)

    task.updated_at = datetime.now(timezone.utc)
    db.add(task)
    await db.commit()
    await db.refresh(task)

    await log_action(
        db=db, org_id=current_user.organization_id, user_id=current_user.id,
        action="maintenance.updated", entity_type="maintenance", entity_id=task.id,
        old_values=old_values, new_values=update_data,
    )

    return MaintenanceResponse.model_validate(task)


# ── Delete task ──────────────────────────────────────────────────


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_maintenance(
    task_id: str,
    current_user: User = Depends(require_role([Role.SUPER_ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """Delete a maintenance task (super_admin only)."""
    task = await db.get(MaintenanceTask, task_id)
    if not task or task.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Maintenance task not found")

    await db.delete(task)
    await db.commit()


# ── Forecast (due in next N days) ────────────────────────────────


@router.get("/forecast/days")
async def maintenance_forecast(
    days: int = Query(30, ge=1, le=365),
    aircraft_id: str | None = Query(None),
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get maintenance forecast for the next N days."""
    org_id = current_user.organization_id
    today = date.today()
    end_date = today + timedelta(days=days)

    conditions = [
        MaintenanceTask.organization_id == org_id,
        MaintenanceTask.status.in_(["scheduled", "overdue"]),
        MaintenanceTask.scheduled_date <= end_date,
    ]
    if aircraft_id:
        await _get_aircraft_in_org(aircraft_id, org_id, db)
        conditions.append(MaintenanceTask.aircraft_id == aircraft_id)

    query = (
        select(MaintenanceTask)
        .where(and_(*conditions))
        .order_by(MaintenanceTask.scheduled_date.asc())
    )
    result = await db.execute(query)
    tasks = result.scalars().all()

    overdue = [t for t in tasks if t.scheduled_date and t.scheduled_date < today]
    upcoming = [t for t in tasks if t.scheduled_date and t.scheduled_date >= today]

    return {
        "forecast_period_days": days,
        "overdue": [MaintenanceResponse.model_validate(t) for t in overdue],
        "upcoming": [MaintenanceResponse.model_validate(t) for t in upcoming],
        "total": len(tasks),
        "overdue_count": len(overdue),
        "upcoming_count": len(upcoming),
    }
