# AGENTS.md — development memory for `piaware_adsb`

This file records how to work on this repo and the decisions/quirks that must not be lost.

## What this is

- Home Assistant custom integration, domain **`piaware_adsb`** ("PiAware ADS-B").
- Reads a local tar1090/dump1090 feed and answers the Assist query *"what plane is that"* with the
  nearest aircraft; plus sensors, overhead notifications, and route enrichment.
- Public GitHub repo: <https://github.com/OhmEye/hacs_piaware> (HACS custom repository).
- See `PLAN.md` (architecture + decision log) and `CHANGELOG.md` (per-version history).

## Commands

Lint (any OS):

```bash
ruff check .
```

Tests (CI / Linux):

```bash
pip install ruff "pytest-homeassistant-custom-component==0.13.365" tzdata
pytest -q
```

Tests on Windows (dev machine — the HA harness is POSIX-only):

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python -m pip install "pytest-homeassistant-custom-component==0.13.365" tzdata
$env:PYTHONPATH = "tools\win_test_shims"   # fcntl/resource shims
.\.venv\Scripts\python -m pytest -q
```

## Environment facts / constraints

- **Python 3.14 is required for tests.** `pytest-homeassistant-custom-component==0.13.365` pins
  **Home Assistant 2026.9.2**. Do not unpin without re-running the suite; newer/older pairings
  change behaviour (e.g. HA 2026 requires `config_entry` on `DataUpdateCoordinator`).
- The HA test harness imports POSIX-only modules (`fcntl`, `resource`); `tools/win_test_shims/`
  provides no-op shims for local Windows runs only. CI is Linux.
- No build step — HACS copies `custom_components/piaware_adsb/` verbatim; `manifest.json` must be
  valid and keys must be in hassfest order (`domain`, `name`, then alphabetical).
- CI: `.github/workflows/tests.yml` (Python 3.14 + ruff + pytest), `hassfest.yml`, `hacs.yml`.

## Architecture invariants (do not regress)

- `PiAwareCoordinator` (poll `tar1090/data/aircraft.json`) **must pass `config_entry`** to
  `DataUpdateCoordinator` (with a `TypeError` fallback for older HA).
- **`CallsignCache`** (`callsign.py`, 6 h TTL): the feed's `flight` field is intermittent for the
  same ICAO hex, so reuse the last callsign seen instead of falling back to hex.
- **Radius toggles** (`count_use_radius`, `nearest_use_radius`, default off) reuse
  `notification_radius_miles`. When on and nothing is in range, the affected sensors are
  `unavailable` (not `0`/`unknown`).
- **Voice fallback:** coordinator keeps `last_in_range = (aircraft, timestamp)`; when
  `nearest_use_radius` is on and nothing is in range, the intent reports the most recent aircraft
  and how long ago.
- **Metadata** (registration + aircraft type) is looked up from the receiver's own tar1090 database
  (no external API): `registration.py` (`Tar1090Database`) scrapes `databaseFolder` from
  `index.html` and follows the `db-*/<prefix>.js` trie; each entry is
  `[registration, type_code, flags, long_name]`. Only invoked by the intent, not per poll. The
  voice phrase is `registration number <reg>` (skipped when it equals the callsign/hex) and the
  type is spoken as `a/an <long_name>` when available, falling back to the ICAO type code.
  Note: `code`/`name` are absent (or `00`) for some aircraft — always handle empty metadata.
- **Route labels**: `RouteInfo.origin_label`/`destination_label` prefer AeroAPI `city` →
  `airport_name` → code; the intent speaks these (e.g. "from Atlanta to Tokyo Haneda"). The
  overhead event exposes both codes and `origin_name`/`destination_name`.
- Reference coordinates come from `hass.config.latitude/longitude`.
- Custom Assist sentences are copied to `config/custom_sentences/en/` at setup; a HA **restart** is
  required for them (and for any custom-integration code update) to take effect.
- The overhead notification blueprint is **bundled** at
  `custom_components/piaware_adsb/blueprints/automation/piaware_adsb/overhead_notify.yaml` and
  always copied to `config/blueprints/automation/piaware_adsb/` at setup (HACS does not install
  blueprints). It uses an entity selector (`domain: assist_satellite`) to choose which voice
  assistants announce; blueprints inject action inputs with `sequence: !input`.

## Release process

1. Bump the version in **both** `custom_components/piaware_adsb/manifest.json` and `pyproject.toml`.
2. `git add -A && git commit -m "..." && git push origin main`.
3. `git tag -a vX.Y.Z -m "PiAware ADS-B vX.Y.Z" && git push origin vX.Y.Z`.
4. `gh release create vX.Y.Z --title "vX.Y.Z" --notes "..."`.
5. Verify: `gh run list --limit 3` — Tests, Hassfest, HACS must be green.

The git tag **must equal** the manifest version, or HACS will not surface the update.

## Git / remote notes

- Remote `origin` = `https://github.com/OhmEye/hacs_piaware.git`.
- Repo-local identity is set (`OhmEye` / `OhmEye@users.noreply.github.com`); there is no global git
  identity on this machine.
- On Windows/PowerShell, `git push` prints progress to stderr and PowerShell shows it as an error,
  but `$LASTEXITCODE` is `0`. Check the exit code, not the red text.

## Data quirks (this receiver)

- Endpoint: `http://piaware.lan/tar1090/data/aircraft.json`; receiver coords via
  `tar1090/data/receiver.json` (42.07002, -77.05097).
- Many entries lack `lat`/`lon`; nearest selection must only consider positioned aircraft.
- The feed has **no ICAO type code** field; but the tar1090 client-side database provides both a
  type code and a long description (`[registration, type_code, flags, long_name]`), which
  `registration.py` reads. External enrichment (FlightAware AeroAPI, else hexdb.io) is a fallback.
- The feed has **no registration** either; tar1090 exposes it via its client-side database
  (`index.html` → `databaseFolder` → `db-*/<prefix>.js`).
- Some aircraft never broadcast an ident and will always display as hex — expected.

## Module map

| File | Responsibility |
|---|---|
| `__init__.py` | setup/unload, coordinator + enrichment wiring, sentence install |
| `config_flow.py` | UI config + options (schema, validation) |
| `coordinator.py` | polling, nearest/in-range selection, overhead event, `last_in_range` |
| `aircraft.py` | dataclass + JSON parsing, nearest helper |
| `callsign.py` | per-hex callsign retention |
| `geo.py` | haversine distance, bearing, compass |
| `enrichment.py` | FlightAware AeroAPI + hexdb, TTL cache/de-dup |
| `registration.py` | local tar1090 DB metadata: registration + type (trie) |
| `intent.py` | Assist intent, speech building, recent-in-range fallback |
| `sensor.py` / `binary_sensor.py` | entities (radius/unavailable logic) |
