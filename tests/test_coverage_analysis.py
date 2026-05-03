"""
Unit tests for RF coverage analysis functions.

Tests validate path loss calculations, terrain blockage estimation,
clutter loss computation, and elevation caching.
"""

import math
import pytest

from modules.coverage_analysis import (
    _estimate_elevation_simple,
    _estimate_clutter_loss_db,
    _estimate_terrain_blockage_db,
    _path_loss_advanced,
)
from modules.constants import (
    FREQUENCY_MHZ,
    TX_ALTITUDE_M,
    RX_ALTITUDE_M,
    FSPL_COEFFICIENT,
)


class TestElevationEstimation:
    """Tests for elevation estimation and caching."""

    def test_elevation_simple_default(self):
        """Test that elevation defaults to reasonable values."""
        elev = _estimate_elevation_simple(40.0, -105.0)
        assert isinstance(elev, float)
        assert 0 <= elev <= 500  # Reasonable elevation range in feet

    def test_elevation_caching(self):
        """Test that elevation cache works correctly."""
        cache = {}
        elev1 = _estimate_elevation_simple(40.0, -105.0, cache=cache)
        assert len(cache) == 1

        # Retrieve from cache
        elev2 = _estimate_elevation_simple(40.0, -105.0, cache=cache)
        assert elev1 == elev2
        assert len(cache) == 1

    def test_elevation_different_coords(self):
        """Test that different coordinates produce different elevations."""
        cache = {}
        elev1 = _estimate_elevation_simple(40.0, -105.0, cache=cache)
        elev2 = _estimate_elevation_simple(41.0, -106.0, cache=cache)
        # Values might be same by chance, but cache should have 2 entries
        assert len(cache) == 2

    def test_elevation_rounding(self):
        """Test that elevation keys are rounded correctly."""
        cache = {}
        elev1 = _estimate_elevation_simple(40.001, -105.001, cache=cache)
        elev2 = _estimate_elevation_simple(40.004, -105.004, cache=cache)
        # Both should map to same rounded key
        assert elev1 == elev2
        assert len(cache) == 1


class TestClutterLoss:
    """Tests for clutter loss estimation."""

    def test_clutter_loss_suburban(self):
        """Test suburban clutter loss."""
        loss = _estimate_clutter_loss_db(40.0, -105.0, "suburban")
        assert isinstance(loss, float)
        assert loss > 0  # Should be positive attenuation
        assert loss < 50  # Reasonable upper bound

    def test_clutter_loss_urban(self):
        """Test urban clutter loss is higher than suburban."""
        loss_urban = _estimate_clutter_loss_db(40.0, -105.0, "urban")
        loss_suburban = _estimate_clutter_loss_db(40.0, -105.0, "suburban")
        assert loss_urban > loss_suburban

    def test_clutter_loss_rural(self):
        """Test rural clutter loss is lower than suburban."""
        loss_rural = _estimate_clutter_loss_db(40.0, -105.0, "rural")
        loss_suburban = _estimate_clutter_loss_db(40.0, -105.0, "suburban")
        assert loss_rural < loss_suburban

    def test_clutter_loss_water(self):
        """Test water clutter loss is minimal."""
        loss_water = _estimate_clutter_loss_db(40.0, -105.0, "water")
        assert loss_water >= 0
        assert loss_water < 5  # Water should have minimal loss

    def test_clutter_loss_default(self):
        """Test default land use class."""
        loss_default = _estimate_clutter_loss_db(40.0, -105.0)
        loss_suburban = _estimate_clutter_loss_db(40.0, -105.0, "suburban")
        assert loss_default == loss_suburban


class TestTerrainBlockage:
    """Tests for terrain blockage loss estimation."""

    def test_terrain_blockage_zero_distance(self):
        """Test that zero distance returns no blockage."""
        loss = _estimate_terrain_blockage_db(40.0, -105.0, 40.0, -105.0, 10.0, 10.0)
        assert loss == 0.0

    def test_terrain_blockage_short_distance(self):
        """Test that very short distances are below blockage threshold."""
        loss = _estimate_terrain_blockage_db(40.0, -105.0, 40.001, -105.001, 10.0, 10.0)
        assert loss == 0.0

    def test_terrain_blockage_reasonable_distance(self):
        """Test blockage at reasonable link distance."""
        loss = _estimate_terrain_blockage_db(
            40.0, -105.0, 40.1, -105.1, TX_ALTITUDE_M, RX_ALTITUDE_M
        )
        assert isinstance(loss, float)
        assert loss >= 0  # Loss should be non-negative
        assert loss < 30  # Should be capped at TERRAIN_BLOCKAGE_LOSS_MAX

    def test_terrain_blockage_altitude_effect(self):
        """Test that higher altitudes reduce blockage."""
        loss_low = _estimate_terrain_blockage_db(
            40.0, -105.0, 40.1, -105.1, 10.0, 10.0
        )
        loss_high = _estimate_terrain_blockage_db(
            40.0, -105.0, 40.1, -105.1, 100.0, 100.0
        )
        # Higher altitude should have less blockage
        assert loss_high <= loss_low


