"""Binary sensor platform for the PiAware ADS-B integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import PiAwareCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PiAwareCoordinator = hass.data[DOMAIN]["coordinator"]
    if not coordinator.notifications_enabled:
        return
    async_add_entities([AircraftOverheadBinarySensor(coordinator, entry)])


class AircraftOverheadBinarySensor(
    CoordinatorEntity[PiAwareCoordinator], BinarySensorEntity
):
    """On while an aircraft is within the configured overhead radius."""

    _attr_has_entity_name = True
    _attr_translation_key = "aircraft_overhead"
    _attr_device_class = BinarySensorDeviceClass.MOTION
    _attr_icon = "mdi:airplane"

    def __init__(self, coordinator: PiAwareCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_aircraft_overhead"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "PiAware ADS-B",
        }

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.overhead

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        aircraft = self.coordinator.data.in_range
        if aircraft is None:
            return None
        return {
            "hex": aircraft.hex,
            "callsign": aircraft.callsign,
            "type_code": aircraft.type_code,
            "altitude_ft": aircraft.altitude_ft,
            "distance_miles": aircraft.distance_miles,
            "compass": aircraft.compass,
            "radius_miles": self.coordinator.notification_radius_miles,
            "attribution": ATTRIBUTION,
        }
