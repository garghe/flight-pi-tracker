# flight-pi-tracker

Autonomous Raspberry Pi application that polls live flight data, finds the closest aircraft within a configurable radius, and displays it on a HUB75 RGB LED matrix panel — no interaction required after initial setup.

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
