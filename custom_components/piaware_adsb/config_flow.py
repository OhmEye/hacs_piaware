"""Config flow for the PiAware ADS-B integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from aiohttp import ClientError
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.core import HomeAssistant, callback

try:  # ConfigFlowResult was added in Home Assistant 2024.4
    from homeassistant.config_entries import ConfigFlowResult
except ImportError:  # pragma: no cover - older Home Assistant
    from homeassistant.data_entry_flow import FlowResult as ConfigFlowResult

from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_INSTALL_SENTENCES,
    CONF_NOTIFICATION_RADIUS_MILES,
    CONF_NOTIFICATIONS_ENABLED,
    CONF_PATH,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_HOST,
    DEFAULT_INSTALL_SENTENCES,
    DEFAULT_NOTIFICATION_RADIUS_MILES,
    DEFAULT_NOTIFICATIONS_ENABLED,
    DEFAULT_PATH,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .coordinator import build_url

_LOGGER = logging.getLogger(__name__)


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    """Build the config/options schema populated with current defaults."""
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, DEFAULT_HOST)): str,
            vol.Required(
                CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            vol.Required(CONF_PATH, default=defaults.get(CONF_PATH, DEFAULT_PATH)): str,
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)),
            vol.Optional(
                CONF_API_KEY, default=defaults.get(CONF_API_KEY, "")
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Required(
                CONF_NOTIFICATIONS_ENABLED,
                default=defaults.get(
                    CONF_NOTIFICATIONS_ENABLED, DEFAULT_NOTIFICATIONS_ENABLED
                ),
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_NOTIFICATION_RADIUS_MILES,
                default=defaults.get(
                    CONF_NOTIFICATION_RADIUS_MILES, DEFAULT_NOTIFICATION_RADIUS_MILES
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.1,
                    max=100,
                    step=0.1,
                    unit_of_measurement="mi",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_INSTALL_SENTENCES,
                default=defaults.get(CONF_INSTALL_SENTENCES, DEFAULT_INSTALL_SENTENCES),
            ): selector.BooleanSelector(),
        }
    )


async def _async_validate(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Fetch the feed once to confirm connectivity and payload shape."""
    session = async_get_clientsession(hass)
    url = build_url(data[CONF_HOST], data[CONF_PORT], data[CONF_PATH])
    async with session.get(url, timeout=10) as resp:
        resp.raise_for_status()
        payload = await resp.json(content_type=None)
    if not isinstance(payload, dict) or "aircraft" not in payload:
        raise ValueError("Endpoint did not return a tar1090/dump1090 aircraft feed")


class PiAwareADSBConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial configuration of the integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await _async_validate(self.hass, user_input)
            except (ClientError, TimeoutError, OSError) as err:
                _LOGGER.debug("Connection error validating feed: %s", err)
                errors["base"] = "cannot_connect"
            except ValueError as err:
                _LOGGER.debug("Invalid feed payload: %s", err)
                errors["base"] = "invalid_feed"
            else:
                return self.async_create_entry(
                    title=f"PiAware ADS-B ({user_input[CONF_HOST]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user", data_schema=_schema(user_input or {}), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return PiAwareADSBOptionsFlow(config_entry)


class PiAwareADSBOptionsFlow(OptionsFlow):
    """Allow tuning the feed, notifications and API key after setup."""

    def __init__(self, config_entry) -> None:
        # Home Assistant injects ``config_entry`` on newer versions; keep a private
        # reference so this also works on versions where it is not injected.
        self._entry = config_entry

    def _current_config(self) -> dict[str, Any]:
        entry = getattr(self, "config_entry", None) or self._entry
        return {**entry.data, **entry.options}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await _async_validate(self.hass, user_input)
            except (ClientError, TimeoutError, OSError) as err:
                _LOGGER.debug("Connection error validating feed: %s", err)
                errors["base"] = "cannot_connect"
            except ValueError as err:
                _LOGGER.debug("Invalid feed payload: %s", err)
                errors["base"] = "invalid_feed"
            else:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init", data_schema=_schema(self._current_config()), errors=errors
        )
