import math
from typing import Tuple, List, Optional, Dict, Any


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on the Earth's surface
    using the Haversine formula.

    Args:
        lat1, lon1: First point in decimal degrees
        lat2, lon2: Second point in decimal degrees

    Returns:
        Distance in kilometers rounded to 3 decimal places
    """
    R = 6371.0088  # Mean Earth radius in kilometers

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    # Numerical stability check for a > 1.0 due to floating point inaccuracies
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return round(R * c, 3)


def find_nearest_point(
    target_lat: float,
    target_lon: float,
    points: List[Dict[str, Any]],
    lat_key: str = "latitude",
    lon_key: str = "longitude",
    max_distance_km: Optional[float] = None
) -> Tuple[Optional[Dict[str, Any]], Optional[float]]:
    """
    Finds the closest point from a list of dictionaries based on Haversine distance.

    Returns:
        Tuple of (closest_item, distance_km) or (None, None) if no point within max_distance_km.
    """
    best_item = None
    min_dist = float("inf")

    for item in points:
        p_lat = item.get(lat_key)
        p_lon = item.get(lon_key)
        if p_lat is None or p_lon is None:
            continue

        dist = haversine_distance(target_lat, target_lon, float(p_lat), float(p_lon))
        if dist < min_dist:
            min_dist = dist
            best_item = item

    if best_item is not None:
        if max_distance_km is not None and min_dist > max_distance_km:
            return None, min_dist
        return best_item, min_dist

    return None, None
