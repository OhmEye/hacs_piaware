"""Sensor platform for the PiAware ADS-B integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .aircraft import Aircraft
from .const import ATTRIBUTION, DOMAIN
from .coordinator import PiAwareCoordinator, PiAwareData


def _aircraft_attributes(aircraft: Aircraft | None) -> dict[str, Any]:
    if aircraft is None:
        return {}
    return {
        "hex": aircraft.hex,
        "callsign": aircraft.callsign,
        "type_code": aircraft.type_code,
        "category": aircraft.category,
        "altitude_ft": aircraft.altitude_ft,
        "ground_speed_kt": aircraft.ground_speed_kt,
        "track": aircraft.track,
        "squawk": aircraft.squawk,
        "latitude": aircraft.latitude,
        "longitude": aircraft.longitude,
        "distance_miles": aircraft.distance_miles,
        "bearing": aircraft.bearing,
        "compass": aircraft.compass,
        "attribution": ATTRIBUTION,
    }


@dataclass(frozen=True, kw_only=True)
class PiAwareSensorEntityDescription(SensorEntityDescription):
    """Describes a PiAware sensor."""

    value_fn: Callable[[PiAwareData], Any]
    attr_fn: Callable[[PiAwareData], dict[str, Any]] | None = None


SENSORS: tuple[PiAwareSensorEntityDescription, ...] = (
    PiAwareSensorEntityDescription(
        key="nearest_aircraft",
        translation_key="nearest_aircraft",
        icon="mdi:airplane",
        value_fn=lambda data: data.nearest.display_name if data.nearest else None,
        attr_fn=lambda data: _aircraft_attributes(data.nearest),
    ),
    PiAwareSensorEntityDescription(
        key="nearest_distance",
        translation_key="nearest_distance",
        icon="mdi:map-marker-distance",
        native_unit_of_measurement="mi",
        value_fn=lambda data: (
            round(data.nearest.distance_miles, 2)
            if data.nearest and data.nearest.distance_miles is not None
            else None
        ),
    ),
    PiAwareSensorEntityDescription(
        key="nearest_altitude",
        translation_key="nearest_altitude",
        icon="mdi:altimeter",
        native_unit_of_measurement="ft",
        value_fn=lambda data: data.nearest.altitude_ft if data.nearest else None,
    ),
    PiAwareSensorEntityDescription(
        key="aircraft_count",
        translation_key="aircraft_count",
        icon="mdi:airplane-marker",
        value_fn=lambda data: data.count,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PiAwareCoordinator = hass.data[DOMAIN]["coordinator"]
    async_add_entities(
        PiAwareSensor(coordinator, entry, description) for description in SENSORS
    )


class PiAwareSensor(CoordinatorEntity[PiAwareCoordinator], SensorEntity):
    """A sensor backed by the coordinator snapshot."""

    entity_description: PiAwareSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PiAwareCoordinator,
        entry: ConfigEntry,
        description: PiAwareSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "PiAware ADS-B",
        }

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attr_fn is None:
            return None
        return self.entity_description.attr_fn(self.coordinator.data)
