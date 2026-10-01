"""Tests for the config flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.piaware_adsb.const import CONF_HOST, DOMAIN

FEED_URL = "http://piaware.lan:80/tar1090/data/aircraft.json"

USER_INPUT = {
    "host": "piaware.lan",
    "port": 80,
    "path": "/tar1090/data/aircraft.json",
    "scan_interval": 10,
    "api_key": "",
    "notifications_enabled": False,
    "notification_radius_miles": 5.0,
    "enrich_notifications": False,
    "count_use_radius": False,
    "nearest_use_radius": False,
    "phonetic_speech": True,
    "callsign_style": "airline",
    "install_sentences": False,
}


async def test_user_flow_creates_entry(
    hass: HomeAssistant, aioclient_mock, aircraft_payload: dict
) -> None:
    aioclient_mock.get(FEED_URL, json=aircraft_payload)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HOST] == "piaware.lan"


async def test_user_flow_cannot_connect(
    hass: HomeAssistant, aioclient_mock
) -> None:
    aioclient_mock.get(FEED_URL, status=500)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "cannot_connect"


async def test_user_flow_invalid_feed(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(FEED_URL, json={"unexpected": True})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_feed"
