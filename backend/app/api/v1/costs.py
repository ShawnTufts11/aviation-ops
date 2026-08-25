"""Cost reconciliation endpoints — estimated vs actual flight costs.

POST /api/v1/flights/{flight_id}/actual-costs — record actual costs paid
GET  /api/v1/flights/{flight_id}/costs         — estimated vs actual comparison
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_org_membership
from app.models.airport import Airport
from app.models.finance import CostCategory, FinancialRecord, RecordType
from app.models.flight import Flight
from app.models.user import User
from app.schemas.costs import ActualCostLineItems, ActualCostsCreate, CostComparison

router = APIRouter(prefix="/flights", tags=["costs"])

# ── Helpers ────────────────────────────────────────────────────────────────

_CATEGORY_MAP: dict[str, CostCategory] = {
    "landing_fee_usd": CostCategory.LANDING_FEES,
    "overnight_parking_usd": CostCategory.LANDING_FEES,
    "handling_fee_usd": CostCategory.HANDLING,
    "customs_fee_usd": CostCategory.CUSTOMS,
}

_DESCRIPTION_MAP: dict[str, str] = {
    "landing_fee_usd": "Landing fee",
    "overnight_parking_usd": "Overnight parking",
    "handling_fee_usd": "Ramp handling",
    "customs_fee_usd": "Customs/CIQ processing",
}


def _cost_from_db_record(record: FinancialRecord, field: str) -> float:
    """Extract a cost line item from a financial record."""
    return float(record.amount) if record else 0.0


async def _get_records_for_flight(
    db: AsyncSession, flight_id: str, category: CostCategory | None = None
) -> list[FinancialRecord]:
    """Get financial records for a flight, optionally filtered by category."""
    stmt = select(FinancialRecord).where(
        FinancialRecord.flight_id == flight_id,
        FinancialRecord.record_type == RecordType.COST,
    )
    if category:
        stmt = stmt.where(FinancialRecord.category == category)
    stmt = stmt.order_by(FinancialRecord.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ── POST: Record actual costs ────────────────────────────────────────────


@router.post("/{flight_id}/actual-costs", status_code=status.HTTP_201_CREATED)
async def record_actual_costs(
    flight_id: str,
    body: ActualCostsCreate,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Record actual costs paid for a flight (landing, parking, handling, customs).

    Creates FinancialRecord entries for each non-zero cost category.
    """
    # Verify flight exists
    flight = await db.get(Flight, flight_id)
    if not flight or flight.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Flight not found")

    entry_date = body.entry_date or date.today()
    created_records: list[str] = []

    cost_fields = [
        ("landing_fee_usd", body.landing_fee_usd),
        ("overnight_parking_usd", body.overnight_parking_usd),
        ("handling_fee_usd", body.handling_fee_usd),
        ("customs_fee_usd", body.customs_fee_usd),
    ]

    for field_name, amount in cost_fields:
        if not amount or amount <= 0:
            continue

        category = _CATEGORY_MAP[field_name]
        rec = FinancialRecord(
            id=str(uuid.uuid4()),
            organization_id=current_user.organization_id,
            aircraft_id=flight.aircraft_id,
            flight_id=flight.id,
            record_type=RecordType.COST,
            category=category,
            amount=Decimal(str(round(amount, 2))),
            description=f"{_DESCRIPTION_MAP[field_name]} — {flight.departure_airport}→{flight.arrival_airport}",
            entry_date=entry_date,
        )
        if body.notes:
            rec.description = f"{rec.description} ({body.notes})"

        db.add(rec)
        created_records.append(field_name)

    await db.commit()

    return {
        "status": "ok",
        "flight_id": flight_id,
        "records_created": created_records,
        "entry_date": entry_date.isoformat(),
    }


# ── GET: Estimated vs actual cost comparison ─────────────────────────────


@router.get("/{flight_id}/costs")
async def get_cost_comparison(
    flight_id: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> CostComparison:
    """Compare estimated vs actual costs for a flight.

    Estimated costs come from the destination airport's cost fields.
    Actual costs come from FinancialRecord entries for this flight.
    """
    flight = await db.get(Flight, flight_id)
    if not flight or flight.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Flight not found")

    # ── Estimated costs from destination airport ────────────────────────
    dest = await db.get(Airport, flight.arrival_airport.upper())
    if not dest:
        estimated = ActualCostLineItems()
    else:
        estimated = ActualCostLineItems(
            landing_fee_usd=dest.landing_fee_usd or 0.0,
            overnight_parking_usd=dest.overnight_parking_usd or 0.0,
            handling_fee_usd=dest.handling_fee_usd or 0.0,
            customs_fee_usd=dest.customs_fee_usd or 0.0,
        )
    estimated.total = round(
        estimated.landing_fee_usd
        + estimated.overnight_parking_usd
        + estimated.handling_fee_usd
        + estimated.customs_fee_usd,
        2,
    )

    # ── Actual costs from financial records ─────────────────────────────
    records = await _get_records_for_flight(db, flight_id)
    actual_landing = Decimal("0.00")
    actual_parking = Decimal("0.00")
    actual_handling = Decimal("0.00")
    actual_customs = Decimal("0.00")

    for rec in records:
        if rec.category == CostCategory.LANDING_FEES:
            # Check description for parking vs landing heuristic
            if rec.description and "parking" in rec.description.lower():
                actual_parking += rec.amount
            else:
                actual_landing += rec.amount
        elif rec.category == CostCategory.HANDLING:
            actual_handling += rec.amount
        elif rec.category == CostCategory.CUSTOMS:
            actual_customs += rec.amount

    actual = ActualCostLineItems(
        landing_fee_usd=float(actual_landing),
        overnight_parking_usd=float(actual_parking),
        handling_fee_usd=float(actual_handling),
        customs_fee_usd=float(actual_customs),
    )
    actual.total = round(
        actual.landing_fee_usd + actual.overnight_parking_usd
        + actual.handling_fee_usd + actual.customs_fee_usd,
        2,
    )

    # ── Variances (actual - estimated) ─────────────────────────────────
    variances = ActualCostLineItems(
        landing_fee_usd=round(actual.landing_fee_usd - estimated.landing_fee_usd, 2),
        overnight_parking_usd=round(actual.overnight_parking_usd - estimated.overnight_parking_usd, 2),
        handling_fee_usd=round(actual.handling_fee_usd - estimated.handling_fee_usd, 2),
        customs_fee_usd=round(actual.customs_fee_usd - estimated.customs_fee_usd, 2),
    )
    variances.total = round(
        variances.landing_fee_usd + variances.overnight_parking_usd
        + variances.handling_fee_usd + variances.customs_fee_usd,
        2,
    )

    return CostComparison(
        flight_id=flight.id,
        departure_airport=flight.departure_airport,
        arrival_airport=flight.arrival_airport,
        estimated=estimated,
        actual=actual,
        variances=variances,
    )
