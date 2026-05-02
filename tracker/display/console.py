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

        airline = f" ({flight.airline})" if flight.airline else ""
        route = ""
        if flight.origin_airport or flight.destination_airport:
            origin = flight.origin_airport or "?"
            dest = flight.destination_airport or "?"
            route = f"  {origin} → {dest}"

        print(
            f"[{ts}] ✈  {flight.callsign:<8}{airline}{route}\n"
            f"         ALT {flight.altitude_ft:>6}ft {vdir}{abs(flight.vertical_rate)}fpm  "
            f"SPD {flight.speed_knots:>3}kt  "
            f"HDG {flight.heading:>3}°  "
            f"DIST {flight.distance_km:.2f}km"
        )

    def show_idle(self) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] -- no flights in range --")

    def close(self) -> None:
        pass
