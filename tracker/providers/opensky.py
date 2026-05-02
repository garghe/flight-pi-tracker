import logging
import time

import requests

from tracker.geo import bounding_box, haversine_km
from tracker.lookup import get_airline_name, get_airport_city
from tracker.models import Flight
from tracker.providers.base import FlightProvider

log = logging.getLogger(__name__)

_STATES_URL = "https://opensky-network.org/api/states/all"
_ROUTES_URL = "https://opensky-network.org/api/routes"
_FLIGHTS_URL = "https://opensky-network.org/api/flights/aircraft"

# OpenSky state-vector field indices
_IDX_ICAO24 = 0
_IDX_CALLSIGN = 1
_IDX_LAT = 6
_IDX_LON = 5
_IDX_ALT_M = 7       # barometric altitude in metres
_IDX_SPEED_MS = 9    # ground speed m/s
_IDX_HEADING = 10    # true track degrees
_IDX_VRATE_MS = 11   # vertical rate m/s

# Route cache: callsign → (origin_icao, dest_icao, fetched_at)
_route_cache: dict[str, tuple[str, str, float]] = {}
_ROUTE_TTL = 1800  # seconds — routes don't change mid-flight


def _ms_to_knots(ms: float | None) -> int:
    return round((ms or 0) * 1.94384)


def _m_to_ft(m: float | None) -> int:
    return round((m or 0) * 3.28084)


def _vrate_ms_to_fpm(ms: float | None) -> int:
    return round((ms or 0) * 196.85)


class OpenSkyProvider(FlightProvider):
    def __init__(self, username: str = "", password: str = "") -> None:
        self._auth = (username, password) if username else None
        if self._auth:
            log.info("OpenSky: using authenticated requests (user=%s)", username)
        else:
            log.warning("OpenSky: no credentials set — route lookups will likely fail")

    def fetch_flights(self, lat: float, lon: float, radius_km: float) -> list[Flight]:
        lat_min, lon_min, lat_max, lon_max = bounding_box(lat, lon, radius_km)
        params = {
            "lamin": lat_min,
            "lomin": lon_min,
            "lamax": lat_max,
            "lomax": lon_max,
        }
        try:
            resp = requests.get(_STATES_URL, params=params, auth=self._auth, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            log.warning("OpenSky request failed: %s", exc)
            return []

        states = resp.json().get("states") or []
        flights: list[Flight] = []

        for sv in states:
            flight_lat = sv[_IDX_LAT]
            flight_lon = sv[_IDX_LON]
            if flight_lat is None or flight_lon is None:
                continue

            icao24 = (sv[_IDX_ICAO24] or "").strip()
            callsign = (sv[_IDX_CALLSIGN] or "").strip() or "??????"
            distance_km = haversine_km(lat, lon, flight_lat, flight_lon)

            origin, destination = self._get_route(callsign, icao24)

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
                    airline=get_airline_name(callsign),
                    origin_airport=get_airport_city(origin),
                    destination_airport=get_airport_city(destination),
                )
            )

        return flights

    def _get_route(self, callsign: str, icao24: str) -> tuple[str, str]:
        """Return (origin_icao, destination_icao), trying /routes first then /flights."""
        cache_key = callsign or icao24
        if not cache_key:
            return "", ""

        cached = _route_cache.get(cache_key)
        if cached and time.time() - cached[2] < _ROUTE_TTL:
            return cached[0], cached[1]

        # Primary: undocumented but reliable /routes endpoint (callsign → route array)
        if callsign and callsign != "??????":
            result = self._routes_endpoint(callsign)
            if result != ("", ""):
                _route_cache[cache_key] = (*result, time.time())
                return result

        # Fallback: /flights/aircraft with a 2-hour look-back window
        if icao24:
            result = self._flights_endpoint(icao24)
            if result != ("", ""):
                _route_cache[cache_key] = (*result, time.time())
                return result

        _route_cache[cache_key] = ("", "", time.time())
        return "", ""

    def _routes_endpoint(self, callsign: str) -> tuple[str, str]:
        try:
            resp = requests.get(
                _ROUTES_URL, params={"callsign": callsign}, auth=self._auth, timeout=10
            )
            log.info("Routes API %s → HTTP %s", callsign, resp.status_code)
            if resp.status_code == 403:
                log.warning("Routes API returned 403 for %s — check credentials", callsign)
                return "", ""
            if resp.status_code == 404:
                log.info("Routes API: no route on record for %s", callsign)
                return "", ""
            resp.raise_for_status()
            data = resp.json()
            route = data.get("route") or []
            log.info("Routes API raw response for %s: %s", callsign, data)
            if len(route) >= 2:
                origin, dest = route[0], route[-1]
                log.info("Route (routes API) %s: %s → %s", callsign, origin, dest)
                return origin, dest
        except Exception as exc:
            log.warning("Routes endpoint failed for %s: %s", callsign, exc)
        return "", ""

    def _flights_endpoint(self, icao24: str) -> tuple[str, str]:
        now = int(time.time())
        params = {"icao24": icao24, "begin": now - 7200, "end": now}
        try:
            resp = requests.get(_FLIGHTS_URL, params=params, auth=self._auth, timeout=10)
            log.info("Flights API %s → HTTP %s", icao24, resp.status_code)
            resp.raise_for_status()
            flights = resp.json()
            if flights:
                latest = max(flights, key=lambda f: f.get("lastSeen", 0))
                origin = latest.get("estDepartureAirport") or ""
                dest = latest.get("estArrivalAirport") or ""
                log.info("Route (flights API) %s: origin=%r dest=%r", icao24, origin, dest)
                return origin, dest
            else:
                log.info("Flights API: no flights found for %s in last 2h", icao24)
        except Exception as exc:
            log.warning("Flights endpoint failed for %s: %s", icao24, exc)
        return "", ""
