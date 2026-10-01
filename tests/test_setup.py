"""End-to-end setup and options-flow tests."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.piaware_adsb.const import (
    CONF_API_KEY,
    CONF_COUNT_USE_RADIUS,
    CONF_ENRICH_NOTIFICATIONS,
    CONF_HOST,
    CONF_INSTALL_SENTENCES,
    CONF_NEAREST_USE_RADIUS,
    CONF_NOTIFICATION_RADIUS_MILES,
    CONF_NOTIFICATIONS_ENABLED,
    CONF_PATH,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DOMAIN,
    EVENT_AIRCRAFT_OVERHEAD,
)

FEED_URL = "http://piaware.lan:80/tar1090/data/aircraft.json"
AEROAPI_GRND1 = "https://aeroapi.flightaware.com/aeroapi/flights/GRND1"

ENTRY_DATA = {
    CONF_HOST: "piaware.lan",
    CONF_PORT: 80,
    CONF_PATH: "/tar1090/data/aircraft.json",
    CONF_SCAN_INTERVAL: 10,
    CONF_NOTIFICATIONS_ENABLED: True,
    CONF_NOTIFICATION_RADIUS_MILES: 5.0,
    CONF_ENRICH_NOTIFICATIONS: False,
    CONF_COUNT_USE_RADIUS: False,
    CONF_NEAREST_USE_RADIUS: False,
    CONF_INSTALL_SENTENCES: False,
}

AEROAPI_ROUTE = {
    "flights": [
        {
            "ident": "GRND1",
            "status": "En Route",
            "operator": "Delta Air Lines",
            "aircraft_type": "B738",
            "origin": {"code_iata": "ATL"},
            "destination": {"code_iata": "JFK"},
        }
    ]
}


async def test_setup_creates_entities(
    hass: HomeAssistant, aioclient_mock, aircraft_payload: dict
) -> None:
    aioclient_mock.get(FEED_URL, json=aircraft_payload)
    hass.config.latitude = 43.0
    hass.config.longitude = -76.0
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.piaware_ads_b_nearest_aircraft") is not None
    assert hass.states.get("sensor.piaware_ads_b_nearest_aircraft_distance") is not None
    assert hass.states.get("sensor.piaware_ads_b_aircraft_in_range") is not None

    overhead = hass.states.get("binary_sensor.piaware_ads_b_aircraft_overhead")
    assert overhead is not None

    nearest = hass.states.get("sensor.piaware_ads_b_nearest_aircraft")
    assert nearest.state == "GRND1"

    # Default: the count sensor reports all positioned aircraft (4 with a position).
    in_range = hass.states.get("sensor.piaware_ads_b_aircraft_in_range")
    assert in_range.state == "4"

    # The most recent in-radius aircraft is remembered for the voice fallback.
    assert hass.data[DOMAIN]["coordinator"].last_in_range is not None

    # The overhead notification blueprint is installed into the config dir.
    blueprint = Path(
        hass.config.path("blueprints/automation/piaware_adsb/overhead_notify.yaml")
    )
    assert blueprint.is_file()

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_radius_toggles_restrict_count_and_nearest(
    hass: HomeAssistant, aioclient_mock, aircraft_payload: dict
) -> None:
    aioclient_mock.get(FEED_URL, json=aircraft_payload)
    hass.config.latitude = 43.0
    hass.config.longitude = -76.0

    data = {
        **ENTRY_DATA,
        CONF_NOTIFICATION_RADIUS_MILES: 0.5,
        CONF_COUNT_USE_RADIUS: True,
        CONF_NEAREST_USE_RADIUS: True,
    }
    entry = MockConfigEntry(domain=DOMAIN, data=data)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Nothing is within 0.5 mi, so the radius-limited sensors are unavailable
    # rather than reporting 0 / unknown.
    assert hass.states.get("sensor.piaware_ads_b_aircraft_in_range").state == "unavailable"
    assert hass.states.get("sensor.piaware_ads_b_nearest_aircraft").state == "unavailable"
    assert hass.states.get("sensor.piaware_ads_b_nearest_aircraft_distance").state == "unavailable"


async def test_callsign_retained_when_feed_omits_it(
    hass: HomeAssistant, aioclient_mock, aircraft_payload: dict
) -> None:
    aioclient_mock.get(FEED_URL, json=aircraft_payload)
    hass.config.latitude = 43.0
    hass.config.longitude = -76.0

    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.piaware_ads_b_nearest_aircraft").state == "GRND1"

    # Next poll: the nearest aircraft's callsign is missing from the feed.
    stripped = deepcopy(aircraft_payload)
    for raw in stripped["aircraft"]:
        if raw["hex"] == "dead01":
            raw.pop("flight", None)

    aioclient_mock.clear_requests()
    aioclient_mock.get(FEED_URL, json=stripped)

    coordinator = hass.data[DOMAIN]["coordinator"]
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    # The remembered callsign is still used instead of falling back to the hex.
    assert hass.states.get("sensor.piaware_ads_b_nearest_aircraft").state == "GRND1"


async def test_radius_toggles_off_ignore_radius(
    hass: HomeAssistant, aioclient_mock, aircraft_payload: dict
) -> None:
    aioclient_mock.get(FEED_URL, json=aircraft_payload)
    hass.config.latitude = 43.0
    hass.config.longitude = -76.0

    data = {
        **ENTRY_DATA,
        CONF_NOTIFICATION_RADIUS_MILES: 0.5,
        CONF_COUNT_USE_RADIUS: False,
        CONF_NEAREST_USE_RADIUS: False,
    }
    entry = MockConfigEntry(domain=DOMAIN, data=data)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Toggles off: the tiny radius is ignored and values are always reported.
    assert hass.states.get("sensor.piaware_ads_b_aircraft_in_range").state == "4"
    assert hass.states.get("sensor.piaware_ads_b_nearest_aircraft").state == "GRND1"


async def test_options_flow_updates_radius(
    hass: HomeAssistant, aioclient_mock, aircraft_payload: dict
) -> None:
    aioclient_mock.get(FEED_URL, json=aircraft_payload)
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {**ENTRY_DATA, CONF_NOTIFICATION_RADIUS_MILES: 12.0},
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_NOTIFICATION_RADIUS_MILES] == 12.0


async def test_overhead_event_fires(
    hass: HomeAssistant, aioclient_mock, aircraft_payload: dict
) -> None:
    aioclient_mock.get(FEED_URL, json=aircraft_payload)
    hass.config.latitude = 43.0
    hass.config.longitude = -76.0

    events: list = []
    hass.bus.async_listen(EVENT_AIRCRAFT_OVERHEAD, events.append)

    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data["callsign"] == "GRND1"
    assert events[0].data["enriched"] is False
    # Only the aircraft feed was fetched; no API call without the enrichment toggle.
    assert aioclient_mock.call_count == 1


async def test_overhead_event_enriched_when_enabled(
    hass: HomeAssistant, aioclient_mock, aircraft_payload: dict
) -> None:
    aioclient_mock.get(FEED_URL, json=aircraft_payload)
    aioclient_mock.get(AEROAPI_GRND1, json=AEROAPI_ROUTE)
    hass.config.latitude = 43.0
    hass.config.longitude = -76.0

    events: list = []
    hass.bus.async_listen(EVENT_AIRCRAFT_OVERHEAD, events.append)

    data = {**ENTRY_DATA, CONF_API_KEY: "test-key", CONF_ENRICH_NOTIFICATIONS: True}
    entry = MockConfigEntry(domain=DOMAIN, data=data)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data["origin"] == "ATL"
    assert events[0].data["destination"] == "JFK"
    assert events[0].data["airline"] == "Delta Air Lines"
    assert events[0].data["enriched"] is True
