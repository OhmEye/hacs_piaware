"""End-to-end setup and options-flow tests."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.piaware_adsb.const import (
    CONF_HOST,
    CONF_INSTALL_SENTENCES,
    CONF_NOTIFICATION_RADIUS_MILES,
    CONF_NOTIFICATIONS_ENABLED,
    CONF_PATH,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)

FEED_URL = "http://piaware.lan:80/tar1090/data/aircraft.json"

ENTRY_DATA = {
    CONF_HOST: "piaware.lan",
    CONF_PORT: 80,
    CONF_PATH: "/tar1090/data/aircraft.json",
    CONF_SCAN_INTERVAL: 10,
    CONF_NOTIFICATIONS_ENABLED: True,
    CONF_NOTIFICATION_RADIUS_MILES: 5.0,
    CONF_INSTALL_SENTENCES: False,
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

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


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
    from custom_components.piaware_adsb.const import EVENT_AIRCRAFT_OVERHEAD

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
