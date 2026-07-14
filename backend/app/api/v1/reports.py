"""Reports: P&L, mx compliance, crew currency, monthly ops summary."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func as sa_func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_org_membership
from app.models.aircraft import Aircraft
from app.models.crew import CrewMember
from app.models.finance import FinancialRecord, RecordType
from app.models.flight import Flight, FlightStatus
from app.models.maintenance import MaintenanceTask, MaintenanceTaskStatus
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/monthly")
async def monthly_summary(
    year: int = Query(default=None),
    month: int = Query(default=None),
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Monthly operations summary: flights, hours, pax, cargo, revenue."""
    today = date.today()
    y = year or today.year
    m = month or today.month
    start = date(y, m, 1)
    if m == 12:
        end = date(y + 1, 1, 1)
    else:
        end = date(y, m + 1, 1)

    oid = current_user.organization_id

    # Flights this month
    flights_result = await db.execute(
        select(sa_func.count(Flight.id), sa_func.coalesce(sa_func.sum(Flight.flight_time_hours), 0),
               sa_func.coalesce(sa_func.sum(Flight.passengers_count), 0)).where(
            Flight.organization_id == oid,
            Flight.status == FlightStatus.COMPLETED,
            Flight.actual_departure >= start,
            Flight.actual_departure < end,
        )
    )
    frow = flights_result.one()
    flight_count = frow[0]
    total_hours = float(frow[1] or 0)
    total_pax = int(frow[2] or 0)

    # Revenue
    rev_result = await db.execute(
        select(sa_func.coalesce(sa_func.sum(FinancialRecord.amount), 0)).where(
            FinancialRecord.organization_id == oid,
            FinancialRecord.record_type == RecordType.REVENUE,
            FinancialRecord.entry_date >= start,
            FinancialRecord.entry_date < end,
        )
    )
    revenue = float(rev_result.scalar() or 0)

    # Costs
    cost_result = await db.execute(
        select(sa_func.coalesce(sa_func.sum(FinancialRecord.amount), 0)).where(
            FinancialRecord.organization_id == oid,
            FinancialRecord.record_type == RecordType.COST,
            FinancialRecord.entry_date >= start,
            FinancialRecord.entry_date < end,
        )
    )
    costs = float(cost_result.scalar() or 0)

    # Fleet utilization
    ac_result = await db.execute(
        select(Aircraft.id, Aircraft.tail_number).where(
            Aircraft.organization_id == oid,
            Aircraft.status == "active",
        )
    )
    aircraft_utilization = []
    for ac_id, tail in ac_result.all():
        hrs = await db.execute(
            select(sa_func.coalesce(sa_func.sum(Flight.flight_time_hours), 0)).where(
                Flight.organization_id == oid,
                Flight.aircraft_id == ac_id,
                Flight.status == FlightStatus.COMPLETED,
                Flight.actual_departure >= start,
                Flight.actual_departure < end,
            )
        )
        aircraft_utilization.append({"tail": tail, "hours": float(hrs.scalar() or 0)})

    return {
        "period": f"{y}-{m:02d}",
        "flights": flight_count,
        "total_flight_hours": round(total_hours, 1),
        "total_passengers": total_pax,
        "revenue": round(revenue, 2),
        "costs": round(costs, 2),
        "profit": round(revenue - costs, 2),
        "fleet_utilization": aircraft_utilization,
        "generated": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/pnl")
async def profit_and_loss(
    aircraft_id: str | None = Query(None),
    from_date: str = Query(default=None, alias="from"),
    to_date: str = Query(default=None, alias="to"),
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """P&L breakdown by aircraft and category."""
    oid = current_user.organization_id
    conditions = [FinancialRecord.organization_id == oid]

    if aircraft_id:
        conditions.append(FinancialRecord.aircraft_id == aircraft_id)
    if from_date:
        conditions.append(FinancialRecord.entry_date >= date.fromisoformat(from_date))
    if to_date:
        conditions.append(FinancialRecord.entry_date <= date.fromisoformat(to_date))

    # Group revenue by category
    rev_result = await db.execute(
        select(FinancialRecord.category, sa_func.coalesce(sa_func.sum(FinancialRecord.amount), 0)).where(
            *conditions, FinancialRecord.record_type == RecordType.REVENUE,
        ).group_by(FinancialRecord.category)
    )
    revenue_by_category = {row[0].value if hasattr(row[0], 'value') else row[0]: float(row[1]) for row in rev_result.all()}

    # Group costs by category
    cost_result = await db.execute(
        select(FinancialRecord.category, sa_func.coalesce(sa_func.sum(FinancialRecord.amount), 0)).where(
            *conditions, FinancialRecord.record_type == RecordType.COST,
        ).group_by(FinancialRecord.category)
    )
    costs_by_category = {row[0].value if hasattr(row[0], 'value') else row[0]: float(row[1]) for row in cost_result.all()}

    total_rev = sum(revenue_by_category.values())
    total_cost = sum(costs_by_category.values())

    return {
        "total_revenue": round(total_rev, 2),
        "total_costs": round(total_cost, 2),
        "net_profit": round(total_rev - total_cost, 2),
        "revenue_by_category": revenue_by_category,
        "costs_by_category": costs_by_category,
        "profit_margin_percent": round(((total_rev - total_cost) / total_rev * 100), 1) if total_rev else 0,
    }


@router.get("/mx-compliance")
async def maintenance_compliance(
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Maintenance completion rates by aircraft."""
    oid = current_user.organization_id

    ac_result = await db.execute(
        select(Aircraft.id, Aircraft.tail_number).where(
            Aircraft.organization_id == oid, Aircraft.status == "active",
        )
    )
    results = []
    for ac_id, tail in ac_result.all():
        total = await db.execute(
            select(sa_func.count(MaintenanceTask.id)).where(
                MaintenanceTask.organization_id == oid,
                MaintenanceTask.aircraft_id == ac_id,
            )
        )
        total_count = total.scalar() or 0

        completed = await db.execute(
            select(sa_func.count(MaintenanceTask.id)).where(
                MaintenanceTask.organization_id == oid,
                MaintenanceTask.aircraft_id == ac_id,
                MaintenanceTask.status == MaintenanceTaskStatus.COMPLETED,
            )
        )
        completed_count = completed.scalar() or 0

        overdue = await db.execute(
            select(sa_func.count(MaintenanceTask.id)).where(
                MaintenanceTask.organization_id == oid,
                MaintenanceTask.aircraft_id == ac_id,
                MaintenanceTask.status == MaintenanceTaskStatus.OVERDUE,
            )
        )
        overdue_count = overdue.scalar() or 0

        results.append({
            "tail": tail,
            "total_tasks": total_count,
            "completed": completed_count,
            "overdue": overdue_count,
            "compliance_rate": round((completed_count / total_count * 100), 1) if total_count else 100,
        })

    return {"aircraft": results}


@router.get("/crew-currency")
async def crew_currency(
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Crew currency matrix — who's current and what's expiring."""
    oid = current_user.organization_id

    result = await db.execute(
        select(CrewMember).where(
            CrewMember.organization_id == oid,
            CrewMember.status == "active",
        ).order_by(CrewMember.last_name)
    )
    crew_list = []
    today = date.today()
    for c in result.scalars().all():
        med_status = "current"
        if c.medical_expiry:
            if c.medical_expiry < today:
                med_status = "expired"
            elif c.medical_expiry < today + timedelta(days=30):
                med_status = "expiring_soon"

        lic_status = "current"
        if c.license_expiry:
            if c.license_expiry < today:
                lic_status = "expired"
            elif c.license_expiry < today + timedelta(days=60):
                lic_status = "expiring_soon"

        crew_list.append({
            "id": c.id,
            "name": f"{c.first_name} {c.last_name}",
            "role": c.role,
            "license_expiry": c.license_expiry.isoformat() if c.license_expiry else None,
            "license_status": lic_status,
            "medical_expiry": c.medical_expiry.isoformat() if c.medical_expiry else None,
            "medical_status": med_status,
            "last_90d_hours": c.last_90d_hours or 0,
        })

    return {
        "crew": crew_list,
        "total_active": len(crew_list),
        "expiring_medical": len([c for c in crew_list if c["medical_status"] == "expiring_soon"]),
        "expired_medical": len([c for c in crew_list if c["medical_status"] == "expired"]),
        "expiring_license": len([c for c in crew_list if c["license_status"] == "expiring_soon"]),
    }
