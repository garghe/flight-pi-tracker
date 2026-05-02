from dataclasses import dataclass, field


@dataclass
class Flight:
    callsign: str
    lat: float
    lon: float
    altitude_ft: int
    speed_knots: int
    heading: int        # degrees 0-360
    distance_km: float
    vertical_rate: int  # ft/min, positive = climbing
    airline: str = ""
    origin_airport: str = ""
    destination_airport: str = ""
