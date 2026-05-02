"""
Airline and airport name lookups backed by the OpenFlights open dataset.
Data is downloaded once on first use and cached in a local data/ directory.
"""

from __future__ import annotations

import csv
import io
import logging
from pathlib import Path

import requests

log = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent / "data"
_AIRLINES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat"
_AIRPORTS_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"

# Loaded lazily on first lookup
_airlines: dict[str, str] | None = None   # ICAO 3-letter code → airline name
_airports: dict[str, str] | None = None   # ICAO 4-letter code → city name


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


def _load_airlines() -> dict[str, str]:
    dest = _DATA_DIR / "airlines.dat"
    result: dict[str, str] = {}
    if not _ensure_file(_AIRLINES_URL, dest):
        return result
    with open(dest, encoding="utf-8", errors="replace") as fh:
        for row in csv.reader(fh):
            if len(row) < 6:
                continue
            name = row[1].strip()
            icao = row[4].strip()
            if icao and icao != r"\N" and name and name != r"\N":
                result[icao.upper()] = name
    log.info("Loaded %d airlines", len(result))
    return result


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


def _airlines_db() -> dict[str, str]:
    global _airlines
    if _airlines is None:
        _airlines = _load_airlines()
    return _airlines


def _airports_db() -> dict[str, str]:
    global _airports
    if _airports is None:
        _airports = _load_airports()
    return _airports


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
