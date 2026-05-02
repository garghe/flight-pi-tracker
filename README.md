# flight-pi-tracker

Autonomous Raspberry Pi application that polls live flight data, finds the closest aircraft within a configurable radius, and displays it on a HUB75 RGB LED matrix panel — no interaction required after initial setup.

## How it works

Every `refresh_interval_sec` seconds the app:

1. Calls the configured flight data provider with a bounding box derived from your home coordinates and radius
2. Computes the haversine distance from home to each returned aircraft
3. Picks the single closest aircraft within the radius threshold
4. Renders it on the LED matrix (or prints to console in dev mode)
5. If nothing is in range, shows an idle screen

The loop never exits on its own — errors are logged and the loop continues, so the display keeps running unattended.

## Architecture

```
main.py                         # Entry point, polling loop, signal handling
tracker/
├── config.py                   # YAML loader + startup validation
├── models.py                   # Flight dataclass (single shared data model)
├── geo.py                      # Haversine distance + bounding box (no extra deps)
├── lookup.py                   # Airline + airport name lookups (OpenFlights data)
├── data/                       # Downloaded at runtime — airlines.dat, airports.dat
├── providers/
│   ├── base.py                 # Abstract FlightProvider interface
│   ├── opensky.py              # OpenSky Network REST implementation
│   └── __init__.py             # Provider factory (name → class)
└── display/
    ├── base.py                 # Abstract Display interface
    ├── hub75.py                # HUB75 RGB matrix via rpi-rgb-led-matrix + Pillow
    ├── console.py              # stdout fallback for development
    └── __init__.py             # Display factory (name → class)
```

Both **providers** and **displays** are pluggable. The active backend is selected by name in `config.yaml` — no code changes needed to swap implementations.

### Flight data flow

```
FlightProvider.fetch_flights(lat, lon, radius_km)
    └─▶ OpenSky /states/all          # live position, speed, altitude
    └─▶ OpenSky /flights/aircraft    # route lookup per aircraft (cached 30 min)
    └─▶ lookup.get_airline_name()    # ICAO prefix → airline name
    └─▶ lookup.get_airport_city()    # ICAO code → city name
    └─▶ returns [Flight, ...]
            └─▶ closest = min(distance_km)
                    └─▶ Display.show_flight(closest)
                         or Display.show_idle()
```

### Data model

```python
@dataclass
class Flight:
    callsign: str
    lat: float
    lon: float
    altitude_ft: int
    speed_knots: int
    heading: int              # degrees 0–360
    distance_km: float
    vertical_rate: int        # ft/min, positive = climbing
    airline: str              # e.g. "British Airways" — from OpenFlights data
    origin_airport: str       # e.g. "London" — from OpenSky route + OpenFlights lookup
    destination_airport: str  # e.g. "New York"
```

