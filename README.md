# PiAware ADS-B for Home Assistant

A custom Home Assistant integration that reads a local PiAware / tar1090 ADS-B feed and answers
the Assist voice query **"what plane is that"** with the nearest aircraft overhead — flight number,
aircraft type, distance, origin and destination.

## Features

- **Assist voice intent** — *"what plane is that"*, *"what's flying overhead"*,
  *"what's the nearest plane"*.
- **Sensors** — nearest aircraft (callsign, type, altitude, distance, bearing, compass), nearest
  distance, nearest altitude, and aircraft-in-range count.
- **Overhead binary sensor** — on while an aircraft is inside the configured radius.
- **Overhead notifications** — optional event + automation blueprint, disabled by default.
  Enriching notifications with route data via the API is a separate, disabled-by-default toggle.
- **Route/type enrichment** — optional FlightAware AeroAPI key, cached to control cost. Routes are
  spoken with the airport city/name when available (e.g. *"from Atlanta to Tokyo Haneda"*),
  falling back to the IATA/ICAO code.
- **Callsign retention** — the last callsign seen for each ICAO address is remembered, so brief
  gaps in the feed's `flight` field don't fall back to the raw hex.
- **Registration & type** — looked up from the receiver's own tar1090 database (no external API):
  the registration is spoken as *"registration number N123NW"* (skipped when it equals the
  callsign), and the aircraft type as *"a Boeing 737-800"* using the database's description.

## Requirements

- Home Assistant OS / Supervised / Container (any install can host a custom integration).
- A PiAware receiver serving `http://<host>/tar1090/data/aircraft.json` (also works with
  `/dump1090/data/aircraft.json`).
- Home coordinates configured in **Settings → System → General → Home information** (used for
  distance/bearing).
- Optional: a [FlightAware AeroAPI](https://flightaware.com/aeroapi/) key for origin/destination.

## Installation

### HACS

1. HACS → Integrations → ⋮ → **Custom repositories**.
2. Add this repository URL, category **Integration**.
3. Install **PiAware ADS-B**, then restart Home Assistant.

### Manual

Copy `custom_components/piaware_adsb` into your Home Assistant `config/custom_components/`
directory and restart.

## Configuration

1. **Settings → Devices & Services → Add Integration → PiAware ADS-B**.
2. Set the host (default `piaware.lan`), port (`80`), and feed path
   (`/tar1090/data/aircraft.json`).
3. Optionally add a FlightAware AeroAPI key to enable route lookups.
4. Choose whether to install the Assist sentences, whether to enable overhead notifications,
   whether overhead notifications should use the FlightAware API (requires a key), and whether the
   notification radius should also constrain the aircraft count and the nearest aircraft.

### Radius toggles

The notification radius can be reused independently for two other entities:

- **Only count aircraft within the notification radius** — the "Aircraft in range" sensor counts
  only aircraft inside the radius. When off (default) it counts every aircraft with a decoded
  position.
- **Only report the nearest aircraft within the notification radius** — the nearest-aircraft sensor
  and the "what plane is that" voice intent only consider aircraft inside the radius. When off
  (default) the absolute nearest aircraft is used regardless of distance.

With a toggle on, when no aircraft is within the radius the affected entities become
**unavailable** instead of reporting `0` or `unknown`, so no state is emitted until an aircraft is
actually in range.

## Assist setup

At setup the integration copies `custom_sentences/en/what_plane.yaml` into
`config/custom_sentences/en/`. Custom sentences are loaded at startup, so **restart Home Assistant
once** after the first install. Then expose an Assist satellite or use the Assist dialog and say:

> "what plane is that"
> "what's the nearest plane"

The default Home Assistant conversation agent handles the intent; LLM-based agents would need
additional tool calling.

With **Only report the nearest aircraft within the notification radius** enabled and a small radius,
an aircraft can leave the radius between polls. In that case the assistant says no aircraft is
within the radius and describes the most recent aircraft that was in range, including how long ago
(e.g. *"No aircraft within 2 miles. The most recent was DAL100, a 737, 1.4 miles to the
north-east, 40 seconds ago."*).

## Overhead notifications

1. Enable **Enable overhead notifications** in the integration options and set the radius.
2. Optionally enable **Use the FlightAware API for overhead notifications** to include the route
   (requires an AeroAPI key; lookups are cached and happen once per overhead aircraft).
3. Create an automation from the blueprint **PiAware ADS-B - aircraft overhead notification**.
4. The event `piaware_adsb_aircraft_overhead` carries `hex`, `callsign`, `type_code`,
   `altitude_ft`, `distance_miles`, `compass`, `squawk`, and — when API enrichment is on —
   `origin`, `destination`, `airline` and `enriched`.

## Entities

| Entity | Description |
|---|---|
| `sensor.nearest_aircraft` | Callsign/ICAO of the nearest aircraft; full details as attributes |
| `sensor.nearest_aircraft_distance` | Distance to the nearest aircraft (miles) |
| `sensor.nearest_aircraft_altitude` | Nearest aircraft altitude (feet) |
| `sensor.aircraft_in_range` | Aircraft with a decoded position; limited to the radius when the count toggle is on |
| `binary_sensor.aircraft_overhead` | On while an aircraft is within the overhead radius |

## Development

Tests require **Python 3.14** (the pinned `pytest-homeassistant-custom-component` tracks a
current Home Assistant). The test harness is POSIX-only.

```bash
python -m pip install -e ".[test]"
ruff check .
pytest
```

On Windows add the POSIX shims: `$env:PYTHONPATH = "tools\win_test_shims"` before `pytest`.

Project docs: [`PLAN.md`](PLAN.md) (architecture + decisions), [`CHANGELOG.md`](CHANGELOG.md)
(version history), [`AGENTS.md`](AGENTS.md) (development memory, commands, release process).

## Attribution

Aircraft data from PiAware / tar1090. Route and aircraft type data from FlightAware AeroAPI and
hexdb.io.

## License

MIT
