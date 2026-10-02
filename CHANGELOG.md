# Changelog

All notable changes to this project are documented here. Versions match
`custom_components/piaware_adsb/manifest.json` and the GitHub release tags.

## [0.9.0] - 2026-10-02

### Added
- Separate **Voice command radius** option, so the overhead notification radius and the voice-command
  radius are now independent. The overhead notification/event and `aircraft_overhead` binary sensor
  use the **Overhead notification radius**; the `count_use_radius`/`nearest_use_radius` toggles and
  the "most recent in-range" voice fallback use the **Voice command radius**.

### Changed
- The radius toggle option labels now reference the voice command radius.

## [0.8.1] - 2026-10-01

### Fixed
- Overhead notifications no longer say "unknown type". The event now takes the aircraft type from
  the receiver's tar1090 database (via the shared `select_type_name`, same as the voice response),
  adding `type_name` to the event and falling back to the DB type code; the blueprint speaks it
  conversationally.

## [0.8.0] - 2026-10-01

### Added
- Aviation phonetic speech: idents and registrations are spoken with the ICAO/NATO alphabet and
  digit words (`N704CT` → "November seven zero four Charlie Tango", `9` → "niner"), for both voice
  responses and overhead notifications.
- New options: **Spell idents and registrations using aviation phonetics** (default on) and
  **Callsign pronunciation** (`airline` name + digits when known, else spell — default — or
  `phonetic` to always spell).
- The overhead event now carries `callsign_spoken`, `registration`, and `registration_spoken`
  (additive); the blueprint speaks the phonetic forms and the registration.

### Note
- Sensor states and the Activity/logbook entries remain raw.

## [0.7.0] - 2026-10-01

### Added
- The overhead notification blueprint now lets you choose which **Assist satellites** announce the
  aircraft (entity selector filtered to `assist_satellite`, one or many), plus an optional
  notification action (use `{{ message }}` for the generated text).
- The blueprint is now bundled with the integration and installed to
  `config/blueprints/automation/piaware_adsb/` at setup (HACS does not install blueprints).

### Changed
- Blueprint action inputs are injected correctly (`sequence: !input`) and the invalid `title` key
  is no longer forced onto voice actions, so `assist_satellite.announce` works.

### Removed
- The repo-root `blueprints/` duplicate; the bundled copy under `custom_components/piaware_adsb/`
  is now the single source of truth.

## [0.6.0] - 2026-10-01

### Added
- The spoken route now uses the AeroAPI airport `city` (falling back to `airport_name`, then the
  IATA/ICAO code), e.g. *"from Atlanta to Tokyo Haneda"*. The overhead event also carries
  `origin_name`/`destination_name`, and the blueprint prefers them.

## [0.5.0] - 2026-10-01

### Added
- Aircraft type from the receiver's own tar1090 database (no external API). The DB entry
  `[registration, type_code, flags, long_name]` supplies a human-readable type name, spoken as
  `a/an <long_name>` (falling back to the ICAO type code). Unknown codes (`00`/empty) are ignored.
- The speech picks the most descriptive available type: local long name, else enrichment/code.

## [0.4.0] - 2026-10-01

### Added
- Registration lookup from the receiver's own tar1090 database (no external API): the voice
  response now includes `registration number <reg>` after the ident, when known and different from
  the callsign/hex. The database folder is discovered from `index.html` and the
  `db-*/<prefix>.js` trie is followed on demand.

## [0.3.3] - 2026-10-01

### Added
- Voice fallback when the nearest-aircraft radius toggle is on and nothing is currently within the
  radius: the assistant reports the most recent aircraft that was in range and how long ago
  (coordinator caches `last_in_range`).

## [0.3.2] - 2026-10-01

### Fixed
- Aircraft names no longer fall back to the raw ICAO hex due to intermittent gaps in the feed's
  `flight` field. A per-hex callsign cache (6 h TTL, `callsign.py`) retains the last callsign seen,
  matching the tar1090 map.

## [0.3.1] - 2026-10-01

### Added
- MIT `LICENSE`; GitHub repository topics (required by HACS validation).

### Changed
- Radius-limited entities (`Aircraft in range`, `Nearest aircraft`, and its distance/altitude)
  become **unavailable** instead of reporting `0`/`unknown` when the toggle is on and nothing is in
  range.
- Home Assistant 2026 compatibility: `config_entry` is passed to `DataUpdateCoordinator`
  (with a fallback for versions that don't accept it).
- CI runs on Python 3.14 against HA 2026.9.2 (`pytest-homeassistant-custom-component==0.13.365`).
- `manifest.json` keys ordered per hassfest; pytest `pythonpath` added.

## [0.3.0] - 2026-10-01

### Added
- Independent toggles `count_use_radius` and `nearest_use_radius` (default off) that reuse the
  notification radius for the aircraft-count sensor and the nearest-aircraft selection/intent.

## [0.2.0] - 2026-10-01

### Added
- Option `enrich_notifications` (default off) to enrich overhead events with FlightAware route,
  airline and type; event gains `origin`, `destination`, `airline`, `enriched`.
- Overhead blueprint shows the route when available.
- New Assist sentences: "what's the nearest plane" and variants.

## [0.1.0] - 2026-10-01

### Added
- Initial release: tar1090/dump1090 polling (`DataUpdateCoordinator`), nearest-aircraft sensors,
  optional overhead binary sensor + blueprint, and the "what plane is that" Assist intent with
  FlightAware AeroAPI (optional key) + hexdb type enrichment.
- Config flow, options flow, HACS packaging, tests, and CI (Tests/Hassfest/HACS).
