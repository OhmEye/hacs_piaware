# PiAware ADS-B for Home Assistant

A custom Home Assistant integration that reads a local PiAware / tar1090 ADS-B feed and answers
the Assist voice query **"what plane is that"** with the nearest aircraft overhead — flight number,
aircraft type, distance, origin and destination.

## Features

- **Assist voice intent** — *"what plane is that"* / *"what's flying overhead"*.
- **Sensors** — nearest aircraft (callsign, type, altitude, distance, bearing, compass), nearest
  distance, nearest altitude, and aircraft-in-range count.
- **Overhead binary sensor** — on while an aircraft is inside the configured radius.
- **Overhead notifications** — optional event + automation blueprint, disabled by default.
- **Route/type enrichment** — optional FlightAware AeroAPI key, cached to control cost.

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
4. Choose whether to install the Assist sentences and whether to enable overhead notifications.

## Assist setup

At setup the integration copies `custom_sentences/en/what_plane.yaml` into
`config/custom_sentences/en/`. Custom sentences are loaded at startup, so **restart Home Assistant
once** after the first install. Then expose an Assist satellite or use the Assist dialog and say:

> "what plane is that"

The default Home Assistant conversation agent handles the intent; LLM-based agents would need
additional tool calling.

## Overhead notifications

1. Enable **Enable overhead notifications** in the integration options and set the radius.
2. Create an automation from the blueprint **PiAware ADS-B - aircraft overhead notification**.
3. The event `piaware_adsb_aircraft_overhead` carries `hex`, `callsign`, `type_code`,
   `altitude_ft`, `distance_miles`, `compass` and `squawk`.

## Entities

| Entity | Description |
|---|---|
| `sensor.nearest_aircraft` | Callsign/ICAO of the nearest aircraft; full details as attributes |
| `sensor.nearest_aircraft_distance` | Distance to the nearest aircraft (miles) |
| `sensor.nearest_aircraft_altitude` | Nearest aircraft altitude (feet) |
| `sensor.aircraft_in_range` | Number of positioned aircraft in range |
| `binary_sensor.aircraft_overhead` | On while an aircraft is within the overhead radius |

## Development

```bash
python -m pip install -e ".[test]"
ruff check .
pytest
```

## Attribution

Aircraft data from PiAware / tar1090. Route and aircraft type data from FlightAware AeroAPI and
hexdb.io.

## License

MIT
