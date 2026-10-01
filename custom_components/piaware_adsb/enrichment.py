"""Flight route and aircraft type enrichment via FlightAware AeroAPI."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from aiohttp import ClientError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import (
    AEROAPI_BASE,
    AEROAPI_TIMEOUT,
    ENRICHMENT_CACHE_TTL,
    HEXDB_URL,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class RouteInfo:
    """Enriched information about a flight."""

    ident: str | None = None
    origin: str | None = None
    destination: str | None = None
    airline: str | None = None
    aircraft_type: str | None = None

    @property
    def has_route(self) -> bool:
        return bool(self.origin and self.destination)


class EnrichmentClient:
    """Caches route/type lookups to bound API usage and cost."""

    def __init__(self, hass: HomeAssistant, api_key: str | None) -> None:
        self._hass = hass
        self._api_key = api_key or None
        self._cache: dict[str, tuple[datetime, RouteInfo]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _cache_get(self, key: str) -> RouteInfo | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        expires, value = entry
        if dt_util.utcnow() >= expires:
            del self._cache[key]
            return None
        return value

    def _cache_set(self, key: str, value: RouteInfo) -> None:
        self._cache[key] = (dt_util.utcnow() + ENRICHMENT_CACHE_TTL, value)

    async def async_enrich(self, ident: str | None, icao24: str) -> RouteInfo:
        """Return enriched data for a flight, using cache and de-duplication."""
        cache_key = (ident or icao24).upper()
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        lock = self._locks.setdefault(cache_key, asyncio.Lock())
        async with lock:
            cached = self._cache_get(cache_key)
            if cached is not None:
                return cached

            info = RouteInfo(ident=ident)
            if self._api_key and ident:
                info = await self._lookup_aeroapi(ident) or info

            if not info.aircraft_type:
                type_name = await self._lookup_hexdb_type(icao24)
                if type_name:
                    info = RouteInfo(
                        ident=info.ident,
                        origin=info.origin,
                        destination=info.destination,
                        airline=info.airline,
                        aircraft_type=type_name,
                    )

            self._cache_set(cache_key, info)
            return info

    async def _lookup_aeroapi(self, ident: str) -> RouteInfo | None:
        session = async_get_clientsession(self._hass)
        url = f"{AEROAPI_BASE}/flights/{ident}"
        headers = {"x-apikey": self._api_key or ""}
        try:
            async with session.get(
                url, headers=headers, timeout=AEROAPI_TIMEOUT
            ) as resp:
                if resp.status in (400, 401, 403, 404):
                    _LOGGER.debug("AeroAPI returned %s for %s", resp.status, ident)
                    return None
                resp.raise_for_status()
                payload: dict[str, Any] = await resp.json(content_type=None)
        except (ClientError, TimeoutError, ValueError) as err:
            _LOGGER.debug("AeroAPI lookup failed for %s: %s", ident, err)
            return None

        flights = payload.get("flights") or []
        if not flights:
            return None
        flight = _select_flight(flights)
        if flight is None:
            return None

        origin = _airport_code(flight.get("origin"))
        destination = _airport_code(flight.get("destination"))
        return RouteInfo(
            ident=flight.get("ident") or ident,
            origin=origin,
            destination=destination,
            airline=_airline_name(flight),
            aircraft_type=flight.get("aircraft_type"),
        )

    async def _lookup_hexdb_type(self, icao24: str) -> str | None:
        if not icao24:
            return None
        session = async_get_clientsession(self._hass)
        url = f"{HEXDB_URL}/{icao24.lower()}"
        try:
            async with session.get(url, timeout=AEROAPI_TIMEOUT) as resp:
                if resp.status != 200:
                    return None
                payload: dict[str, Any] = await resp.json(content_type=None)
        except (ClientError, TimeoutError, ValueError) as err:
            _LOGGER.debug("hexdb lookup failed for %s: %s", icao24, err)
            return None
        return payload.get("Type") or payload.get("ICAOTypeCode") or None


def _select_flight(flights: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Choose the most relevant flight, preferring one with a route."""
    with_route = [
        f
        for f in flights
        if _airport_code(f.get("origin")) and _airport_code(f.get("destination"))
    ]
    candidates = with_route or flights
    for status in ("En Route", "Scheduled", "Arrived"):
        for flight in candidates:
            if flight.get("status") == status:
                return flight
    return candidates[0] if candidates else None


def _airport_code(airport: Any) -> str | None:
    if not isinstance(airport, dict):
        return None
    return airport.get("code_iata") or airport.get("code") or airport.get("code_icao")


def _airline_name(flight: dict[str, Any]) -> str | None:
    return (
        flight.get("operator")
        or flight.get("operator_iata")
        or flight.get("operator_icao")
    )
