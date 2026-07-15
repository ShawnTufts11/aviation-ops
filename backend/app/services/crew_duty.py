"""
Crew Duty Time calculator — FAR 135.267 / 135.271 compliance enforcement.

Calculates cumulative duty day and flight time limits based on the mission
schedule and the crew's last known rest period.

Key limits (FAR 135.267):
  - 8hr flight time in 24hr for single-pilot ops
  - 10hr flight time in 24hr for 2-pilot ops
  - 14hr maximum duty period
  - Minimum 10hr consecutive rest before duty
  - 500hr in any calendar quarter
  - 800hr in any two consecutive quarters
  - 1,400hr in any calendar year
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass
class CrewDutyStatus:
    """Duty time compliance status for a specific crew member on a mission."""

    crew_name: str = ""
    crew_role: str = ""
    is_pilot: bool = False

    # Current duty state
    last_duty_end: datetime | None = None
    rest_hours_received: float = 0.0
    rest_adequate: bool = True

    # Mission duty projection
    duty_start: datetime | None = None
    duty_end: datetime | None = None
    duty_period_hours: float = 0.0
    flight_time_hours: float = 0.0
    duty_period_exceeded: bool = False

    # Flight time limits (FAR 135.267)
    flight_time_24hr: float = 0.0  # Flight time in last 24 hours
    flight_time_24hr_limit: float = 10.0  # 10hr for 2-pilot, 8hr for 1-pilot
    flight_time_24hr_exceeded: bool = False

    # Cumulative limits (FAR 135.267(b))
    flight_time_quarter_hrs: float = 0.0
    flight_time_quarter_limit: float = 500.0
    flight_time_two_quarter_hrs: float = 0.0
    flight_time_two_quarter_limit: float = 800.0
    flight_time_year_hrs: float = 0.0
    flight_time_year_limit: float = 1400.0

    # Compliance
    is_legal: bool = True
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class CrewCheckResult:
    """Duty time compliance for all crew on a mission."""

    crew: list[CrewDutyStatus] = field(default_factory=list)
    mission_legal: bool = True
    mission_violations: list[str] = field(default_factory=list)


def _hours_between(a: datetime | None, b: datetime | None) -> float:
    """Return hours between two datetimes (or 0 if either is None)."""
    if not a or not b:
        return 0.0
    return abs((a - b).total_seconds()) / 3600


async def check_crew_duty(
    mission_flight_time_hrs: float,
    mission_duty_period_hrs: float | None = None,
    is_two_pilot: bool = True,
    crew_members: list[dict[str, Any]] | None = None,
    hypothetical_departure: datetime | None = None,
) -> CrewCheckResult:
    """
    Check crew duty time compliance for a planned mission.

    Args:
        mission_flight_time_hrs: Total flight time for the mission
        mission_duty_period_hrs: Total duty period (defaults to flight + 1hr pre/post)
        is_two_pilot: Whether a 2-pilot crew is assigned (affects 8hr vs 10hr limit)
        crew_members: Optional list of crew dicts with name, role, last_duty_end, cumulative times
        hypothetical_departure: Assumed departure time (defaults to now)

    Returns:
        CrewCheckResult with per-crew analysis and mission-level verdict
    """
    crew_members = crew_members or []
    departure = hypothetical_departure or datetime.now(timezone.utc)

    # Duty period: mission flight time + 1hr preflight + 0.5hr postflight
    duty_period = mission_duty_period_hrs or (mission_flight_time_hrs + 1.5)
    duty_end = departure + timedelta(hours=duty_period)

    result = CrewCheckResult()
    flight_limit = 8.0 if not is_two_pilot else 10.0

    if not crew_members:
        # No specific crew data — check generically
        status = CrewDutyStatus(
            crew_name="Assigned Crew",
            crew_role="captain/first_officer" if is_two_pilot else "single_pilot",
            is_pilot=True,
            duty_start=departure,
            duty_end=duty_end,
            duty_period_hours=round(duty_period, 2),
            flight_time_hours=round(mission_flight_time_hrs, 2),
            flight_time_24hr_limit=flight_limit,
            flight_time_24hr=round(mission_flight_time_hrs, 2),
        )

        # Check duty period (14hr max)
        if duty_period > 14:
            status.duty_period_exceeded = True
            status.violations.append(
                f"Duty period {duty_period:.1f}hrs exceeds 14-hour maximum"
            )

        # Check flight time in 24hr
        if mission_flight_time_hrs > flight_limit:
            status.flight_time_24hr_exceeded = True
            status.violations.append(
                f"Flight time {mission_flight_time_hrs:.1f}hrs exceeds "
                f"{'10hr' if is_two_pilot else '8hr'} maximum for "
                f"{'2-pilot' if is_two_pilot else '1-pilot'} crew"
            )

        status.is_legal = len(status.violations) == 0
        result.crew.append(status)

    else:
        for crew in crew_members:
            last_duty = crew.get("last_duty_end")
            rest_hrs = _hours_between(last_duty, departure) if last_duty else 99.0
            rest_ok = rest_hrs >= 10.0

            status = CrewDutyStatus(
                crew_name=crew.get("name", "Unknown"),
                crew_role=crew.get("role", "pilot"),
                is_pilot=crew.get("is_pilot", True),
                last_duty_end=last_duty,
                rest_hours_received=round(rest_hrs, 1),
                rest_adequate=rest_ok,
                duty_start=departure,
                duty_end=duty_end,
                duty_period_hours=round(duty_period, 2),
                flight_time_hours=round(mission_flight_time_hrs, 2),
                flight_time_24hr_limit=flight_limit,
                flight_time_24hr=round(crew.get("flight_time_24hr", 0) + mission_flight_time_hrs, 2),
                flight_time_quarter_hrs=round(crew.get("flight_time_quarter_hrs", 0) + mission_flight_time_hrs, 2),
                flight_time_two_quarter_hrs=round(crew.get("flight_time_two_quarter_hrs", 0) + mission_flight_time_hrs, 2),
                flight_time_year_hrs=round(crew.get("flight_time_year_hrs", 0) + mission_flight_time_hrs, 2),
            )

            # ── Rest check ────────────────────────────────────────────────
            if not rest_ok:
                status.violations.append(
                    f"Insufficient rest: {rest_hrs:.1f}hrs (minimum 10hrs required)"
                )

            # ── Duty period ───────────────────────────────────────────────
            if duty_period > 14:
                status.duty_period_exceeded = True
                status.violations.append(
                    f"Duty period {duty_period:.1f}hrs exceeds 14-hour maximum"
                )

            # ── Flight time in 24hr ───────────────────────────────────────
            if status.flight_time_24hr > flight_limit:
                status.flight_time_24hr_exceeded = True
                status.violations.append(
                    f"Total flight time {status.flight_time_24hr:.1f}hrs in 24hr exceeds "
                    f"{flight_limit:.0f}hr limit"
                )

            # ── Cumulative limits ─────────────────────────────────────────
            if status.flight_time_quarter_hrs > status.flight_time_quarter_limit:
                status.violations.append(
                    f"Quarterly flight time {status.flight_time_quarter_hrs:.0f}hrs exceeds "
                    f"{status.flight_time_quarter_limit:.0f}hr limit"
                )

            if status.flight_time_two_quarter_hrs > status.flight_time_two_quarter_limit:
                status.violations.append(
                    f"Two-quarter flight time {status.flight_time_two_quarter_hrs:.0f}hrs exceeds "
                    f"{status.flight_time_two_quarter_limit:.0f}hr limit"
                )

            if status.flight_time_year_hrs > status.flight_time_year_limit:
                status.violations.append(
                    f"Annual flight time {status.flight_time_year_hrs:.0f}hrs exceeds "
                    f"{status.flight_time_year_limit:.0f}hr limit"
                )

            # ── Warnings ─────────────────────────────────────────────────
            if duty_period > 12:
                status.warnings.append(f"Duty period approaching 14hr limit ({duty_period:.1f}hrs)")
            if status.flight_time_24hr > flight_limit * 0.85:
                status.warnings.append(
                    f"Flight time {status.flight_time_24hr:.1f}hrs approaching "
                    f"{flight_limit:.0f}hr limit"
                )
            if rest_hrs < 12:
                status.warnings.append(f"Marginal rest: {rest_hrs:.1f}hrs")

            status.is_legal = len(status.violations) == 0
            result.crew.append(status)

    # ── Mission verdict ──────────────────────────────────────────────────
    for crew_status in result.crew:
        result.mission_violations.extend(crew_status.violations)

    result.mission_legal = all(c.is_legal for c in result.crew)

    return result


def duty_check_to_dict(
    result: CrewCheckResult,
    is_two_pilot: bool = True,
    departure_time: str | None = None,
) -> dict[str, Any]:
    """Convert CrewCheckResult to JSON-serializable dict."""
    flight_limit = 10.0 if is_two_pilot else 8.0

    return {
        "is_two_pilot": is_two_pilot,
        "flight_time_limit_24hr": flight_limit,
        "departure_time": departure_time or "now",
        "mission_legal": result.mission_legal,
        "mission_violations": result.mission_violations,
        "crew": [
            {
                "name": c.crew_name,
                "role": c.crew_role,
                "is_pilot": c.is_pilot,
                "rest": {
                    "last_duty_end": c.last_duty_end.isoformat() if c.last_duty_end else None,
                    "rest_hours_received": c.rest_hours_received,
                    "rest_adequate": c.rest_adequate,
                },
                "duty": {
                    "duty_period_hours": c.duty_period_hours,
                    "duty_period_exceeded": c.duty_period_exceeded,
                    "flight_time_hours": c.flight_time_hours,
                    "flight_time_24hr": c.flight_time_24hr,
                    "flight_time_24hr_exceeded": c.flight_time_24hr_exceeded,
                    "flight_time_quarter_hrs": c.flight_time_quarter_hrs,
                    "flight_time_two_quarter_hrs": c.flight_time_two_quarter_hrs,
                    "flight_time_year_hrs": c.flight_time_year_hrs,
                },
                "is_legal": c.is_legal,
                "violations": c.violations,
                "warnings": c.warnings,
            }
            for c in result.crew
        ],
    }
