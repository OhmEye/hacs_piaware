"""Local aircraft registration lookup from the tar1090 metadata database.

tar1090 serves a client-side metadata database under ``<tar1090>/<databaseFolder>/``
(as referenced in ``index.html``). Each ``<prefix>.js`` file is JSON mapping the
remaining hex characters to ``[registration, type_code, ...]``. This lets the
integration report a registration without any external API call.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

_DATABASE_FOLDER_RE = re.compile(r'databaseFolder\s*=\s*"([^"]+)"')
_MAX_CACHED_FILES = 64
_TIMEOUT = 10


def registration_root(feed_url: str) -> str:
    """Return the tar1090 root URL from the aircraft.json feed URL."""
    marker = "/data/"
    index = feed_url.find(marker)
    if index != -1:
        return feed_url[:index]
    return feed_url.rsplit("/", 1)[0]


class Tar1090RegistrationLookup:
    """Looks up registrations from the receiver's own tar1090 database."""

    def __init__(self, hass: HomeAssistant, root_url: str) -> None:
        self._hass = hass
        self._root = root_url.rstrip("/")
        self._folder: str | None = None
        self._files: dict[str, dict[str, Any] | None] = {}

    async def async_get_registration(self, icao24: str | None) -> str | None:
        """Return the registration for an ICAO 24-bit address, if known."""
        icao = (icao24 or "").upper()
        if not icao or icao.startswith("~"):
            return None
        data = await self._async_lookup(icao, 1)
        if not isinstance(data, list) or not data:
            return None
        registration = data[0]
        return registration if isinstance(registration, str) and registration else None

    async def _async_lookup(self, icao: str, level: int) -> Any:
        if level > len(icao):
            return None
        bkey = icao[:level]
        dkey = icao[level:]
        if not dkey:
            return None

        data = await self._async_file(bkey)
        if data is None:
            return None
        if dkey in data:
            return data[dkey]

        children = data.get("children")
        if isinstance(children, list) and bkey + dkey[0] in children:
            return await self._async_lookup(icao, level + 1)
        return None

    async def _async_file(self, bkey: str) -> dict[str, Any] | None:
        if bkey in self._files:
            return self._files[bkey]

        folder = await self._async_folder()
        if folder is None:
            return None

        session = async_get_clientsession(self._hass)
        url = f"{self._root}/{folder}/{bkey}.js"
        data: dict[str, Any] | None = None
        try:
            async with session.get(url, timeout=_TIMEOUT) as resp:
                if resp.status != 404:
                    resp.raise_for_status()
                    data = await resp.json(content_type=None)
        except Exception as err:  # noqa: BLE001 - optional enrichment, never fatal
            _LOGGER.debug("tar1090 database lookup failed for %s: %s", url, err)
            data = None

        while len(self._files) >= _MAX_CACHED_FILES:
            self._files.pop(next(iter(self._files)), None)
        self._files[bkey] = data
        return data

    async def _async_folder(self) -> str | None:
        if self._folder is not None:
            return self._folder

        session = async_get_clientsession(self._hass)
        try:
            async with session.get(
                f"{self._root}/index.html", timeout=_TIMEOUT
            ) as resp:
                resp.raise_for_status()
                text = await resp.text()
        except Exception as err:  # noqa: BLE001 - optional discovery
            _LOGGER.debug("Could not discover tar1090 database folder: %s", err)
            return None

        match = _DATABASE_FOLDER_RE.search(text)
        if match:
            self._folder = match.group(1)
        return self._folder
