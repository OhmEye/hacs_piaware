"""Tests for aircraft parsing and nearest-aircraft selection."""

from __future__ import annotations

from custom_components.piaware_adsb.aircraft import (
    Aircraft,
    nearest_aircraft,
    parse_aircraft_payload,
    select_type_name,
)
from custom_components.piaware_adsb.enrichment import RouteInfo
from custom_components.piaware_adsb.registration import AircraftMeta

HOME_LAT = 43.0
HOME_LON = -76.0


def test_parse_computes_distance_and_compass(aircraft_payload: dict) -> None:
    aircraft = parse_aircraft_payload(aircraft_payload, HOME_LAT, HOME_LON)
    by_hex = {a.hex: a for a in aircraft}

    dal = by_hex["abc123"]
    assert dal.callsign == "DAL100"
    assert dal.distance_miles is not None
    assert dal.distance_miles < 6
    assert dal.compass is not None


def test_aircraft_without_position_has_no_distance(aircraft_payload: dict) -> None:
    aircraft = parse_aircraft_payload(aircraft_payload, HOME_LAT, HOME_LON)
    no_pos = next(a for a in aircraft if a.hex == "a53436")
    assert no_pos.distance_miles is None
    assert no_pos.has_position is False


def test_callsign_falls_back_to_hex(aircraft_payload: dict) -> None:
    aircraft = parse_aircraft_payload(aircraft_payload, HOME_LAT, HOME_LON)
    no_callsign = next(a for a in aircraft if a.hex == "c06363")
    assert no_callsign.callsign is None
    assert no_callsign.display_name == "C06363"


def test_on_ground_aircraft(aircraft_payload: dict) -> None:
    aircraft = parse_aircraft_payload(aircraft_payload, HOME_LAT, HOME_LON)
    ground = next(a for a in aircraft if a.hex == "dead01")
    assert ground.on_ground is True
    assert ground.altitude_ft is None


def test_nearest_aircraft_ignores_unpositioned(aircraft_payload: dict) -> None:
    aircraft = parse_aircraft_payload(aircraft_payload, HOME_LAT, HOME_LON)
    nearest = nearest_aircraft(aircraft)
    assert nearest is not None
    assert nearest.hex == "dead01"


def test_nearest_aircraft_within_radius(aircraft_payload: dict) -> None:
    aircraft = parse_aircraft_payload(aircraft_payload, HOME_LAT, HOME_LON)
    nearest = nearest_aircraft(aircraft, within_miles=10)
    assert nearest is not None
    assert nearest.hex in {"abc123", "dead01"}


def test_nearest_returns_none_when_empty() -> None:
    assert nearest_aircraft([]) is None


def test_select_type_name_prefers_descriptive() -> None:
    route = RouteInfo(aircraft_type="B738")
    meta = AircraftMeta(type_name="Boeing 737-800")
    assert select_type_name(route, meta, Aircraft(hex="abc123")) == "Boeing 737-800"


def test_select_type_name_falls_back_to_code() -> None:
    assert (
        select_type_name(None, AircraftMeta(type_code="A320"), Aircraft(hex="abc123"))
        == "A320"
    )
    assert select_type_name(None, None, Aircraft(hex="abc123", type_code="C172")) == "C172"


def test_select_type_name_none_when_unknown() -> None:
    assert select_type_name(None, None, Aircraft(hex="abc123")) is None
