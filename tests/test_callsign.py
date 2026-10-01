"""Tests for callsign retention."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.piaware_adsb.aircraft import Aircraft
from custom_components.piaware_adsb.callsign import CallsignCache

TTL = timedelta(hours=6)


def test_callsign_is_remembered_when_feed_omits_it() -> None:
    cache = CallsignCache(TTL)
    t0 = datetime(2026, 1, 1, tzinfo=UTC)

    cache.apply([Aircraft(hex="abc123", callsign="DAL100")], t0)

    later = Aircraft(hex="abc123")
    cache.apply([later], t0 + timedelta(minutes=5))
    assert later.callsign == "DAL100"


def test_cache_respects_ttl() -> None:
    cache = CallsignCache(TTL)
    t0 = datetime(2026, 1, 1, tzinfo=UTC)

    cache.apply([Aircraft(hex="abc123", callsign="DAL100")], t0)

    stale = Aircraft(hex="abc123")
    cache.apply([stale], t0 + TTL + timedelta(minutes=1))
    assert stale.callsign is None


def test_unknown_aircraft_stays_without_callsign() -> None:
    cache = CallsignCache(TTL)
    t0 = datetime(2026, 1, 1, tzinfo=UTC)

    unknown = Aircraft(hex="dead01")
    cache.apply([unknown], t0)
    assert unknown.callsign is None


def test_updated_callsign_replaces_previous() -> None:
    cache = CallsignCache(TTL)
    t0 = datetime(2026, 1, 1, tzinfo=UTC)

    cache.apply([Aircraft(hex="abc123", callsign="DAL100")], t0)
    cache.apply([Aircraft(hex="abc123", callsign="DAL200")], t0)

    followup = Aircraft(hex="abc123")
    cache.apply([followup], t0)
    assert followup.callsign == "DAL200"
