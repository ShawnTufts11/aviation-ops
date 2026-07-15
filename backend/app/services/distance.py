"""
Great-circle distance calculator — the geometry engine for route planning.

Uses the Haversine formula to compute distances between any pair of
coordinates. Accurate to ~0.5% for aviation-grade route calculations.
"""

from __future__ import annotations

import math

# Earth's mean radius in various units
R_KM = 6371.0
R_NM = 3440.065  # 6371 km ÷ 1.852
R_MILES = 3958.8


def haversine_radians(
    lat1_deg: float, lon1_deg: float,
    lat2_deg: float, lon2_deg: float,
) -> tuple[float, float, float]:
    """
    Compute great-circle distance using the Haversine formula.

    Returns (distance_nm, distance_km, distance_miles).
    """
    dlat = math.radians(lat2_deg - lat1_deg)
    dlon = math.radians(lon2_deg - lon1_deg)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1_deg))
        * math.cos(math.radians(lat2_deg))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    nm = R_NM * c
    km = R_KM * c
    mi = R_MILES * c

    return round(nm, 1), round(km, 1), round(mi, 1)


def initial_bearing(
    lat1_deg: float, lon1_deg: float,
    lat2_deg: float, lon2_deg: float,
) -> float:
    """Calculate the initial great-circle bearing (true) from point 1 to point 2."""
    dlon = math.radians(lon2_deg - lon1_deg)
    lat1 = math.radians(lat1_deg)
    lat2 = math.radians(lat2_deg)

    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)

    return (math.degrees(math.atan2(x, y)) + 360) % 360
