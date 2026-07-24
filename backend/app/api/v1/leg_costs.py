"""Per-leg cost logging, audit trail, and mission P&L endpoints.

POST /api/v1/missions/{mission_id}/legs/{leg_number}/costs — log a cost
GET  /api/v1/missions/{mission_id}/costs                — all leg costs
GET  /api/v1/missions/{mission_id}/pnl                  — mission P&L
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.core.audit import log_action
from app.core.permissions import require_org_membership
from app.models.airport import Airport
from app.models.leg_cost import LegCost, LegCostCategory, PaymentMethod
from app.models.mission import Mission, FlightLeg
from app.models.user import User
from app.schemas.leg_costs import (
    CategoryBreakdown,
    LegCostCreate,
    LegCostResponse,
    LegCostSummary,
    MissionCostsResponse,
    MissionPnLResponse,
)

router = APIRouter(prefix="/missions", tags=["leg-costs"])


# ── Helpers ────────────────────────────────────────────────────


async def _resolve_leg(
    db: AsyncSession,
    mission_id: str,
    leg_number: int,
    org_id: str,
) -> tuple[Mission, FlightLeg]:
    """Resolve a mission and its leg by leg_number, verifying org access."""
    mission = await db.get(Mission, mission_id)
    if not mission or mission.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Mission not found")

    # Find the leg by leg_number within the mission
    # Use a query to avoid loading all legs if there are many
    result = await db.execute(
        select(FlightLeg).where(
            FlightLeg.mission_id == mission_id,
            FlightLeg.leg_number == leg_number,
        )
    )
    leg = result.scalar_one_or_none()
    if not leg:
        raise HTTPException(
            status_code=404,
            detail=f"Leg {leg_number} not found in mission {mission_id}",
        )
    return mission, leg


def _calc_estimated_from_airport(dest: Airport) -> float:
    """Replicate route planner's cash estimate from airport fields."""
    return round(
        (dest.landing_fee_usd or 0)
        + (dest.overnight_parking_usd or 0)
        + (dest.handling_fee_usd or 0)
        + (dest.customs_fee_usd or 0),
        2,
    )


# ── POST: Log a cost for a specific leg ────────────────────────


