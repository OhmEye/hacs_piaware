"""Set up the PiAware ADS-B integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_API_KEY,
    CONF_COUNT_USE_RADIUS,
    CONF_ENRICH_NOTIFICATIONS,
    CONF_HOST,
    CONF_INSTALL_SENTENCES,
    CONF_NEAREST_USE_RADIUS,
    CONF_NOTIFICATION_RADIUS_MILES,
    CONF_NOTIFICATIONS_ENABLED,
    CONF_PATH,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CUSTOM_SENTENCE_FILE,
    DEFAULT_COUNT_USE_RADIUS,
    DEFAULT_ENRICH_NOTIFICATIONS,
    DEFAULT_INSTALL_SENTENCES,
    DEFAULT_NEAREST_USE_RADIUS,
    DEFAULT_NOTIFICATION_RADIUS_MILES,
    DEFAULT_NOTIFICATIONS_ENABLED,
    DEFAULT_PATH,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import PiAwareCoordinator
from .enrichment import EnrichmentClient
from .intent import async_setup_intents
from .registration import Tar1090RegistrationLookup, registration_root

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PiAware ADS-B from a config entry."""
    config = {**entry.data, **entry.options}

    enrichment = EnrichmentClient(hass, config.get(CONF_API_KEY))

    coordinator = PiAwareCoordinator(
        hass,
        config_entry=entry,
        host=config[CONF_HOST],
        port=config.get(CONF_PORT, DEFAULT_PORT),
        path=config.get(CONF_PATH, DEFAULT_PATH),
        scan_interval=config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        notifications_enabled=config.get(
            CONF_NOTIFICATIONS_ENABLED, DEFAULT_NOTIFICATIONS_ENABLED
        ),
        notification_radius_miles=config.get(
            CONF_NOTIFICATION_RADIUS_MILES, DEFAULT_NOTIFICATION_RADIUS_MILES
        ),
        enrich_notifications=config.get(
            CONF_ENRICH_NOTIFICATIONS, DEFAULT_ENRICH_NOTIFICATIONS
        ),
        count_use_radius=config.get(CONF_COUNT_USE_RADIUS, DEFAULT_COUNT_USE_RADIUS),
        nearest_use_radius=config.get(
            CONF_NEAREST_USE_RADIUS, DEFAULT_NEAREST_USE_RADIUS
        ),
        enrichment=enrichment,
    )
    await coordinator.async_config_entry_first_refresh()

    store = hass.data.setdefault(DOMAIN, {})
    store["coordinator"] = coordinator
    store["enrichment"] = enrichment
    store["registration"] = Tar1090RegistrationLookup(
        hass, registration_root(coordinator.url)
    )

    await async_setup_intents(hass)

    if config.get(CONF_INSTALL_SENTENCES, DEFAULT_INSTALL_SENTENCES):
        await _async_install_sentences(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_options))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        store = hass.data.get(DOMAIN, {})
        store.pop("coordinator", None)
        store.pop("enrichment", None)
        store.pop("registration", None)
    return unloaded


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_install_sentences(hass: HomeAssistant) -> None:
    """Copy the bundled custom sentences into the HA config directory."""
    source = (
        Path(__file__).parent
        / "custom_sentences"
        / "en"
        / CUSTOM_SENTENCE_FILE
    )
    target = Path(hass.config.path("custom_sentences", "en", CUSTOM_SENTENCE_FILE))

    def _copy() -> bool:
        try:
            content = source.read_text(encoding="utf-8")
        except OSError as err:
            _LOGGER.warning("Bundled sentences unavailable: %s", err)
            return False
        try:
            if target.exists() and target.read_text(encoding="utf-8") == content:
                return False
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        except OSError as err:
            _LOGGER.warning("Could not install custom sentences: %s", err)
            return False
        return True

    if await hass.async_add_executor_job(_copy):
        _LOGGER.warning(
            "Installed custom Assist sentences to %s. Restart Home Assistant "
            "for the new sentences to take effect.",
            target,
        )
