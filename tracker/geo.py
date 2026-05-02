import math


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in kilometres between two lat/lon points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def bounding_box(lat: float, lon: float, radius_km: float) -> tuple[float, float, float, float]:
    """Return (lat_min, lon_min, lat_max, lon_max) for a square bounding box."""
    delta_lat = math.degrees(radius_km / 6371.0)
    delta_lon = math.degrees(radius_km / (6371.0 * math.cos(math.radians(lat))))
    return lat - delta_lat, lon - delta_lon, lat + delta_lat, lon + delta_lon
