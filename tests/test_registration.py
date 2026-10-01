"""Tests for the local tar1090 registration database lookup."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.piaware_adsb.registration import (
    Tar1090RegistrationLookup,
    registration_root,
)

ROOT = "http://piaware.lan:80/tar1090"
INDEX = f"{ROOT}/index.html"
INDEX_HTML = '<script>let databaseFolder = "db-test";</script>'


def test_registration_root_from_feed_url() -> None:
    url = "http://piaware.lan:80/tar1090/data/aircraft.json"
    assert registration_root(url) == "http://piaware.lan:80/tar1090"


def test_registration_root_without_data_segment() -> None:
    assert registration_root("http://host/dump1090/aircraft.json") == "http://host/dump1090"


async def test_lookup_follows_trie(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(INDEX, text=INDEX_HTML)
    aioclient_mock.get(f"{ROOT}/db-test/A.js", json={"children": ["A9"]})
    aioclient_mock.get(f"{ROOT}/db-test/A9.js", json={"63AE": ["N704CT", "00"]})

    lookup = Tar1090RegistrationLookup(hass, ROOT)

    assert await lookup.async_get_registration("a963ae") == "N704CT"


async def test_lookup_direct_hit(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(INDEX, text=INDEX_HTML)
    aioclient_mock.get(f"{ROOT}/db-test/A.js", json={"E0000": ["63-8146", "T38"]})

    lookup = Tar1090RegistrationLookup(hass, ROOT)

    assert await lookup.async_get_registration("ae0000") == "63-8146"


async def test_lookup_unknown_returns_none(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(INDEX, text=INDEX_HTML)
    aioclient_mock.get(f"{ROOT}/db-test/A.js", json={"children": ["A9"]})
    aioclient_mock.get(f"{ROOT}/db-test/A9.js", json={})

    lookup = Tar1090RegistrationLookup(hass, ROOT)

    assert await lookup.async_get_registration("a9ffff") is None


async def test_lookup_skips_non_icao(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(INDEX, text=INDEX_HTML)

    lookup = Tar1090RegistrationLookup(hass, ROOT)

    assert await lookup.async_get_registration("~0ea58e") is None


async def test_lookup_handles_missing_index(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(INDEX, status=500)

    lookup = Tar1090RegistrationLookup(hass, ROOT)

    assert await lookup.async_get_registration("a963ae") is None
