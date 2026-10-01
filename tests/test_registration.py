"""Tests for the local tar1090 metadata database lookup."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.piaware_adsb.registration import (
    AircraftMeta,
    Tar1090Database,
    tar1090_root,
)

ROOT = "http://piaware.lan:80/tar1090"
INDEX = f"{ROOT}/index.html"
INDEX_HTML = '<script>let databaseFolder = "db-test";</script>'


def test_root_from_feed_url() -> None:
    url = "http://piaware.lan:80/tar1090/data/aircraft.json"
    assert tar1090_root(url) == "http://piaware.lan:80/tar1090"


def test_root_without_data_segment() -> None:
    assert tar1090_root("http://host/dump1090/aircraft.json") == "http://host/dump1090"


async def test_lookup_follows_trie(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(INDEX, text=INDEX_HTML)
    aioclient_mock.get(f"{ROOT}/db-test/A.js", json={"children": ["A9"]})
    aioclient_mock.get(f"{ROOT}/db-test/A9.js", json={"63AE": ["N704CT", "00"]})

    hud = Tar1090Database(hass, ROOT)
    meta = await hud.async_get_metadata("a963ae")

    assert meta == AircraftMeta(registration="N704CT", type_code=None, type_name=None)


async def test_lookup_returns_type(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(INDEX, text=INDEX_HTML)
    aioclient_mock.get(
        f"{ROOT}/db-test/A.js",
        json={"E0000": ["63-8146", "T38", "10", "NORTHROP T-38 Talon"]},
    )

    hud = Tar1090Database(hass, ROOT)
    meta = await hud.async_get_metadata("ae0000")

    assert meta is not None
    assert meta.registration == "63-8146"
    assert meta.type_code == "T38"
    assert meta.type_name == "NORTHROP T-38 Talon"


async def test_registration_shortcut(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(INDEX, text=INDEX_HTML)
    aioclient_mock.get(f"{ROOT}/db-test/A.js", json={"E0000": ["63-8146", "T38"]})

    hud = Tar1090Database(hass, ROOT)

    assert await hud.async_get_registration("ae0000") == "63-8146"


async def test_lookup_unknown_returns_none(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(INDEX, text=INDEX_HTML)
    aioclient_mock.get(f"{ROOT}/db-test/A.js", json={"children": ["A9"]})
    aioclient_mock.get(f"{ROOT}/db-test/A9.js", json={})

    hud = Tar1090Database(hass, ROOT)

    assert await hud.async_get_metadata("a9ffff") is None


async def test_lookup_skips_non_icao(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(INDEX, text=INDEX_HTML)

    hud = Tar1090Database(hass, ROOT)

    assert await hud.async_get_metadata("~0ea58e") is None


async def test_lookup_handles_missing_index(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(INDEX, status=500)

    hud = Tar1090Database(hass, ROOT)

    assert await hud.async_get_metadata("a963ae") is None
