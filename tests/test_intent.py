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
from custom_components.piaware_adsb.registration import AircraftMeta


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
    speech = build_speech(_aircraft(), route, phonetic=False)

    assert speech.startswith("DAL100")
    assert "4 miles to the north-east" in speech
    assert "from ATL to JFK" in speech
    assert "Delta Air Lines" in speech


def test_build_speech_phonetic_airline_style() -> None:
    route = RouteInfo(
        ident="DAL100",
        origin="ATL",
        destination="JFK",
        airline="Delta Air Lines",
    )
    speech = build_speech(_aircraft(), route, phonetic=True, callsign_style="airline")

    assert speech.startswith("Delta Air Lines one zero zero")


def test_build_speech_phonetic_spells_when_no_airline() -> None:
    speech = build_speech(_aircraft(), None, phonetic=True, callsign_style="airline")

    assert speech.startswith("Delta Alpha Lima one zero zero")


def test_build_speech_phonetic_spell_every_character() -> None:
    route = RouteInfo(airline="Delta Air Lines")
    speech = build_speech(
        _aircraft(), route, phonetic=True, callsign_style="phonetic"
    )

    assert speech.startswith("Delta Alpha Lima one zero zero")


def test_build_speech_uses_city_names_when_available() -> None:
    route = RouteInfo(
        ident="DAL100",
        origin="ATL",
        destination="HND",
        origin_name="Atlanta",
        destination_name="Tokyo",
    )
    speech = build_speech(_aircraft(), route)

    assert "from Atlanta to Tokyo" in speech
    assert "ATL" not in speech
    assert "HND" not in speech


def test_build_speech_without_route_uses_altitude() -> None:
    speech = build_speech(_aircraft(), None)

    assert "32,000 feet" in speech
    assert "from" not in speech


def test_build_speech_without_aircraft_details() -> None:
    speech = build_speech(Aircraft(hex="abc123"), None)
    assert speech == "Alpha Bravo Charlie one two three."


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
        "coordinator": SimpleNamespace(
            data=PiAwareData(nearest=_aircraft()),
            phonetic_speech=False,
            callsign_style="airline",
        ),
        "enrichment": None,
    }
    intent_obj = SimpleNamespace(hass=hass, language="en")

    response = await WhatPlaneIntent().async_handle(intent_obj)

    assert "DAL100" in response.speech["plain"]["speech"]


async def test_intent_phonetic_speech(hass) -> None:
    hass.data[DOMAIN] = {
        "coordinator": SimpleNamespace(
            data=PiAwareData(nearest=_aircraft()),
            phonetic_speech=True,
            callsign_style="airline",
        ),
        "enrichment": None,
    }

    response = await WhatPlaneIntent().async_handle(
        SimpleNamespace(hass=hass, language="en")
    )

    assert "Delta Alpha Lima one zero zero" in response.speech["plain"]["speech"]


def test_build_recent_speech() -> None:
    speech = build_recent_speech(_aircraft(), None, 5.0, 120, phonetic=False)

    assert speech.startswith("No aircraft within 5 miles.")
    assert "DAL100" in speech
    assert "2 minutes ago" in speech


def test_build_speech_includes_registration() -> None:
    speech = build_speech(
        _aircraft(), None, AircraftMeta(registration="N123NW"), phonetic=False
    )
    assert "registration number N123NW" in speech


def test_build_speech_phonetic_registration() -> None:
    speech = build_speech(
        _aircraft(), None, AircraftMeta(registration="N123NW"), phonetic=True
    )
    assert "registration number November one two three November Whiskey" in speech


def test_build_speech_skips_registration_matching_callsign() -> None:
    aircraft = Aircraft(
        hex="a963ae", callsign="N704CT", distance_miles=1.0, compass="north"
    )
    speech = build_speech(aircraft, None, AircraftMeta(registration="N704CT"))
    assert "registration number" not in speech


def test_build_speech_uses_db_type_name() -> None:
    speech = build_speech(
        Aircraft(hex="a1ecfd", callsign="RPA5678"),
        None,
        AircraftMeta(type_name="EMBRAER ERJ 170-200"),
    )
    assert "an EMBRAER ERJ 170-200" in speech


def test_build_speech_falls_back_to_type_code() -> None:
    speech = build_speech(
        Aircraft(hex="a3f793"), None, AircraftMeta(type_code="A320")
    )
    assert "an A320" in speech


def test_build_speech_prefers_descriptive_type_over_route_code() -> None:
    route = RouteInfo(aircraft_type="B738")
    speech = build_speech(
        Aircraft(hex="ac1466", callsign="DAL336"),
        route,
        AircraftMeta(type_name="Boeing 737-800"),
    )
    assert "a Boeing 737-800" in speech


def test_build_recent_speech_includes_registration() -> None:
    speech = build_recent_speech(
        _aircraft(), None, 5.0, 30, AircraftMeta(registration="N123NW"), phonetic=False
    )
    assert "No aircraft within 5 miles" in speech
    assert "registration number N123NW" in speech


class _FakeDb:
    """Stub tar1090 database client."""

    async def async_get_metadata(self, icao24: str | None) -> AircraftMeta:
        return AircraftMeta(registration="N123NW", type_name="Boeing 737-800")


async def test_intent_includes_registration_and_type(hass) -> None:
    hass.data[DOMAIN] = {
        "coordinator": SimpleNamespace(
            data=PiAwareData(nearest=_aircraft()),
            phonetic_speech=False,
            callsign_style="airline",
        ),
        "enrichment": None,
        "tar1090_db": _FakeDb(),
    }

    response = await WhatPlaneIntent().async_handle(
        SimpleNamespace(hass=hass, language="en")
    )
    speech = response.speech["plain"]["speech"]

    assert "registration number N123NW" in speech
    assert "a Boeing 737-800" in speech


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
        voice_radius_miles=5.0,
        phonetic_speech=False,
        callsign_style="airline",
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
        voice_radius_miles=5.0,
        last_in_range=(_aircraft(), when),
    )
    hass.data[DOMAIN] = {"coordinator": coordinator, "enrichment": None}

    response = await WhatPlaneIntent().async_handle(
        SimpleNamespace(hass=hass, language="en")
    )

    assert "don't see any aircraft" in response.speech["plain"]["speech"]
