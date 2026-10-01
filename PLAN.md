# Project Plan & Development Log — `piaware_adsb`

**Status:** Implemented and released. Latest release **v0.3.3** on
<https://github.com/OhmEye/hacs_piaware>. All CI (Tests, Hassfest, HACS) green.

## Goal

Answer the Home Assistant Assist voice query **"what plane is that"** with the nearest aircraft
overhead — flight number, aircraft type, distance, origin and destination — from a local
PiAware/tar1090 feed. Also expose dashboard sensors, optional overhead notifications, and ship as a
HACS-installable custom integration with tests.

## Confirmed decisions

| Item | Decision |
|---|---|
| Voice front-end | HA Assist, default conversation agent |
| Selection | Nearest aircraft by great-circle distance from HA home coordinates |
| Data source | `http://piaware.lan/tar1090/data/aircraft.json` (receiver at 42.07002, -77.05097) |
| Spoken detail | flight no./callsign, type, distance, origin, destination |
| Units | Miles, altitude in feet, bearing as compass direction |
| Enrichment | FlightAware AeroAPI `/flights/{ident}` with `x-apikey`; hexdb.io fallback for type; 6 h TTL cache; invoked on voice query (and optionally for overhead events) |
| Reference location | HA `hass.config.latitude/longitude` (Settings → Home Information) |
| Overhead notifications | Config option, configurable radius, **disabled by default** |
| Notification API enrichment | Separate option `enrich_notifications`, **disabled by default** |
| Radius toggles | `count_use_radius` and `nearest_use_radius`, both **default off**, reuse the notification radius |
| Packaging | Custom integration + HACS custom repository |
| Extras | Dashboard sensors, tests, CI, config flow, blueprint |

## Architecture (as built)

```
tar1090 aircraft.json ──(aiohttp poll / DataUpdateCoordinator)──▶ [PiAwareCoordinator]
   ├─ aircraft.parse_aircraft_payload()  → Geo distance/bearing (geo.py) vs. HA home coords
   ├─ CallsignCache.apply()              → reuse last callsign per ICAO hex (6 h TTL)
   ├─ nearest_aircraft() / in-radius     → optional radius filter per toggle
   ├─ remembers last_in_range (aircraft, timestamp)
   ├─ sensors: nearest aircraft / distance / altitude / aircraft count
   ├─ binary_sensor.aircraft_overhead    (only when notifications enabled)
   ├─ event piaware_adsb_aircraft_overhead (rising edge, optional API enrich)
   └─ Assist intent "what plane is that"
        └─ EnrichmentClient → AeroAPI (cached, de-duped) + hexdb type fallback
             └─ speech: nearest, or "most recent in-range + how long ago"
```

### Coordinates / entities

- Home reference = `hass.config.latitude/longitude`; receiver also exposes coords via
  `tar1090/data/receiver.json`.
- Entities (device "PiAware ADS-B" → slug `piaware_ads_b`):
  `sensor.piaware_ads_b_nearest_aircraft`, `..._nearest_aircraft_distance`,
  `..._nearest_aircraft_altitude`, `..._aircraft_in_range`,
  `binary_sensor.piaware_ads_b_aircraft_overhead`.

## Decisions taken during development

1. **Callsign = ADS-B `flight` field** (the ident). The feed intermittently omits it for the *same*
   ICAO address between snapshots; tar1090's map hides this by retaining the last value. →
   `CallsignCache` (6 h TTL) fills gaps before selection so entities don't flip to hex. Aircraft
   that never broadcast an ident still show hex (inherent to the data).
2. **"Aircraft in range" originally exposed all positioned aircraft** despite its name. Rather than
   rename, added independent `count_use_radius` and `nearest_use_radius` toggles that reuse the
   notification radius.
3. **Radius-limited entities go `unavailable`** (not `0`/`unknown`) when the toggle is on and
   nothing is in range, so no misleading state is emitted until an aircraft is present.
4. **Voice fallback for small radius:** cache `last_in_range` (aircraft + timestamp); when nothing
   is currently in radius, answer "No aircraft within N miles. The most recent was …, X ago." Only
   when `nearest_use_radius` is on.
5. **Value extraction from the feed is defensive**: many entries lack `lat`/`lon` (`a53436`) and
   some lack `flight`. Nearest selection filters to positioned entries; naming falls back to hex.
   This receiver publishes **no ICAO type code**, so type comes only from enrichment.
6. **HA 2026 compatibility:** pass `config_entry` to `DataUpdateCoordinator` (with a `TypeError`
   fallback for older HA that lacks the parameter).
7. **HACS cannot use private repos** and does not auto-discover custom repositories; the repo is
   public but only appears in HACS for instances that add it manually.
8. **Custom sentences** must live in `config/custom_sentences/en/`; the integration copies them at
   setup and logs that a restart is required.
9. **Applying an update needs a full HA restart** (custom-integration Python is cached in
   `sys.modules`); HACS can *notice* updates after reloading its config entry.

## Layout

```
custom_components/piaware_adsb/
  __init__.py     manifest.json     const.py        config_flow.py
  coordinator.py  aircraft.py       callsign.py     geo.py
  enrichment.py   intent.py         sensor.py       binary_sensor.py
  strings.json + translations/en.json
  custom_sentences/en/what_plane.yaml
blueprints/automation/piaware_adsb/overhead_notify.yaml
tests/  hacs.json  pyproject.toml  README.md  PLAN.md  CHANGELOG.md  AGENTS.md  LICENSE
.github/workflows/  tests.yml  hassfest.yml  hacs.yml
```

## Development & release workflow

- Tests: `pytest` on **Python 3.14** with `pytest-homeassistant-custom-component==0.13.365`
  (pins HA 2026.9.2). See `AGENTS.md` for platform quirks.
- Lint: `ruff check .`.
- Release: bump `manifest.json` + `pyproject.toml` version → commit/push → `git tag` → `gh release
  create` (tag must match the manifest version for HACS).

## Risks / notes

- API cost is bounded by query-only invocation + 6 h caches.
- The overhead event/binary sensor are suppressed when notifications are disabled.
- `flight` gaps are handled by cache; genuinely ident-less targets remain hex.
- Windows cannot run the HA test harness (POSIX-only `fcntl`/`resource`); CI runs on Linux.

## Future ideas (not implemented)

- Registration lookup for ident-less aircraft (hexdb) as a display fallback.
- Cap/configure the age window for the "most recent in-range" voice fallback.
- Options-flow schema grouping / tests for the options flow.

## Acceptance criteria — met

- "what plane is that" returns the nearest aircraft with flight no., type, distance (mi) and route.
- Sensors expose nearest-aircraft data; overhead notifications fire within the configured radius.
- Installs via HACS, UI-configurable, passes ruff + pytest + hassfest/HACS.
