"""Financial dashboard endpoints — Module 7."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_org_membership
from app.models.finance import FinancialRecord, RecordType, CostCategory
from app.models.user import User

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/pnl")
async def pnl_by_tail(
    tail_number: str | None = Query(None),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """P&L summary — revenue vs costs, optionally by tail number or date range."""
    org_id = current_user.organization_id
    conditions = [FinancialRecord.organization_id == org_id]

    if from_date:
        conditions.append(FinancialRecord.entry_date >= from_date)
    if to_date:
        conditions.append(FinancialRecord.entry_date <= to_date)

    # Revenue
    rev_q = select(sa_func.sum(FinancialRecord.amount)).where(
        *conditions, FinancialRecord.record_type == RecordType.REVENUE
    )
    total_revenue = (await db.execute(rev_q)).scalar() or 0

    # Costs
    cost_q = select(sa_func.sum(FinancialRecord.amount)).where(
        *conditions, FinancialRecord.record_type == RecordType.COST
    )
    total_costs = (await db.execute(cost_q)).scalar() or 0

    # By category
    cat_q = select(
        FinancialRecord.category,
        sa_func.sum(FinancialRecord.amount),
        sa_func.count(FinancialRecord.id),
    ).where(*conditions).group_by(FinancialRecord.category)
    cat_result = await db.execute(cat_q)

    return {
        "total_revenue": float(total_revenue),
        "total_costs": float(total_costs),
        "net": float(total_revenue) - float(total_costs),
        "by_category": [
            {"category": row[0], "amount": float(row[1]), "count": row[2]}
            for row in cat_result.all()
        ],
    }


@router.get("/records")
async def list_records(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List financial records."""
    conditions = [FinancialRecord.organization_id == current_user.organization_id]
    query = select(FinancialRecord).where(*conditions).order_by(
        FinancialRecord.created_at.desc()
    ).offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    rows = result.scalars().all()

    return {
        "data": [
            {
                "id": r.id,
                "record_type": r.record_type.value,
                "category": r.category.value,
                "amount": float(r.amount),
                "currency": r.currency,
                "description": r.description,
                "aircraft_id": r.aircraft_id,
                "flight_id": r.flight_id,
                "entry_date": r.entry_date.isoformat(),
            }
            for r in rows
        ],
        "total": len(rows),
        "page": page,
        "per_page": per_page,
    }


@router.get("/summary")
async def financial_summary(
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Quick financial summary for the Operation Center."""
    org_id = current_user.organization_id
    today = date.today()
    month_start = today.replace(day=1)

    # MTD
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

    return {
        "mtd_revenue": float(mtd_rev.scalar() or 0),
        "mtd_costs": float(mtd_cost.scalar() or 0),
        "mtd_net": float(mtd_rev.scalar() or 0) - float(mtd_cost.scalar() or 0),
    }