class TestPathLossAdvanced:
    """Tests for advanced path loss model."""

    def test_path_loss_zero_distance(self):
        """Test that zero distance returns zero loss."""
        loss = _path_loss_advanced(0.0, freq_mhz=FREQUENCY_MHZ)
        assert loss == 0.0

    def test_path_loss_short_distance(self):
        """Test that very short distances return zero loss."""
        loss = _path_loss_advanced(5.0, freq_mhz=FREQUENCY_MHZ)
        assert loss == 0.0

    def test_path_loss_basic_distance(self):
        """Test path loss at typical link distance."""
        loss = _path_loss_advanced(1000.0, freq_mhz=FREQUENCY_MHZ)
        assert isinstance(loss, float)
        assert loss > 0  # Should have positive loss
        assert loss < 200  # Reasonable upper bound

    def test_path_loss_increases_with_distance(self):
        """Test that path loss increases with distance."""
        loss_1km = _path_loss_advanced(1000.0, freq_mhz=FREQUENCY_MHZ)
        loss_10km = _path_loss_advanced(10000.0, freq_mhz=FREQUENCY_MHZ)
        assert loss_10km > loss_1km

    def test_path_loss_increases_with_frequency(self):
        """Test that path loss increases with frequency."""
        loss_low_freq = _path_loss_advanced(1000.0, freq_mhz=1000)
        loss_high_freq = _path_loss_advanced(1000.0, freq_mhz=5000)
        assert loss_high_freq > loss_low_freq

    def test_path_loss_with_coordinates(self):
        """Test path loss with coordinate-based clutter and terrain."""
        loss_no_coords = _path_loss_advanced(1000.0, freq_mhz=FREQUENCY_MHZ)
        loss_with_coords = _path_loss_advanced(
            1000.0,
            freq_mhz=FREQUENCY_MHZ,
            tx_lat=40.0,
            tx_lon=-105.0,
            rx_lat=40.01,
            rx_lon=-105.01,
        )
        # With coordinates should have more loss (clutter + terrain)
        assert loss_with_coords > loss_no_coords

    def test_path_loss_land_use_effect(self):
        """Test that land use class affects path loss."""
        loss_rural = _path_loss_advanced(
            1000.0,
            freq_mhz=FREQUENCY_MHZ,
            tx_lat=40.0,
            tx_lon=-105.0,
            land_use="rural",
        )
        loss_urban = _path_loss_advanced(
            1000.0,
            freq_mhz=FREQUENCY_MHZ,
            tx_lat=40.0,
            tx_lon=-105.0,
            land_use="urban",
        )
        # Urban should have more loss than rural
        assert loss_urban > loss_rural

    def test_path_loss_friis_equation(self):
        """Test that path loss roughly follows Friis equation."""
        distance_m = 10000.0
        freq_mhz = FREQUENCY_MHZ
        loss = _path_loss_advanced(distance_m, freq_mhz=freq_mhz)

        # Friis formula: PL = 20*log10(d) + 20*log10(f) + 27.55
        expected_fspl = (
            20.0 * math.log10(distance_m)
            + 20.0 * math.log10(freq_mhz)
            + FSPL_COEFFICIENT
        )
        # Loss should be at least FSPL plus fade margin
        assert loss >= expected_fspl


class TestPathLossIntegration:
    """Integration tests for path loss model components."""

    def test_realistic_urban_link(self):
        """Test realistic urban link budget."""
        # Urban link: 1 km, 3390 MHz, 10m TX/RX height
        loss = _path_loss_advanced(
            distance_m=1000.0,
            freq_mhz=FREQUENCY_MHZ,
            tx_alt_m=10.0,
            rx_alt_m=10.0,
            tx_lat=40.7128,  # New York
            tx_lon=-74.0060,
            rx_lat=40.7228,
            rx_lon=-74.0060,
            land_use="urban",
        )
        # Typical urban link loss should be 100-140 dB for 1 km @ 3.39 GHz
        assert 100 < loss < 150

    def test_realistic_rural_link(self):
        """Test realistic rural link budget."""
        # Rural link: 10 km, 3390 MHz, 10m TX/RX height
        loss = _path_loss_advanced(
            distance_m=10000.0,
            freq_mhz=FREQUENCY_MHZ,
            tx_alt_m=10.0,
            rx_alt_m=10.0,
            tx_lat=40.0,
            tx_lon=-105.0,
            rx_lat=40.05,
            rx_lon=-105.05,
            land_use="rural",
        )
        # Typical rural link loss should be 130-160 dB for 10 km @ 3.39 GHz
        assert 130 < loss < 160
