import logging
from datetime import datetime

from tracker.display.base import Display
from tracker.models import Flight

log = logging.getLogger(__name__)


class ConsoleDisplay(Display):
    """Prints flight info to stdout — useful for development on non-Pi hardware."""

    def __init__(self, **_: object) -> None:
        pass

    def show_flight(self, flight: Flight) -> None:
        vdir = "↑" if flight.vertical_rate >= 0 else "↓"
        ts = datetime.now().strftime("%H:%M:%S")
        print(
            f"[{ts}] ✈  {flight.callsign:<8} "
            f"ALT {flight.altitude_ft:>6}ft  "
            f"SPD {flight.speed_knots:>3}kt  "
            f"HDG {flight.heading:>3}°  "
            f"DIST {flight.distance_km:.2f}km  "
            f"{vdir}{abs(flight.vertical_rate)}fpm"
        )

    def show_idle(self) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] -- no flights in range --")

    def close(self) -> None:
        pass
