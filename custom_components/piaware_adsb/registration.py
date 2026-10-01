"""Local aircraft metadata lookup from the tar1090 database.

tar1090 serves a client-side metadata database under ``<tar1090>/<databaseFolder>/``
(as referenced in ``index.html``). Each ``<prefix>.js`` file is JSON mapping the
remaining hex characters to ``[registration, type_code, flags, long_name]``. This
lets the integration report a registration and an aircraft type without any
external API call.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

_DATABASE_FOLDER_RE = re.compile(r'databaseFolder\s*=\s*"([^"]+)"')
_MAX_CACHED_FILES = 64
_MAX_CACHED_META = 1024
_TIMEOUT = 10
_UNKNOWN_TYPE_CODES = {"", "00", "NA", "N/A", "-", "UNKNOWN"}


def tar1090_root(feed_url: str) -> str:
    """Return the tar1090 root URL from the aircraft.json feed URL."""
    marker = "/data/"
    index = feed_url.find(marker)
    if index != -1:
        return feed_url[:index]
    return feed_url.rsplit("/", 1)[0]


@dataclass(slots=True, frozen=True)
class AircraftMeta:
    """Aircraft metadata from the tar1090 database."""

    registration: str | None = None
    type_code: str | None = None
    type_name: str | None = None

    @property
    def is_empty(self) -> bool:
        return not (self.registration or self.type_code or self.type_name)


def _clean(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _parse_meta(data: Any) -> AircraftMeta | None:
    if not isinstance(data, list) or not data:
        return None
    registration = _clean(data[0])
    type_code = _clean(data[1]) if len(data) > 1 else None
    if type_code is not None and type_code.upper() in _UNKNOWN_TYPE_CODES:
        type_code = None
    type_name = _clean(data[3]) if len(data) > 3 else None
    meta = AircraftMeta(registration, type_code, type_name)
    return None if meta.is_empty else meta


class Tar1090Database:
    """Looks up registrations and aircraft types from the receiver's tar1090 DB."""

    def __init__(self, hass: HomeAssistant, root_url: str) -> None:
        self._hass = hass
        self._root = root_url.rstrip("/")
        self._folder: str | None = None
        self._files: dict[str, dict[str, Any] | None] = {}
        self._meta: dict[str, AircraftMeta | None] = {}

    async def async_get_metadata(self, icao24: str | None) -> AircraftMeta | None:
        """Return metadata for an ICAO 24-bit address, if known."""
        icao = (icao24 or "").upper()
        if not icao or icao.startswith("~"):
            return None
        if icao in self._meta:
            return self._meta[icao]

        meta = _parse_meta(await self._async_lookup(icao, 1))
        while len(self._meta) >= _MAX_CACHED_META:
            self._meta.pop(next(iter(self._meta)), None)
        self._meta[icao] = meta
        return meta

    async def async_get_registration(self, icao24: str | None) -> str | None:
        """Return just the registration for an ICAO 24-bit address, if known."""
        meta = await self.async_get_metadata(icao24)
        return meta.registration if meta else None

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