@router.post("/{mission_id}/legs/{leg_number}/costs", status_code=status.HTTP_201_CREATED)
async def log_leg_cost(
    mission_id: str,
    leg_number: int,
    body: LegCostCreate,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> LegCostResponse:
    """Log a cost against a specific leg of a mission.

    The leg is identified by its leg_number within the mission
    (e.g. leg 1 = first leg).  Creates an audit log entry alongside
    the cost record.
    """
    mission, leg = await _resolve_leg(db, mission_id, leg_number, current_user.organization_id)

    # Validate category enum
    try:
        category = LegCostCategory(body.category.lower())
    except ValueError:
        valid = [e.value for e in LegCostCategory]
        raise HTTPException(
            status_code=422,
            detail=f"Invalid category '{body.category}'. Valid: {valid}",
        )

    # Validate payment method enum
    try:
        payment_method = PaymentMethod(body.payment_method.lower())
    except ValueError:
        valid = [e.value for e in PaymentMethod]
        raise HTTPException(
            status_code=422,
            detail=f"Invalid payment_method '{body.payment_method}'. Valid: {valid}",
        )

    cost = LegCost(
        id=str(uuid.uuid4()),
        flight_leg_id=leg.id,
        category=category,
        amount=body.amount,
        currency=body.currency.upper() if body.currency else "USD",
        payment_method=payment_method,
        notes=body.notes,
        receipt_url=body.receipt_url,
        logged_by=current_user.display_name or current_user.email,
        logged_at=datetime.now(timezone.utc),
    )
    db.add(cost)
    await db.flush()

    # Audit trail
    await log_action(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        action="cost_logged",
        entity_type="leg_cost",
        entity_id=cost.id,
        new_values={
            "mission_id": mission_id,
            "leg_number": leg_number,
            "leg_id": leg.id,
            "route": f"{leg.departure_airport}→{leg.arrival_airport}",
            "category": category.value,
            "amount": body.amount,
            "currency": cost.currency,
            "payment_method": payment_method.value,
            "notes": body.notes,
            "receipt_url": body.receipt_url,
        },
    )

    await db.commit()
    await db.refresh(cost)
    return LegCostResponse.model_validate(cost)


# ── GET: All leg costs for a mission, grouped by leg ──────────


@router.get("/{mission_id}/costs")
async def get_mission_costs(
    mission_id: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> MissionCostsResponse:
    """Return all leg costs for a mission, grouped per-leg.

    Cancelled and diverted legs are shown at the end of the list
    with their costs, but excluded from the main operational rollup.
    """
    mission = await db.get(Mission, mission_id)
    if not mission or mission.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Mission not found")

    # Load legs eagerly with their costs
    stmt = (
        select(FlightLeg)
        .options(selectinload(FlightLeg.mission))
        .where(FlightLeg.mission_id == mission_id)
        .order_by(FlightLeg.leg_number)
    )
    result = await db.execute(stmt)
    legs = list(result.scalars().all())

    if not legs:
        return MissionCostsResponse(mission_id=mission_id, leg_count=0, legs=[],
                                     completed_leg_count=0, cancelled_leg_count=0)

    # Pre-fetch all LegCost records for these legs
    leg_ids = [leg.id for leg in legs]
    cost_stmt = (
        select(LegCost)
        .where(LegCost.flight_leg_id.in_(leg_ids))
        .order_by(LegCost.logged_at.desc())
    )
    cost_result = await db.execute(cost_stmt)
    cost_records = list(cost_result.scalars().all())

    # Group costs by leg_id
    costs_by_leg: dict[str, list[LegCost]] = {}
    for c in cost_records:
        costs_by_leg.setdefault(c.flight_leg_id, []).append(c)

    # Batch-load all destination airports at once (fix N+1)
    airport_icaos = {leg.arrival_airport.upper() for leg in legs}
    airport_stmt = select(Airport).where(Airport.icao_code.in_(airport_icaos))
    airport_result = await db.execute(airport_stmt)
    airport_map: dict[str, Airport] = {}
    for apt in airport_result.scalars().all():
        airport_map[apt.icao_code] = apt

    # Classify legs
    active_legs: list[FlightLeg] = []
    cancelled_legs: list[FlightLeg] = []
    for leg in legs:
        if leg.status.value in ("cancelled", "diverted"):
            cancelled_legs.append(leg)
        else:
            active_legs.append(leg)

    def _build_summary(leg: FlightLeg) -> LegCostSummary:
        actual_costs = costs_by_leg.get(leg.id, [])
        total_actual = sum(c.amount for c in actual_costs)
        dest = airport_map.get(leg.arrival_airport.upper())
        estimated = _calc_estimated_from_airport(dest) if dest else 0.0
        return LegCostSummary(
            leg_number=leg.leg_number,
            departure_airport=leg.departure_airport,
            arrival_airport=leg.arrival_airport,
            status=leg.status.value,
            estimated_cash_needed=estimated,
            actual_costs=[LegCostResponse.model_validate(c) for c in actual_costs],
            total_actual=round(total_actual, 2),
            variance=round(total_actual - estimated, 2),
        )

    leg_summaries = [_build_summary(leg) for leg in active_legs]
    # Append cancelled legs at the end with dimmed indicator
    leg_summaries.extend(_build_summary(leg) for leg in cancelled_legs)

    completed_count = sum(1 for leg in legs if leg.status.value == "completed")
    cancelled_count = len(cancelled_legs)

    return MissionCostsResponse(
        mission_id=mission_id,
        leg_count=len(leg_summaries),
        completed_leg_count=completed_count,
        cancelled_leg_count=cancelled_count,
        legs=leg_summaries,
    )


# ── GET: Mission P&L ───────────────────────────────────────────


@router.get("/{mission_id}/pnl")
async def get_mission_pnl(
    mission_id: str,
    current_user: User = Depends(require_org_membership),
    db: AsyncSession = Depends(get_db),
) -> MissionPnLResponse:
    """Real-time mission profit & loss summary.

    Cancelled and diverted legs are excluded from estimated and
    actual cost totals. Their costs can still be viewed via the
    /costs endpoint.
    """
    mission = await db.get(Mission, mission_id)
    if not mission or mission.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Mission not found")

    # Load legs
    stmt = (
        select(FlightLeg)
        .where(FlightLeg.mission_id == mission_id)
        .order_by(FlightLeg.leg_number)
    )
    result = await db.execute(stmt)
    legs = list(result.scalars().all())

    if not legs:
        return MissionPnLResponse(
            mission_id=mission_id,
            leg_count=0,
            completed_leg_count=0,
            cancelled_leg_count=0,
        )

    # Split legs by status — cancelled/diverted excluded from financial rollup
    active_legs = [leg for leg in legs if leg.status.value not in ("cancelled", "diverted")]
    cancelled_legs = [leg for leg in legs if leg.status.value in ("cancelled", "diverted")]

    # Batch-load destination airports (fix N+1)
    airport_icaos = {leg.arrival_airport.upper() for leg in active_legs}
    airport_stmt = select(Airport).where(Airport.icao_code.in_(airport_icaos))
    airport_result = await db.execute(airport_stmt)
    airport_map: dict[str, Airport] = {}
    for apt in airport_result.scalars().all():
        airport_map[apt.icao_code] = apt

    # Total estimated: sum airport fee estimates per active leg only
    total_estimated = 0.0
    for leg in active_legs:
        dest = airport_map.get(leg.arrival_airport.upper())
        total_estimated += _calc_estimated_from_airport(dest) if dest else 0.0
    total_estimated = round(total_estimated, 2)

    # Total actual: sum LegCost records for active legs only
    active_leg_ids = [leg.id for leg in active_legs]
    all_leg_ids = [leg.id for leg in legs]
    if active_leg_ids:
        cost_stmt = select(LegCost).where(LegCost.flight_leg_id.in_(active_leg_ids))
        cost_result = await db.execute(cost_stmt)
        all_costs = list(cost_result.scalars().all())
    else:
        all_costs = []

    total_actual = round(sum(c.amount for c in all_costs), 2)

    # Per-category breakdown
    category_totals: dict[str, float] = {}
    category_counts: dict[str, int] = {}
    for c in all_costs:
        cat = c.category.value if hasattr(c.category, "value") else str(c.category)
        category_totals[cat] = category_totals.get(cat, 0.0) + c.amount
        category_counts[cat] = category_counts.get(cat, 0) + 1

    per_category = [
        CategoryBreakdown(
            category=cat,
            total=round(total, 2),
            count=category_counts[cat],
        )
        for cat, total in sorted(category_totals.items())
    ]

    variance = round(total_actual - total_estimated, 2)
    completed_count = sum(1 for leg in legs if leg.status.value == "completed")
    cancelled_count = len(cancelled_legs)

    return MissionPnLResponse(
        mission_id=mission_id,
        total_estimated_costs=total_estimated,
        total_actual_costs=total_actual,
        variance=variance,
        per_category=per_category,
        leg_count=len(legs),
        completed_leg_count=completed_count,
        cancelled_leg_count=cancelled_count,
    )
