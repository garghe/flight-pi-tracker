from abc import ABC, abstractmethod

from tracker.models import Flight


class Display(ABC):
    @abstractmethod
    def show_flight(self, flight: Flight) -> None:
        """Render the given flight on the display."""

    @abstractmethod
    def show_idle(self) -> None:
        """Render an idle/no-aircraft state."""

    @abstractmethod
    def close(self) -> None:
        """Release display resources."""
