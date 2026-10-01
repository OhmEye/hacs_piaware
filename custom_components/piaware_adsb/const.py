"""Constants for the PiAware ADS-B integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "piaware_adsb"

CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_PATH: Final = "path"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_API_KEY: Final = "api_key"
CONF_NOTIFICATIONS_ENABLED: Final = "notifications_enabled"
CONF_NOTIFICATION_RADIUS_MILES: Final = "notification_radius_miles"
CONF_ENRICH_NOTIFICATIONS: Final = "enrich_notifications"
CONF_COUNT_USE_RADIUS: Final = "count_use_radius"
CONF_NEAREST_USE_RADIUS: Final = "nearest_use_radius"
CONF_INSTALL_SENTENCES: Final = "install_sentences"

DEFAULT_HOST: Final = "piaware.lan"
DEFAULT_PORT: Final = 80
DEFAULT_PATH: Final = "/tar1090/data/aircraft.json"
DEFAULT_SCAN_INTERVAL: Final = 10
DEFAULT_NOTIFICATIONS_ENABLED: Final = False
DEFAULT_NOTIFICATION_RADIUS_MILES: Final = 5.0
DEFAULT_ENRICH_NOTIFICATIONS: Final = False
DEFAULT_COUNT_USE_RADIUS: Final = False
DEFAULT_NEAREST_USE_RADIUS: Final = False
DEFAULT_INSTALL_SENTENCES: Final = True

MIN_SCAN_INTERVAL: Final = 2
MAX_SCAN_INTERVAL: Final = 300

SCAN_INTERVAL: Final = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

# How long a previously seen callsign is reused when the feed omits it.
CALLSIGN_CACHE_TTL: Final = timedelta(hours=6)

# FlightAware AeroAPI
AEROAPI_BASE: Final = "https://aeroapi.flightaware.com/aeroapi"
AEROAPI_TIMEOUT: Final = 10
ENRICHMENT_CACHE_TTL: Final = timedelta(hours=6)
HEXDB_URL: Final = "https://hexdb.io/api/v1/aircraft"

# Assist intent
INTENT_WHAT_PLANE: Final = "PiawareWhatPlane"
CUSTOM_SENTENCE_FILE: Final = "what_plane.yaml"
BLUEPRINT_FILE: Final = "overhead_notify.yaml"

# Events / signals
EVENT_AIRCRAFT_OVERHEAD: Final = f"{DOMAIN}_aircraft_overhead"
SIGNAL_AIRCRAFT_OVERHEAD: Final = f"{DOMAIN}_aircraft_overhead_signal"

ATTRIBUTION: Final = "Data from PiAware / tar1090 and FlightAware AeroAPI"
