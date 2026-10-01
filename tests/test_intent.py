"""Tests for the Assist intent response building."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

from homeassistant.util import dt as dt_util

from custom_components.piaware_adsb.aircraft import Aircraft
from custom_components.piaware_adsb.const import DOMAIN
from custom_components.piaware_adsb.coordinator import PiAwareData
from custom_components.piaware_adsb.enrichment import RouteInfo
from custom_components.piaware_adsb.intent import (
    WhatPlaneIntent,
    _humanize_age,
    build_recent_speech,
    build_speech,
)


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


def test_build_recent_speech() -> None:
    speech = build_recent_speech(_aircraft(), None, 5.0, 120)

    assert speech.startswith("No aircraft within 5 miles.")
    assert "DAL100" in speech
    assert "2 minutes ago" in speech


def test_build_speech_includes_registration() -> None:
    speech = build_speech(_aircraft(), None, "N123NW")
    assert "registration number N123NW" in speech


def test_build_speech_skips_registration_matching_callsign() -> None:
    aircraft = Aircraft(
        hex="a963ae", callsign="N704CT", distance_miles=1.0, compass="north"
    )
    speech = build_speech(aircraft, None, "N704CT")
    assert "registration number" not in speech


def test_build_recent_speech_includes_registration() -> None:
    speech = build_recent_speech(_aircraft(), None, 5.0, 30, "N123NW")
    assert "No aircraft within 5 miles" in speech
    assert "registration number N123NW" in speech


class _FakeRegistration:
    """Stub registration client."""

    async def async_get_registration(self, icao24: str | None) -> str | None:
        return "N123NW"


async def test_intent_includes_registration(hass) -> None:
    hass.data[DOMAIN] = {
        "coordinator": SimpleNamespace(data=PiAwareData(nearest=_aircraft())),
        "enrichment": None,
        "registration": _FakeRegistration(),
    }

    response = await WhatPlaneIntent().async_handle(
        SimpleNamespace(hass=hass, language="en")
    )

    assert "registration number N123NW" in response.speech["plain"]["speech"]


def test_humanize_age() -> None:
    assert _humanize_age(3) == "just now"
    assert _humanize_age(30) == "30 seconds ago"
    assert _humanize_age(60) == "1 minute ago"
    assert _humanize_age(120) == "2 minutes ago"
    assert _humanize_age(7200) == "2 hours ago"
    assert _humanize_age(90000) == "1 day ago"


async def test_intent_reports_recent_when_nothing_in_radius(hass) -> None:
    when = dt_util.utcnow() - timedelta(minutes=2)
    coordinator = SimpleNamespace(
        data=PiAwareData(nearest=None),
        nearest_use_radius=True,
        notification_radius_miles=5.0,
        last_in_range=(_aircraft(), when),
    )
    hass.data[DOMAIN] = {"coordinator": coordinator, "enrichment": None}

    response = await WhatPlaneIntent().async_handle(
        SimpleNamespace(hass=hass, language="en")
    )
    speech = response.speech["plain"]["speech"]

    assert "No aircraft within 5 miles" in speech
    assert "DAL100" in speech
    assert "2 minutes ago" in speech


async def test_intent_ignores_recent_cache_without_radius(hass) -> None:
    when = dt_util.utcnow() - timedelta(minutes=2)
    coordinator = SimpleNamespace(
        data=PiAwareData(nearest=None),
        nearest_use_radius=False,
        notification_radius_miles=5.0,
        last_in_range=(_aircraft(), when),
    )
    hass.data[DOMAIN] = {"coordinator": coordinator, "enrichment": None}

    response = await WhatPlaneIntent().async_handle(
        SimpleNamespace(hass=hass, language="en")
    )

    assert "don't see any aircraft" in response.speech["plain"]["speech"]
