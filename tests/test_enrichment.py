"""Tests for FlightAware / hexdb enrichment and caching."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.piaware_adsb.enrichment import EnrichmentClient

AEROAPI_URL = "https://aeroapi.flightaware.com/aeroapi/flights/DAL100"

AEROAPI_PAYLOAD = {
    "flights": [
        {
            "ident": "DAL100",
            "status": "En Route",
            "operator": "Delta Air Lines",
            "aircraft_type": "B738",
            "origin": {"code_iata": "ATL", "code": "KATL"},
            "destination": {"code_iata": "JFK", "code": "KJFK"},
        }
    ]
}


async def test_enrich_returns_route(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(AEROAPI_URL, json=AEROAPI_PAYLOAD)
    client = EnrichmentClient(hass, "test-key")

    info = await client.async_enrich("DAL100", "abc123")

    assert info.origin == "ATL"
    assert info.destination == "JFK"
    assert info.airline == "Delta Air Lines"
    assert info.aircraft_type == "B738"
    assert info.has_route is True


async def test_enrich_is_cached(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(AEROAPI_URL, json=AEROAPI_PAYLOAD)
    client = EnrichmentClient(hass, "test-key")

    await client.async_enrich("DAL100", "abc123")
    await client.async_enrich("DAL100", "abc123")

    assert aioclient_mock.call_count == 1


async def test_enrich_falls_back_to_hexdb_for_type(
    hass: HomeAssistant, aioclient_mock
) -> None:
    aioclient_mock.get(AEROAPI_URL, json={"flights": []})
    aioclient_mock.get(
        "https://hexdb.io/api/v1/aircraft/abc123",
        json={"Type": "Boeing 737-800", "ICAOTypeCode": "B738"},
    )
    client = EnrichmentClient(hass, "test-key")

    info = await client.async_enrich("DAL100", "abc123")

    assert info.origin is None
    assert info.aircraft_type == "Boeing 737-800"


async def test_enrich_without_api_key_uses_hexdb(
    hass: HomeAssistant, aioclient_mock
) -> None:
    aioclient_mock.get(
        "https://hexdb.io/api/v1/aircraft/c06363",
        json={"Type": "Cessna 172"},
    )
    client = EnrichmentClient(hass, None)

    info = await client.async_enrich(None, "c06363")

    assert info.aircraft_type == "Cessna 172"
    assert info.has_route is False
