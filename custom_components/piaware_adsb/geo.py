"""Geographic helpers for the PiAware ADS-B integration."""

from __future__ import annotations

from math import asin, atan2, cos, degrees, radians, sin, sqrt

EARTH_RADIUS_MILES: float = 3958.7613

_COMPASS_POINTS: tuple[str, ...] = (
    "north",
    "north-east",
    "east",
    "south-east",
    "south",
    "south-west",
    "west",
    "north-west",
)


def distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance between two points in statute miles."""
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lon2 - lon1)
    a = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * asin(min(1.0, sqrt(a)))


def bearing_degrees(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the initial bearing in degrees (0-360) from point 1 to point 2."""
    phi1, phi2 = radians(lat1), radians(lat2)
    d_lambda = radians(lon2 - lon1)
    y = sin(d_lambda) * cos(phi2)
    x = cos(phi1) * sin(phi2) - sin(phi1) * cos(phi2) * cos(d_lambda)
    return (degrees(atan2(y, x)) + 360) % 360


def compass_point(bearing: float) -> str:
    """Convert a bearing in degrees to an 8-point compass name."""
    index = int((bearing + 22.5) // 45) % 8
    return _COMPASS_POINTS[index]
