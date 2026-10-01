"""Assist intent handling for the PiAware ADS-B integration."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent as intent_helper
from homeassistant.util import dt as dt_util

from .aircraft import Aircraft
from .const import DOMAIN, INTENT_WHAT_PLANE
from .enrichment import EnrichmentClient, RouteInfo
from .registration import AircraftMeta

_LOGGER = logging.getLogger(__name__)

_NO_TRAFFIC_SPEECH = "I don't see any aircraft nearby right now."


def _get_coordinator(hass: HomeAssistant):
    store = hass.data.get(DOMAIN, {})
    if isinstance(store, dict):
        return store.get("coordinator")
    return None


def _get_enrichment(hass: HomeAssistant) -> EnrichmentClient | None:
    store = hass.data.get(DOMAIN, {})
    if isinstance(store, dict):
        return store.get("enrichment")
    return None


def _get_tar1090_db(hass: HomeAssistant):
    store = hass.data.get(DOMAIN, {})
    if isinstance(store, dict):
        return store.get("tar1090_db")
    return None


def _recent_in_range(coordinator) -> tuple[Aircraft, datetime] | None:
    """Return the cached last in-radius aircraft when the radius is applied."""
    if coordinator is None or not getattr(coordinator, "nearest_use_radius", False):
        return None
    recent = getattr(coordinator, "last_in_range", None)
    if recent is None or getattr(coordinator, "notification_radius_miles", None) is None:
        return None
    return recent


def _select_type_name(
    route: RouteInfo | None,
    meta: AircraftMeta | None,
    aircraft: Aircraft,
) -> str | None:
    """Pick the friendliest available aircraft type description."""
    candidates = [
        route.aircraft_type if route else None,
        meta.type_name if meta else None,
        meta.type_code if meta else None,
        aircraft.type_code,
    ]
    present = [c for c in candidates if c]
    for candidate in present:
        # Prefer a descriptive name (e.g. "Boeing 737-800") over a bare ICAO code.
        if " " in candidate or any(ch.islower() for ch in candidate):
            return candidate
    return present[0] if present else None


def _describe(
    aircraft: Aircraft,
    route: RouteInfo | None,
    meta: AircraftMeta | None = None,
) -> list[str]:
    """Build the descriptor phrases for an aircraft."""
    parts: list[str] = [aircraft.display_name]

    registration = meta.registration if meta else None
    if registration and registration.upper() not in (
        (aircraft.callsign or "").upper(),
        aircraft.hex.upper(),
    ):
        parts.append(f"registration number {registration}")

    type_name = _select_type_name(route, meta, aircraft)
    if type_name:
        article = "an" if type_name[:1].upper() in "AEIOU" else "a"
        parts.append(f"{article} {type_name}")

    if aircraft.distance_miles is not None:
        distance = round(aircraft.distance_miles)
        direction = f" to the {aircraft.compass}" if aircraft.compass else ""
        parts.append(f"{distance} miles{direction}")

    if route and route.has_route:
        airline = f" ({route.airline})" if route.airline else ""
        parts.append(f"from {route.origin} to {route.destination}{airline}")
    elif aircraft.altitude_ft is not None:
        parts.append(f"at {aircraft.altitude_ft:,} feet")

    return parts


def build_speech(
    aircraft: Aircraft,
    route: RouteInfo | None,
    meta: AircraftMeta | None = None,
) -> str:
    """Compose the spoken answer for the nearest aircraft."""
    return ", ".join(_describe(aircraft, route, meta)) + "."


def _humanize_age(seconds: float) -> str:
    """Describe an elapsed time in whole-word form."""
    total = int(max(0, seconds))
    if total < 5:
        return "just now"
    if total < 60:
        return f"{total} seconds ago"
    minutes = total // 60
    if minutes < 60:
        return "1 minute ago" if minutes == 1 else f"{minutes} minutes ago"
    hours = minutes // 60
    if hours < 24:
        return "1 hour ago" if hours == 1 else f"{hours} hours ago"
    days = hours // 24
    return "1 day ago" if days == 1 else f"{days} days ago"


def build_recent_speech(
    aircraft: Aircraft,
    route: RouteInfo | None,
    radius_miles: float,
    seconds: float,
    meta: AircraftMeta | None = None,
) -> str:
    """Compose the answer when nothing is in range but one recently was."""
    recent = ", ".join(_describe(aircraft, route, meta))
    return (
        f"No aircraft within {radius_miles:g} miles. "
        f"The most recent was {recent}, {_humanize_age(seconds)}."
    )


class WhatPlaneIntent(intent_helper.IntentHandler):
    """Answer "what plane is that" with the nearest aircraft."""

    intent_type = INTENT_WHAT_PLANE

    async def async_handle(
        self, intent_obj: intent_helper.Intent
    ) -> intent_helper.IntentResponse:
        hass = intent_obj.hass
        response = intent_helper.IntentResponse(language=intent_obj.language)

        coordinator = _get_coordinator(hass)
        snapshot = getattr(coordinator, "data", None)
        target: Aircraft | None = snapshot.nearest if snapshot else None
        enrichment = _get_enrichment(hass)
        tar1090_db = _get_tar1090_db(hass)

        async def _enrich(aircraft: Aircraft) -> RouteInfo | None:
            if enrichment is None:
                return None
            try:
                return await enrichment.async_enrich(aircraft.callsign, aircraft.hex)
            except Exception:  # noqa: BLE001 - never fail the voice query
                _LOGGER.exception("Enrichment failed for %s", aircraft.hex)
                return None

        async def _metadata_for(aircraft: Aircraft) -> AircraftMeta | None:
            if tar1090_db is None:
                return None
            try:
                return await tar1090_db.async_get_metadata(aircraft.hex)
            except Exception:  # noqa: BLE001 - never fail the voice query
                _LOGGER.debug("tar1090 metadata lookup failed for %s", aircraft.hex)
                return None

        if target is None:
            recent = _recent_in_range(coordinator)
            if recent is not None:
                aircraft, when = recent
                route = await _enrich(aircraft)
                meta = await _metadata_for(aircraft)
                age = (dt_util.utcnow() - when).total_seconds()
                response.async_set_speech(
                    build_recent_speech(
                        aircraft,
                        route,
                        coordinator.notification_radius_miles,
                        age,
                        meta,
                    )
                )
                return response
            response.async_set_speech(_NO_TRAFFIC_SPEECH)
            return response

        route = await _enrich(target)
        meta = await _metadata_for(target)
        response.async_set_speech(build_speech(target, route, meta))
        return response


async def async_setup_intents(hass: HomeAssistant) -> None:
    """Register the integration's intents exactly once."""
    store = hass.data.setdefault(DOMAIN, {})
    if store.get("intents_registered"):
        return
    intent_helper.async_register(hass, WhatPlaneIntent())
    store["intents_registered"] = True
