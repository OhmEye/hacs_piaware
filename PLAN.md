# Project Plan — `piaware_adsb` Home Assistant Integration

## Goal

Voice query via **HA Assist**: *"what plane is that"* answers with the **nearest aircraft
overhead** — flight number, aircraft type, distance, origin and destination. The project also
exposes dashboard sensors, optional overhead notifications, and production polish (config flow,
tests, HACS packaging).

## Confirmed decisions

| Item | Decision |
|---|---|
| Voice front-end | HA Assist, default conversation agent |
| Selection | Nearest aircraft overhead, regardless of distance |
| Data source | `http://piaware.lan/tar1090/data/aircraft.json` (verified live) |
| Spoken detail | flight no./callsign, type, distance, origin, destination |
| Units | Miles, altitude in feet, bearing as compass direction |
| Enrichment | FlightAware AeroAPI, on voice query only, cached |
| Reference location | HA `zone.home` / exact coordinates (Settings → Home Information) |
| Overhead notifications | Config option, configurable radius, disabled by default |
| Packaging | Custom integration, HACS-installable |
| Extras | Dashboard sensors, tests, CI, config flow |

## Architecture

```
tar1090 aircraft.json ──(aiohttp poll / DataUpdateCoordinator)──▶ [coordinator]
   └─ parse (aircraft.py) → geo distance/bearing (geo.py) → nearest snapshot
        ├─ sensors: nearest_callsign / type / altitude / distance_mi / bearing / count
        ├─ binary_sensor: aircraft_overhead (only when notifications enabled)
        └─ assist intent "what plane is that"
             └─ enrichment.py → FlightAware AeroAPI /flights/{ident} (TTL cache)
                  └─ spoken response (fallbacks for missing route/type)
```

## Layout

```
custom_components/piaware_adsb/
  __init__.py        manifest.json     const.py
  config_flow.py     coordinator.py    geo.py       aircraft.py
  enrichment.py      intent.py         sensor.py    binary_sensor.py
  strings.json + translations/en.json
  custom_sentences/en/what_plane.yaml
blueprints/automation/piaware_adsb/overhead_notify.yaml
tests/                hacs.json         pyproject.toml     README.md
.github/workflows/    tests.yml  hassfest.yml  hacs.yml
```

## Phases

1. **Scaffold** — manifest, HACS metadata, pyproject (ruff + pytest), CI stubs, README skeleton.
2. **Core polling** — aircraft parser + geo + coordinator; config flow (host, path, interval,
   notifications toggle + radius, FlightAware key); home coords from `zone.home`.
3. **Entities** — `sensor.*` (nearest callsign/type/altitude ft/distance mi/bearing/compass,
   in-range count) and `binary_sensor.aircraft_overhead` (active only when notifications enabled).
4. **Voice intent** — register intents + sentence file; handler selects nearest by great-circle
   distance (no cutoff), enriches via AeroAPI, speaks
   `"{flight}, a {type}, {dist} miles to the {compass}, from {origin} to {destination}"`.
5. **Enrichment** — AeroAPI `/flights/{ident}` with `x-apikey`, TTL cache (~6 h) + in-flight
   de-dup; type fallback via `hexdb.io`; runs only on intent call.
6. **Notifications** — event fires only when enabled and within configured radius (default
   disabled); ship automation blueprint.
7. **Tests & polish** — pytest, fixtures from real `aircraft.json`, translations, README,
   HACS + hassfest validation.

## Risks / notes

- **Custom sentences** must live in `config/custom_sentences/en/`; the component cannot ship them
  through HACS. The integration offers a consented install step at setup, with manual-copy fallback.
- Many aircraft lack `lat`/`lon`/`flight`; nearest selection filters to positioned entries and
  falls back to `hex` for naming.
- API cost is controlled by query-only invocation and caching.
- The overhead binary sensor and event are suppressed when notifications are disabled.

## Acceptance criteria

- "what plane is that" returns the nearest aircraft with flight no., type, distance (mi) and
  route in under ~3 s.
- Sensors expose nearest-aircraft data; overhead notification fires within the configured radius
  only when enabled.
- Installs via HACS, is UI-configurable, and passes ruff + pytest + hassfest/HACS.
