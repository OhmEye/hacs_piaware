"""Aircraft model and parsing for the PiAware ADS-B integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .geo import bearing_degrees, compass_point, distance_miles


@dataclass(slots=True)
class Aircraft:
    """A single aircraft decoded from a tar1090/dump1090 feed."""

    hex: str
    callsign: str | None = None
    type_code: str | None = None
    category: str | None = None
    altitude_ft: int | None = None
    on_ground: bool = False
    ground_speed_kt: float | None = None
    track: float | None = None
    squawk: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    distance_miles: float | None = None
    bearing: float | None = None
    compass: str | None = None

    @property
    def display_name(self) -> str:
        """Human friendly identifier used for naming and speech."""
        return self.callsign or self.hex.upper()

    @property
    def has_position(self) -> bool:
        return self.latitude is not None and self.longitude is not None


def _as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_aircraft(
    raw: dict[str, Any],
    home_latitude: float | None,
    home_longitude: float | None,
) -> Aircraft | None:
    """Parse one raw aircraft entry, computing distance/bearing from home."""
    hex_id = raw.get("hex")
    if not hex_id:
        return None

    altitude_raw = raw.get("alt_baro")
    on_ground = altitude_raw == "ground"
    altitude_ft = None if on_ground else _as_float(altitude_raw)

    callsign = (raw.get("flight") or "").strip() or None

    aircraft = Aircraft(
        hex=str(hex_id),
        callsign=callsign,
        type_code=raw.get("t"),
        category=raw.get("category"),
        altitude_ft=int(altitude_ft) if altitude_ft is not None else None,
        on_ground=on_ground,
        ground_speed_kt=_as_float(raw.get("gs")),
        track=_as_float(raw.get("track")),
        squawk=raw.get("squawk"),
        latitude=_as_float(raw.get("lat")),
        longitude=_as_float(raw.get("lon")),
    )

    if aircraft.has_position and home_latitude is not None and home_longitude is not None:
        aircraft.distance_miles = distance_miles(
            home_latitude, home_longitude, aircraft.latitude, aircraft.longitude
        )
        aircraft.bearing = bearing_degrees(
            home_latitude, home_longitude, aircraft.latitude, aircraft.longitude
        )
        aircraft.compass = compass_point(aircraft.bearing)

    return aircraft


def parse_aircraft_payload(
    payload: dict[str, Any],
    home_latitude: float | None,
    home_longitude: float | None,
) -> list[Aircraft]:
    """Parse a full aircraft.json payload into a list of aircraft."""
    result: list[Aircraft] = []
    for raw in payload.get("aircraft", []) or []:
        if not isinstance(raw, dict):
            continue
        parsed = parse_aircraft(raw, home_latitude, home_longitude)
        if parsed is not None:
            result.append(parsed)
    return result


def nearest_aircraft(
    aircraft: list[Aircraft], *, within_miles: float | None = None
) -> Aircraft | None:
    """Return the closest positioned aircraft, optionally within a radius."""
    candidates = [
        a
        for a in aircraft
        if a.distance_miles is not None
        and (within_miles is None or a.distance_miles <= within_miles)
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda a: a.distance_miles)  # type: ignore[arg-type,return-value]
