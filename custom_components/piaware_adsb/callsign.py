"""Callsign retention for the PiAware ADS-B integration.

The tar1090/dump1090 feed reports the ``flight`` (callsign) field intermittently
for the same ICAO address: a snapshot can be missing it even though the aircraft
does broadcast an ident. The tar1090 web map hides this by keeping the last
callsign it saw; this cache does the same so entities do not flip to the raw hex.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .aircraft import Aircraft

_PRUNE_THRESHOLD = 1024


class CallsignCache:
    """Remembers the most recent callsign seen for each ICAO address."""

    def __init__(self, ttl: timedelta) -> None:
        self._ttl = ttl
        self._cache: dict[str, tuple[str, datetime]] = {}

    def apply(self, aircraft: list[Aircraft], now: datetime) -> None:
        """Fill in missing callsigns from previously seen ident values."""
        for item in aircraft:
            if item.callsign:
                self._cache[item.hex] = (item.callsign, now)
                continue
            entry = self._cache.get(item.hex)
            if entry is None:
                continue
            callsign, seen = entry
            if now - seen <= self._ttl:
                item.callsign = callsign
            else:
                del self._cache[item.hex]
        self._prune(now)

    def _prune(self, now: datetime) -> None:
        if len(self._cache) <= _PRUNE_THRESHOLD:
            return
        cutoff = now - self._ttl
        stale = [hex_id for hex_id, (_, seen) in self._cache.items() if seen < cutoff]
        for hex_id in stale:
            del self._cache[hex_id]
