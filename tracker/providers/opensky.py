import logging

import requests

from tracker.geo import bounding_box, haversine_km
from tracker.models import Flight
from tracker.providers.base import FlightProvider

log = logging.getLogger(__name__)

_API_URL = "https://opensky-network.org/api/states/all"

# OpenSky state-vector field indices
_IDX_CALLSIGN = 1
_IDX_LAT = 6
_IDX_LON = 5
_IDX_ALT_M = 7       # barometric altitude in metres
_IDX_SPEED_MS = 9    # ground speed m/s
_IDX_HEADING = 10    # true track degrees
_IDX_VRATE_MS = 11   # vertical rate m/s


def _ms_to_knots(ms: float | None) -> int:
    return round((ms or 0) * 1.94384)


def _m_to_ft(m: float | None) -> int:
    return round((m or 0) * 3.28084)


def _vrate_ms_to_fpm(ms: float | None) -> int:
    return round((ms or 0) * 196.85)


class OpenSkyProvider(FlightProvider):
    def __init__(self, username: str = "", password: str = "") -> None:
        self._auth = (username, password) if username else None

    def fetch_flights(self, lat: float, lon: float, radius_km: float) -> list[Flight]:
        lat_min, lon_min, lat_max, lon_max = bounding_box(lat, lon, radius_km)
        params = {
            "lamin": lat_min,
            "lomin": lon_min,
            "lamax": lat_max,
            "lomax": lon_max,
        }
        try:
            resp = requests.get(_API_URL, params=params, auth=self._auth, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            log.warning("OpenSky request failed: %s", exc)
            return []

        data = resp.json()
        states = data.get("states") or []
        flights: list[Flight] = []

        for sv in states:
            flight_lat = sv[_IDX_LAT]
            flight_lon = sv[_IDX_LON]
            if flight_lat is None or flight_lon is None:
                continue

            callsign = (sv[_IDX_CALLSIGN] or "").strip() or "??????"
            distance_km = haversine_km(lat, lon, flight_lat, flight_lon)

            flights.append(
                Flight(
                    callsign=callsign,
                    lat=flight_lat,
                    lon=flight_lon,
                    altitude_ft=_m_to_ft(sv[_IDX_ALT_M]),
                    speed_knots=_ms_to_knots(sv[_IDX_SPEED_MS]),
                    heading=round(sv[_IDX_HEADING] or 0),
                    distance_km=distance_km,
                    vertical_rate=_vrate_ms_to_fpm(sv[_IDX_VRATE_MS]),
                )
            )

        return flights
