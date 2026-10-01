"""Assist intent handling for the PiAware ADS-B integration."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent as intent_helper

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


def build_speech(aircraft: Aircraft, route: RouteInfo | None) -> str:
    """Compose the spoken answer for the nearest aircraft."""
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

    return ", ".join(parts) + "."


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

        if target is None:
            response.async_set_speech(_NO_TRAFFIC_SPEECH)
            return response

        route: RouteInfo | None = None
        enrichment = _get_enrichment(hass)
        if enrichment is not None:
            try:
                route = await enrichment.async_enrich(target.callsign, target.hex)
            except Exception:  # noqa: BLE001 - never fail the voice query
                _LOGGER.exception("Enrichment failed for %s", target.hex)

        response.async_set_speech(build_speech(target, route))
        return response


async def async_setup_intents(hass: HomeAssistant) -> None:
    """Register the integration's intents exactly once."""
    store = hass.data.setdefault(DOMAIN, {})
    if store.get("intents_registered"):
        return
    intent_helper.async_register(hass, WhatPlaneIntent())
    store["intents_registered"] = True
