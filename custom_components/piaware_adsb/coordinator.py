"""DataUpdateCoordinator for the PiAware ADS-B integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING

from aiohttp import ClientError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .aircraft import Aircraft, nearest_aircraft, parse_aircraft_payload
from .const import (
    DOMAIN,
    EVENT_AIRCRAFT_OVERHEAD,
    SIGNAL_AIRCRAFT_OVERHEAD,
)

if TYPE_CHECKING:
    from .enrichment import EnrichmentClient

_LOGGER = logging.getLogger(__name__)


def build_url(host: str, port: int, path: str) -> str:
    """Build the aircraft.json URL from its parts."""
    if not path.startswith("/"):
        path = f"/{path}"
    return f"http://{host}:{port}{path}"


@dataclass(slots=True)
class PiAwareData:
    """Parsed snapshot of the ADS-B feed."""

    aircraft: list[Aircraft] = field(default_factory=list)
    nearest: Aircraft | None = None
    in_range: Aircraft | None = None
    count: int = 0
    in_range_count: int = 0

    @property
    def overhead(self) -> bool:
        return self.in_range is not None


class PiAwareCoordinator(DataUpdateCoordinator[PiAwareData]):
    """Polls the tar1090 aircraft.json feed and exposes a parsed snapshot."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        host: str,
        port: int,
        path: str,
        scan_interval: int,
        notifications_enabled: bool,
        notification_radius_miles: float,
        enrich_notifications: bool = False,
        count_use_radius: bool = False,
        nearest_use_radius: bool = False,
        enrichment: EnrichmentClient | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self._url = build_url(host, port, path)
        self.notifications_enabled = notifications_enabled
        self.notification_radius_miles = notification_radius_miles
        self.enrich_notifications = enrich_notifications
        self.count_use_radius = count_use_radius
        self.nearest_use_radius = nearest_use_radius
        self._enrichment = enrichment
        self._was_overhead = False

    @property
    def url(self) -> str:
        """The configured aircraft.json URL."""
        return self._url

    async def _async_update_data(self) -> PiAwareData:
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(self._url, timeout=10) as resp:
                resp.raise_for_status()
                payload = await resp.json(content_type=None)
        except (ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"Error fetching {self._url}: {err}") from err

        aircraft = parse_aircraft_payload(
            payload, self.hass.config.latitude, self.hass.config.longitude
        )
        in_range = nearest_aircraft(aircraft, within_miles=self.notification_radius_miles)
        positioned_count = sum(1 for a in aircraft if a.has_position)
        in_range_count = sum(
            1
            for a in aircraft
            if a.distance_miles is not None
            and a.distance_miles <= self.notification_radius_miles
        )

        nearest = (
            in_range if self.nearest_use_radius else nearest_aircraft(aircraft)
        )
        count = in_range_count if self.count_use_radius else positioned_count

        data = PiAwareData(
            aircraft=aircraft,
            nearest=nearest,
            in_range=in_range,
            count=count,
            in_range_count=in_range_count,
        )

        await self._handle_overhead(data)
        return data

    async def _handle_overhead(self, data: PiAwareData) -> None:
        """Fire the overhead event/signal on a rising edge when enabled."""
        if self.notifications_enabled and data.overhead and not self._was_overhead:
            target = data.in_range
            assert target is not None
            event_data = {
                "hex": target.hex,
                "callsign": target.callsign,
                "type_code": target.type_code,
                "altitude_ft": target.altitude_ft,
                "distance_miles": target.distance_miles,
                "compass": target.compass,
                "squawk": target.squawk,
                "origin": None,
                "destination": None,
                "airline": None,
                "enriched": False,
            }

            if (
                self.enrich_notifications
                and self._enrichment is not None
                and self._enrichment.has_api_key
            ):
                route = await self._enrichment.async_enrich(
                    target.callsign, target.hex
                )
                event_data["origin"] = route.origin
                event_data["destination"] = route.destination
                event_data["airline"] = route.airline
                if route.aircraft_type:
                    event_data["type_code"] = route.aircraft_type
                event_data["enriched"] = route.has_route

            self.hass.bus.async_fire(EVENT_AIRCRAFT_OVERHEAD, event_data)
            async_dispatcher_send(self.hass, SIGNAL_AIRCRAFT_OVERHEAD, target)
        self._was_overhead = data.overhead
