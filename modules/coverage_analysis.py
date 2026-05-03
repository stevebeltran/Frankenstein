"""
RF coverage analysis and path loss calculations.

Provides functions for computing radio frequency propagation effects including:
- Free-space path loss (FSPL)
- Terrain blockage and diffraction
- Clutter/foliage loss based on land-use classification
- Elevation estimation with caching
"""

import math
from typing import Dict, Optional, Tuple

from modules.constants import (
    FREQUENCY_HZ,
    FREQUENCY_MHZ,
    FSPL_COEFFICIENT,
    TX_ALTITUDE_M,
    RX_ALTITUDE_M,
    METERS_PER_DEGREE_LATITUDE,
    TERRAIN_BLOCKAGE_CRITICAL_RATIO,
    TERRAIN_BLOCKAGE_LOSS_COEFFICIENT,
    TERRAIN_BLOCKAGE_LOSS_MAX,
    FADE_MARGIN_DB,
    CLUTTER_LOSS,
    MIN_DISTANCE_FOR_TERRAIN_CALC,
    MIN_DISTANCE_FOR_PATH_LOSS,
)


def _estimate_elevation_simple(
    lat: float, lon: float, cache: Optional[Dict[Tuple[float, float], float]] = None
) -> float:
    """Fetch elevation for a point (cached) — fallback to 100 ft if unavailable.

    Uses a simple mock model based on coordinates for deterministic variation
    without requiring external elevation API calls.

    Args:
        lat: Latitude in degrees
        lon: Longitude in degrees
        cache: Optional elevation cache dictionary

    Returns:
        Elevation in feet
    """
    if cache is None:
        cache = {}
    key = (round(lat, 2), round(lon, 2))
    if key in cache:
        return cache[key]
    try:
        # Fallback: use simple rule based on typical coastal vs inland
        elev = max(0, 100 + (lon % 1) * 50 - (lat % 1) * 30)  # Mock variation
    except Exception:
        elev = 100.0  # Default 100 ft mean elevation
    cache[key] = elev
    return elev


def _estimate_clutter_loss_db(
    lat: float, lon: float, land_use_class: str = "suburban"
) -> float:
    """Estimate clutter/foliage/building loss based on land-use class.

    Returns dB added to path loss (positive = attenuation).
    Simplified model; real implementation would use GIS layers.

    Args:
        lat: Transmitter latitude in degrees
        lon: Transmitter longitude in degrees
        land_use_class: One of "urban", "suburban", "rural", "water"

    Returns:
        Clutter loss in dB
    """
    params = CLUTTER_LOSS.get(land_use_class, CLUTTER_LOSS["suburban"])
    # Add small pseudorandom variation based on coordinates
    var = (abs(lat * 137.5) % 1.0 + abs(lon * 173.2) % 1.0) / 2.0 * params["var"]
    return params["base"] + var