Airline names are resolved by matching the 3-letter ICAO prefix of the callsign (e.g. `BAW` → British Airways) against the [OpenFlights airlines database](https://openflights.org/data), which is downloaded automatically on first run.

Departure and destination airports are fetched from the [OpenSky `/flights/aircraft` endpoint](https://openskynetwork.github.io/opensky-api/rest.html) using a 2-hour look-back window, then mapped to city names via the OpenFlights airports database. Results are cached per aircraft for 30 minutes to stay within rate limits.

> **Tip:** Register a free account at [opensky-network.org](https://opensky-network.org) and set `provider.username` / `provider.password` in `config.yaml` for higher rate limits and more reliable route data.

### Display layout (64×32 HUB75)

```
┌────────────────────────────────┐
│  BAW123 British Airways        │  ← callsign + airline, yellow
│  London->New York              │  ← origin → destination, cyan
│  ALT 3500ft v 0.4km            │  ← altitude + climb/descend + distance, green
└────────────────────────────────┘
```

Console output example:

```
[14:43:13] ✈  BAW123   (British Airways)  London → New York
             ALT   3500ft ↓800fpm  SPD 210kt  HDG 275°  DIST 0.40km
```

## Configuration reference

All settings live in `config.yaml`:

| Key | Default | Description |
|---|---|---|
| `location.lat` | *(required)* | Home latitude — app will not start without this |
| `location.lon` | *(required)* | Home longitude — app will not start without this |
| `threshold.radius_km` | `1.6` | Only show flights within this distance (~1 mile) |
| `provider.name` | `opensky` | Flight data provider to use |
| `provider.username` | `""` | OpenSky username (optional, increases rate limits) |
| `provider.password` | `""` | OpenSky password |
| `refresh_interval_sec` | `10` | Polling interval in seconds |
| `display.type` | `hub75` | Display backend: `hub75` or `console` |
| `display.width` | `64` | Panel width in pixels |
| `display.height` | `32` | Panel height in pixels |
| `display.brightness` | `60` | Brightness 0–100 |
| `display.gpio_slowdown` | `2` | GPIO timing (1–4; increase on Pi 4 if glitchy) |

## Extending the app

### Adding a new flight data provider

1. Create `tracker/providers/myprovider.py` implementing `FlightProvider`:

```python
from tracker.providers.base import FlightProvider
from tracker.models import Flight

class MyProvider(FlightProvider):
    def fetch_flights(self, lat: float, lon: float, radius_km: float) -> list[Flight]:
        ...
```

2. Register it in `tracker/providers/__init__.py`:

```python
from tracker.providers.myprovider import MyProvider

_REGISTRY = {
    "opensky": OpenSkyProvider,
    "myprovider": MyProvider,   # ← add this
}
```

3. Set `provider.name: myprovider` in `config.yaml`.

### Adding a new display backend

Same pattern — implement `tracker/display/base.py`'s `Display` interface (`show_flight`, `show_idle`, `close`), register it in `tracker/display/__init__.py`, and set `display.type` in `config.yaml`.

## Hardware

### RGB LED Matrix Panel

The app is designed for a **64×32 HUB75 RGB LED matrix panel**. These are widely available in a few pitch sizes:

| Panel | Pitch | Link |
|---|---|---|
| 64×32 RGB LED Matrix | 3 mm | [Adafruit #2279](https://www.adafruit.com/product/2279) |
| 64×32 RGB LED Matrix | 2.5 mm | [Adafruit #5036](https://www.adafruit.com/product/5036) |
| 64×32 RGB LED Matrix | 3 mm | [The Pi Hut](https://thepihut.com/products/adafruit-64x32-rgb-led-matrix-3mm-pitch) |
| Various HUB75 panels | various | [Pimoroni](https://shop.pimoroni.com/en-us/products/rgb-led-matrix-panel) |

The **3 mm pitch** panel is a good default for a desk display — the pixels are large enough to read from ~1 m away. Choose 2.5 mm if you want a more compact unit.

### GPIO Wiring

The recommended way to connect the panel to a Raspberry Pi is via the **Adafruit RGB Matrix Bonnet** ([Adafruit #5778](https://www.adafruit.com/product/5778)), which handles level-shifting and correct pin mapping without any loose wires. A full wiring guide is available in the [Adafruit RGB Matrix + Raspberry Pi guide](https://learn.adafruit.com/rgb-matrix-panels-with-raspberry-pi-5/overview).

### Driver Library

Panel control uses [hzeller/rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix) — the de-facto standard Raspberry Pi HUB75 library.

### Power

Each 64×32 panel draws up to **4 A at 5 V** at full brightness. Use a dedicated 5 V/4 A supply — do **not** power it from the Pi's USB port.

## Quick Start

1. Edit `config.yaml` — set `location.lat` / `location.lon` and adjust `threshold.radius_km`
2. Install dependencies: `pip install -r requirements.txt`
3. Run (root required for GPIO): `sudo python main.py`

For development without a Pi, set `display.type: console` in `config.yaml` and run without `sudo`.
