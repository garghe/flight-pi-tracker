"""
Airline and airport name lookups backed by the OpenFlights open dataset.
Data is downloaded once on first use and cached in a local data/ directory.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

import requests

log = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent / "data"
_AIRLINES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat"
_AIRPORTS_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
_ROUTES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat"

# Loaded lazily on first lookup
_airlines: dict[str, str] | None = None        # ICAO 3-letter code → airline name
_airline_iata: dict[str, str] | None = None    # ICAO 3-letter code → IATA 2-letter code
_airports: dict[str, str] | None = None        # ICAO 4-letter code → city name
# (airline_iata, origin_icao) → set of destination ICAO codes
_routes: dict[tuple[str, str], set[str]] | None = None


def _ensure_file(url: str, dest: Path) -> bool:
    if dest.exists():
        return True
    log.info("Downloading %s → %s", url, dest)
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(resp.content)
        return True
    except Exception as exc:
        log.warning("Could not download %s: %s", url, exc)
        return False


def _load_airlines() -> tuple[dict[str, str], dict[str, str]]:
    """Return (icao→name, icao→iata) dicts."""
    dest = _DATA_DIR / "airlines.dat"
    names: dict[str, str] = {}
    icao_to_iata: dict[str, str] = {}
    if not _ensure_file(_AIRLINES_URL, dest):
        return names, icao_to_iata
    with open(dest, encoding="utf-8", errors="replace") as fh:
        for row in csv.reader(fh):
            if len(row) < 6:
                continue
            name = row[1].strip()
            iata = row[3].strip()
            icao = row[4].strip()
            if icao and icao != r"\N":
                if name and name != r"\N":
                    names[icao.upper()] = name
                if iata and iata != r"\N":
                    icao_to_iata[icao.upper()] = iata.upper()
    log.info("Loaded %d airlines", len(names))
    return names, icao_to_iata


def _load_airports() -> dict[str, str]:
    dest = _DATA_DIR / "airports.dat"
    result: dict[str, str] = {}
    if not _ensure_file(_AIRPORTS_URL, dest):
        return result
    with open(dest, encoding="utf-8", errors="replace") as fh:
        for row in csv.reader(fh):
            if len(row) < 6:
                continue
            city = row[2].strip()
            icao = row[5].strip()
            if icao and icao != r"\N":
                result[icao.upper()] = city or row[1].strip()
    log.info("Loaded %d airports", len(result))
    return result


def _load_routes() -> dict[tuple[str, str], set[str]]:
    dest = _DATA_DIR / "routes.dat"
    result: dict[tuple[str, str], set[str]] = {}
    if not _ensure_file(_ROUTES_URL, dest):
        return result
    # fields: airline_iata, airline_id, src_iata, src_id, dst_iata, dst_id, ...
    # OpenFlights routes.dat uses IATA codes, not ICAO — we map via airports_db
    iata_to_icao = {v: k for k, v in _airports_db().items()}  # city lookup is ICAO→city; we need iata→icao
    # rebuild: load airports with iata col (col index 4)
    airports_dest = _DATA_DIR / "airports.dat"
    iata_to_icao = {}
    if airports_dest.exists():
        with open(airports_dest, encoding="utf-8", errors="replace") as fh:
            for row in csv.reader(fh):
                if len(row) < 6:
                    continue
                iata = row[4].strip()
                icao = row[5].strip()
                if iata and iata != r"\N" and icao and icao != r"\N":
                    iata_to_icao[iata.upper()] = icao.upper()

    with open(dest, encoding="utf-8", errors="replace") as fh:
        for row in csv.reader(fh):
            if len(row) < 5:
                continue
            airline_iata = row[0].strip().upper()
            src_iata = row[2].strip().upper()
            dst_iata = row[4].strip().upper()
            if not airline_iata or not src_iata or not dst_iata:
                continue
            if r"\N" in (airline_iata, src_iata, dst_iata):
                continue
            # Convert IATA → ICAO where possible; fall back to IATA code
            src_icao = iata_to_icao.get(src_iata, src_iata)
            dst_icao = iata_to_icao.get(dst_iata, dst_iata)
            # Map airline IATA to ICAO via airlines db
            key = (airline_iata, src_icao)
            result.setdefault(key, set()).add(dst_icao)
    log.info("Loaded %d airline+origin route combinations", len(result))
    return result


def _airlines_db() -> dict[str, str]:
    global _airlines, _airline_iata
    if _airlines is None:
        _airlines, _airline_iata = _load_airlines()
    return _airlines


def _airline_iata_db() -> dict[str, str]:
    global _airlines, _airline_iata
    if _airline_iata is None:
        _airlines, _airline_iata = _load_airlines()
    return _airline_iata


def _airports_db() -> dict[str, str]:
    global _airports
    if _airports is None:
        _airports = _load_airports()
    return _airports


def _routes_db() -> dict[tuple[str, str], set[str]]:
    global _routes
    if _routes is None:
        _routes = _load_routes()
    return _routes


def get_airline_name(callsign: str) -> str:
    """Return airline name for a callsign, e.g. 'BAW123' → 'British Airways'."""
    if not callsign or len(callsign) < 3:
        return ""
    icao_prefix = callsign[:3].upper()
    return _airlines_db().get(icao_prefix, "")


def get_airport_city(icao: str) -> str:
    """Return city name for an ICAO airport code, e.g. 'EGLL' → 'London'."""
    if not icao or icao == r"\N":
        return ""
    return _airports_db().get(icao.upper(), icao)


def get_destination_from_routes(callsign: str, origin_icao: str) -> str:
    """
    Look up destination ICAO using OpenFlights routes.dat.
    Returns a result only when there is exactly one known destination for this
    airline + origin combination — avoids guessing when multiple routes exist.
    """
    if not callsign or len(callsign) < 3 or not origin_icao:
        return ""
    icao_prefix = callsign[:3].upper()
    airline_iata = _airline_iata_db().get(icao_prefix, "")
    if not airline_iata:
        return ""
    destinations = _routes_db().get((airline_iata, origin_icao.upper()), set())
    if len(destinations) == 1:
        return next(iter(destinations))
    return ""