def _estimate_terrain_blockage_db(
    tx_lat: float,
    tx_lon: float,
    rx_lat: float,
    rx_lon: float,
    tx_alt_m: float,
    rx_alt_m: float,
) -> float:
    """Estimate terrain blockage loss using simple Fresnel zone calculation.

    If midpoint elevation is significantly above line-of-sight, adds loss
    based on knife-edge diffraction model.

    Args:
        tx_lat: Transmitter latitude in degrees
        tx_lon: Transmitter longitude in degrees
        rx_lat: Receiver latitude in degrees
        rx_lon: Receiver longitude in degrees
        tx_alt_m: Transmitter altitude in meters (above ground)
        rx_alt_m: Receiver altitude in meters (above ground)

    Returns:
        Terrain blockage loss in dB
    """
    try:
        # Midpoint
        mid_lat = (tx_lat + rx_lat) / 2.0
        mid_lon = (tx_lon + rx_lon) / 2.0

        # Distance
        lat_dist_m = (rx_lat - tx_lat) * METERS_PER_DEGREE_LATITUDE
        lon_dist_m = (
            (rx_lon - tx_lon)
            * METERS_PER_DEGREE_LATITUDE
            * math.cos(math.radians((tx_lat + rx_lat) / 2.0))
        )
        horiz_dist = math.sqrt(lat_dist_m**2 + lon_dist_m**2)

        if horiz_dist < MIN_DISTANCE_FOR_TERRAIN_CALC:  # Too close, skip terrain calc
            return 0.0

        # Fresnel radius at midpoint
        freq_hz = FREQUENCY_HZ
        fresnel_r = math.sqrt(0.5 * 3e8 / freq_hz * horiz_dist)

        # Estimate elevations (simple proxy)
        tx_elev = _estimate_elevation_simple(tx_lat, tx_lon)
        rx_elev = _estimate_elevation_simple(rx_lat, rx_lon)
        mid_elev = _estimate_elevation_simple(mid_lat, mid_lon)

        # LOS line from tx to rx
        tx_height = tx_elev + tx_alt_m
        rx_height = rx_elev + rx_alt_m
        los_height_at_mid = (tx_height + rx_height) / 2.0

        # Blockage: if terrain > Fresnel blockage threshold above LOS, add loss
        blockage_m = max(0, mid_elev - los_height_at_mid)
        blockage_ratio = blockage_m / max(1.0, fresnel_r)

        # Knife-edge diffraction approximation
        if blockage_ratio > TERRAIN_BLOCKAGE_CRITICAL_RATIO:
            loss_db = TERRAIN_BLOCKAGE_LOSS_COEFFICIENT * blockage_ratio**2
        else:
            loss_db = 0.0

        return min(TERRAIN_BLOCKAGE_LOSS_MAX, loss_db)
    except Exception:
        return 0.0


def _path_loss_advanced(
    distance_m: float,
    freq_mhz: float = FREQUENCY_MHZ,
    tx_alt_m: float = TX_ALTITUDE_M,
    rx_alt_m: float = RX_ALTITUDE_M,
    tx_lat: Optional[float] = None,
    tx_lon: Optional[float] = None,
    rx_lat: Optional[float] = None,
    rx_lon: Optional[float] = None,
    land_use: str = "suburban",
) -> float:
    """Advanced path loss model combining multiple RF propagation effects.

    Total path loss = FSPL + clutter_loss + terrain_loss + fade_margin

    where:
      - FSPL = free-space path loss using Friis equation
      - clutter_loss = function of land use classification
      - terrain_loss = function of elevation difference and blockage
      - fade_margin = 3 dB multipath fading margin

    Args:
        distance_m: Distance between transmitter and receiver in meters
        freq_mhz: Frequency in MHz (default from constants)
        tx_alt_m: Transmitter altitude in meters above ground
        rx_alt_m: Receiver altitude in meters above ground
        tx_lat: Transmitter latitude in degrees (optional for clutter/terrain)
        tx_lon: Transmitter longitude in degrees (optional for clutter/terrain)
        rx_lat: Receiver latitude in degrees (optional for terrain blockage)
        rx_lon: Receiver longitude in degrees (optional for terrain blockage)
        land_use: Land-use class for clutter loss ("urban", "suburban", "rural", "water")

    Returns:
        Total path loss in dB
    """
    if distance_m < MIN_DISTANCE_FOR_PATH_LOSS:
        return 0.0  # No loss at very short range

    # Free-space path loss
    fspl = 20.0 * math.log10(distance_m) + 20.0 * math.log10(freq_mhz) + FSPL_COEFFICIENT

    # Clutter loss
    clutter_db = (
        _estimate_clutter_loss_db(tx_lat, tx_lon, land_use) if tx_lat else 0.0
    )

    # Terrain/blockage loss (if we have coordinates)
    terrain_db = 0.0
    if tx_lat and tx_lon and rx_lat and rx_lon:
        terrain_db = _estimate_terrain_blockage_db(
            tx_lat, tx_lon, rx_lat, rx_lon, tx_alt_m, rx_alt_m
        )

    # Fade margin (Rayleigh/urban multipath)
    fade_db = FADE_MARGIN_DB

    total_pl = fspl + clutter_db + terrain_db + fade_db
    return total_pl
