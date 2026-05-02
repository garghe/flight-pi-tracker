from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class LocationConfig:
    lat: float
    lon: float


@dataclass
class ThresholdConfig:
    radius_km: float = 1.6


@dataclass
class ProviderConfig:
    name: str = "opensky"
    username: str = ""
    password: str = ""


@dataclass
class DisplayConfig:
    type: str = "hub75"
    width: int = 64
    height: int = 32
    brightness: int = 60
    gpio_slowdown: int = 2


@dataclass
class AppConfig:
    location: LocationConfig
    threshold: ThresholdConfig = field(default_factory=ThresholdConfig)
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    refresh_interval_sec: int = 10


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    raw = yaml.safe_load(Path(path).read_text())

    loc = raw.get("location", {})
    lat = loc.get("lat")
    lon = loc.get("lon")
    if lat is None or lon is None:
        sys.exit(
            "ERROR: location.lat and location.lon must be set in config.yaml before running.\n"
            "Example:\n  location:\n    lat: 51.5074\n    lon: -0.1278"
        )

    thr = raw.get("threshold", {})
    prov = raw.get("provider", {})
    disp = raw.get("display", {})

    return AppConfig(
        location=LocationConfig(lat=float(lat), lon=float(lon)),
        threshold=ThresholdConfig(radius_km=float(thr.get("radius_km", 1.6))),
        provider=ProviderConfig(
            name=prov.get("name", "opensky"),
            username=prov.get("username", "") or "",
            password=prov.get("password", "") or "",
        ),
        display=DisplayConfig(
            type=disp.get("type", "hub75"),
            width=int(disp.get("width", 64)),
            height=int(disp.get("height", 32)),
            brightness=int(disp.get("brightness", 60)),
            gpio_slowdown=int(disp.get("gpio_slowdown", 2)),
        ),
        refresh_interval_sec=int(raw.get("refresh_interval_sec", 10)),
    )
