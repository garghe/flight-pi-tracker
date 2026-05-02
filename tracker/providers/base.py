from abc import ABC, abstractmethod

from tracker.models import Flight


class FlightProvider(ABC):
    @abstractmethod
    def fetch_flights(self, lat: float, lon: float, radius_km: float) -> list[Flight]:
        """Return all observable flights within radius_km of (lat, lon)."""
