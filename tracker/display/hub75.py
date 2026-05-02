from __future__ import annotations

import logging

from tracker.display.base import Display
from tracker.models import Flight

log = logging.getLogger(__name__)

_WHITE = (255, 255, 255)
_YELLOW = (255, 215, 0)
_CYAN = (0, 200, 255)
_GREEN = (0, 220, 100)
_DIM = (80, 80, 80)


class Hub75Display(Display):
    """HUB75 RGB LED matrix display via rpi-rgb-led-matrix + Pillow."""

    def __init__(
        self,
        width: int = 64,
        height: int = 32,
        brightness: int = 60,
        gpio_slowdown: int = 2,
        **_: object,
    ) -> None:
        self._width = width
        self._height = height
        self._matrix = self._init_matrix(width, height, brightness, gpio_slowdown)
        self._font = self._load_font()

    def _init_matrix(self, width: int, height: int, brightness: int, slowdown: int):
        try:
            from rgbmatrix import RGBMatrix, RGBMatrixOptions  # type: ignore[import]

            opts = RGBMatrixOptions()
            opts.rows = height
            opts.cols = width
            opts.chain_length = 1
            opts.parallel = 1
            opts.brightness = brightness
            opts.gpio_slowdown = slowdown
            opts.disable_hardware_pulsing = False
            return RGBMatrix(options=opts)
        except ImportError:
            log.warning(
                "rpi-rgb-led-matrix not available — Hub75Display will run in no-op mode. "
                "Use display.type: console for development."
            )
            return None

    def _load_font(self):
        try:
            from PIL import ImageFont  # type: ignore[import]

            for path in (
                "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
            ):
                try:
                    return ImageFont.truetype(path, 8)
                except OSError:
                    continue
            return ImageFont.load_default()
        except ImportError:
            return None

    def _render(self, lines: list[tuple[str, tuple[int, int, int]]]) -> None:
        if self._matrix is None:
            return
        try:
            from PIL import Image, ImageDraw  # type: ignore[import]

            img = Image.new("RGB", (self._width, self._height), (0, 0, 0))
            draw = ImageDraw.Draw(img)
            y = 1
            for text, colour in lines:
                draw.text((1, y), text, font=self._font, fill=colour)
                y += 10
            self._matrix.SetImage(img.convert("RGB"))
        except Exception as exc:
            log.error("Hub75 render error: %s", exc)

    def show_flight(self, flight: Flight) -> None:
        vdir = "^" if flight.vertical_rate >= 0 else "v"

        # Line 1: callsign + airline (truncated to fit 64px)
        label = flight.callsign
        if flight.airline:
            label = f"{flight.callsign} {flight.airline[:12]}"

        # Line 2: route (origin → destination)
        origin = (flight.origin_airport or "unknown")[:10]
        dest = (flight.destination_airport or "unknown")[:10]
        route_line = f"{origin}->{dest}"

        # Line 3: altitude + vertical trend + distance
        alt_line = f"ALT {flight.altitude_ft}ft {vdir} {flight.distance_km:.1f}km"

        self._render([
            (label[:21], _YELLOW),
            (route_line[:21], _CYAN),
            (alt_line[:21], _GREEN),
        ])

    def show_idle(self) -> None:
        self._render([
            ("", _DIM),
            ("  NO FLIGHTS", _DIM),
            ("   IN RANGE", _DIM),
        ])

    def close(self) -> None:
        if self._matrix is not None:
            self._matrix.Clear()
