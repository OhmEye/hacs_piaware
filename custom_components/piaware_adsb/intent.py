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


def _recent_in_range(coordinator) -> tuple[Aircraft, datetime] | None:
    """Return the cached last in-radius aircraft when the radius is applied."""
    if coordinator is None or not getattr(coordinator, "nearest_use_radius", False):
        return None
    recent = getattr(coordinator, "last_in_range", None)
    if recent is None or getattr(coordinator, "notification_radius_miles", None) is None:
        return None
    return recent


def _describe(aircraft: Aircraft, route: RouteInfo | None) -> list[str]:
    """Build the descriptor phrases for an aircraft."""
    parts: list[str] = [aircraft.display_name]

    type_name = (route.aircraft_type if route else None) or aircraft.type_code
    if type_name:
        parts.append(f"a {type_name}")

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


def build_speech(aircraft: Aircraft, route: RouteInfo | None) -> str:
    """Compose the spoken answer for the nearest aircraft."""
    return ", ".join(_describe(aircraft, route)) + "."


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
) -> str:
    """Compose the answer when nothing is in range but one recently was."""
    recent = ", ".join(_describe(aircraft, route))
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

        async def _enrich(aircraft: Aircraft) -> RouteInfo | None:
            if enrichment is None:
                return None
            try:
                return await enrichment.async_enrich(aircraft.callsign, aircraft.hex)
            except Exception:  # noqa: BLE001 - never fail the voice query
                _LOGGER.exception("Enrichment failed for %s", aircraft.hex)
                return None

        if target is None:
            recent = _recent_in_range(coordinator)
            if recent is not None:
                aircraft, when = recent
                route = await _enrich(aircraft)
                age = (dt_util.utcnow() - when).total_seconds()
                response.async_set_speech(
                    build_recent_speech(
                        aircraft,
                        route,
                        coordinator.notification_radius_miles,
                        age,
                    )
                )
                return response
            response.async_set_speech(_NO_TRAFFIC_SPEECH)
            return response

        response.async_set_speech(build_speech(target, await _enrich(target)))
        return response


async def async_setup_intents(hass: HomeAssistant) -> None:
    """Register the integration's intents exactly once."""
    store = hass.data.setdefault(DOMAIN, {})
    if store.get("intents_registered"):
        return
    intent_helper.async_register(hass, WhatPlaneIntent())
    store["intents_registered"] = True
