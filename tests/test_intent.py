"""Tests for the Assist intent response building."""

from __future__ import annotations

from types import SimpleNamespace

from custom_components.piaware_adsb.aircraft import Aircraft
from custom_components.piaware_adsb.const import DOMAIN
from custom_components.piaware_adsb.coordinator import PiAwareData
from custom_components.piaware_adsb.enrichment import RouteInfo
from custom_components.piaware_adsb.intent import WhatPlaneIntent, build_speech


def _aircraft() -> Aircraft:
    return Aircraft(
        hex="abc123",
        callsign="DAL100",
        type_code="B738",
        altitude_ft=32000,
        distance_miles=4.3,
        compass="north-east",
    )


def test_build_speech_with_route() -> None:
    route = RouteInfo(
        ident="DAL100",
        origin="ATL",
        destination="JFK",
        airline="Delta Air Lines",
        aircraft_type="B738",
    )
    speech = build_speech(_aircraft(), route)

    assert speech.startswith("DAL100")
    assert "4 miles to the north-east" in speech
    assert "from ATL to JFK" in speech
    assert "Delta Air Lines" in speech


def test_build_speech_without_route_uses_altitude() -> None:
    speech = build_speech(_aircraft(), None)

    assert "32,000 feet" in speech
    assert "from" not in speech


def test_build_speech_without_aircraft_details() -> None:
    speech = build_speech(Aircraft(hex="abc123"), None)
    assert speech == "ABC123."


async def test_intent_without_traffic(hass) -> None:
    hass.data[DOMAIN] = {
        "coordinator": SimpleNamespace(data=PiAwareData()),
        "enrichment": None,
    }
    intent_obj = SimpleNamespace(hass=hass, language="en")

    response = await WhatPlaneIntent().async_handle(intent_obj)

    assert "don't see any aircraft" in response.speech["plain"]["speech"]


async def test_intent_returns_nearest(hass) -> None:
    hass.data[DOMAIN] = {
        "coordinator": SimpleNamespace(data=PiAwareData(nearest=_aircraft())),
        "enrichment": None,
    }
    intent_obj = SimpleNamespace(hass=hass, language="en")

    response = await WhatPlaneIntent().async_handle(intent_obj)

    assert "DAL100" in response.speech["plain"]["speech"]
