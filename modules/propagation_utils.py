"""
RF propagation and path loss calculation utilities.

Provides shared functions for radio propagation modeling, used in station coverage
analysis and link budget calculations.
"""

import math
from typing import Optional


# ─ Cached values for elevation data ────────────────────────────────────────────
_elevation_cache: dict = {}


def get_cached_elevation(lat: float, lon: float) -> float:
    """Get elevation from cache, or compute default estimate.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Elevation in feet
    """
    key = (round(lat, 2), round(lon, 2))
    if key in _elevation_cache:
        return _elevation_cache[key]
    # Default elevation (100 ft)
    return 100.0


def cache_elevation(lat: float, lon: float, elevation_ft: float) -> None:
    """Cache elevation data for a coordinate.

    Args:
        lat: Latitude
        lon: Longitude
        elevation_ft: Elevation in feet
    """
    key = (round(lat, 2), round(lon, 2))
    _elevation_cache[key] = elevation_ft


def compute_great_circle_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Compute great-circle distance between two points.

    Args:
        lat1, lon1: First point (degrees)
        lat2, lon2: Second point (degrees)

    Returns:
        Distance in meters
    """
    lat_dist_m = (lat2 - lat1) * 111000.0  # ~111 km per degree
    lon_dist_m = (lon2 - lon1) * 111000.0 * math.cos(math.radians((lat1 + lat2) / 2.0))
    return math.sqrt(lat_dist_m**2 + lon_dist_m**2)


def compute_fresnel_radius(
    distance_m: float, frequency_hz: float
) -> float:
    """Compute Fresnel zone radius for a distance and frequency.

    Args:
        distance_m: Distance in meters
        frequency_hz: Frequency in Hz

    Returns:
        Fresnel radius in meters
    """
    return math.sqrt(0.5 * 3e8 / frequency_hz * distance_m)


def compute_free_space_path_loss(
    distance_m: float, frequency_mhz: float
) -> float:
    """Compute free-space path loss using Friis equation.

    Formula: PL(dB) = 20*log10(d) + 20*log10(f) + 27.55

    Args:
        distance_m: Distance in meters
        frequency_mhz: Frequency in MHz

    Returns:
        Path loss in dB
    """
    if distance_m < 10:
        return 0.0
    return 20.0 * math.log10(distance_m) + 20.0 * math.log10(frequency_mhz) + 27.55


def estimate_terrain_blockage_loss(
    blockage_ratio: float, terrain_blockage_critical_ratio: float = 0.1
) -> float:
    """Estimate terrain blockage loss using knife-edge diffraction.

    Args:
        blockage_ratio: Ratio of blockage to Fresnel radius
        terrain_blockage_critical_ratio: Threshold ratio for blockage onset

    Returns:
        Loss in dB
    """
    if blockage_ratio <= terrain_blockage_critical_ratio:
        return 0.0
    loss_db = 6.0 * blockage_ratio**2  # ITM-style knife-edge loss
    return min(loss_db, 25.0)  # Cap at 25 dB


def estimate_clutter_loss(land_use_class: str, clutter_map: dict) -> float:
    """Estimate clutter/foliage loss based on land-use classification.

    Args:
        land_use_class: One of "urban", "suburban", "rural", "water"
        clutter_map: Dict mapping class names to {"base": dB, "var": dB}

    Returns:
        Clutter loss in dB
    """
    params = clutter_map.get(land_use_class, clutter_map.get("suburban", {"base": 12.0, "var": 5.0}))
    base = params.get("base", 12.0)
    var = params.get("var", 5.0)
    # Add pseudorandom variation based on coordinates (for deterministic results)
    variation = (abs(lat := params.get("_lat", 0)) * 137.5 % 1.0 +
                 abs(lon := params.get("_lon", 0)) * 173.2 % 1.0) / 2.0 * var
    return base + variation
