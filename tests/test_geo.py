"""Tests for geographic helpers."""

from __future__ import annotations

import math

from custom_components.piaware_adsb.geo import (
    bearing_degrees,
    compass_point,
    distance_miles,
)


def test_distance_one_degree_latitude() -> None:
    # One degree of latitude is ~69.09 statute miles.
    assert math.isclose(distance_miles(0.0, 0.0, 1.0, 0.0), 69.09, abs_tol=0.2)


def test_distance_is_zero_for_same_point() -> None:
    assert distance_miles(43.0, -76.0, 43.0, -76.0) == 0.0


def test_bearing_north_and_east() -> None:
    assert math.isclose(bearing_degrees(0.0, 0.0, 1.0, 0.0), 0.0, abs_tol=0.5)
    assert math.isclose(bearing_degrees(0.0, 0.0, 0.0, 1.0), 90.0, abs_tol=0.5)


def test_compass_points() -> None:
    assert compass_point(0) == "north"
    assert compass_point(90) == "east"
    assert compass_point(180) == "south"
    assert compass_point(270) == "west"
    assert compass_point(45) == "north-east"
    assert compass_point(315) == "north-west"
    assert compass_point(359) == "north"
