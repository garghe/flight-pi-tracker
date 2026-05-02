#!/usr/bin/env python3
"""Flight Pi Tracker — autonomous nearby-flight display for Raspberry Pi."""

import argparse
import logging
import signal
import sys
import time

from tracker.config import load_config
from tracker.display import get_display
from tracker.providers import get_provider

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("main")


def main() -> None:
    parser = argparse.ArgumentParser(description="Display nearby flights on an LED matrix.")
    parser.add_argument(
        "--config", default="config.yaml", help="Path to config YAML (default: config.yaml)"
    )
    args = parser.parse_args()

    cfg = load_config(args.config)

    provider = get_provider(
        cfg.provider.name,
        username=cfg.provider.username,
        password=cfg.provider.password,
    )
    display = get_display(
        cfg.display.type,
        width=cfg.display.width,
        height=cfg.display.height,
        brightness=cfg.display.brightness,
        gpio_slowdown=cfg.display.gpio_slowdown,
    )

    lat = cfg.location.lat
    lon = cfg.location.lon
    radius_km = cfg.threshold.radius_km
    interval = cfg.refresh_interval_sec

    log.info(
        "Started — location=(%.4f, %.4f) radius=%.1fkm provider=%s display=%s",
        lat, lon, radius_km, cfg.provider.name, cfg.display.type,
    )

    def _shutdown(sig, _frame):
        log.info("Shutting down (signal %s)", sig)
        display.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    while True:
        try:
            flights = provider.fetch_flights(lat, lon, radius_km)
            if flights:
                closest = min(flights, key=lambda f: f.distance_km)
                log.info(
                    "Closest: %s at %.2fkm (alt %dft, %dkt, hdg %d°)",
                    closest.callsign, closest.distance_km,
                    closest.altitude_ft, closest.speed_knots, closest.heading,
                )
                display.show_flight(closest)
            else:
                log.info("No flights within %.1fkm", radius_km)
                display.show_idle()
        except Exception as exc:
            log.error("Polling error: %s", exc)

        time.sleep(interval)


if __name__ == "__main__":
    main()
