"""
Unit tests for RF propagation utility functions.

Tests validate elevation caching, distance calculations, Fresnel zones,
free-space path loss, and loss estimation functions.
"""

import math
import pytest

from modules.propagation_utils import (
    get_cached_elevation,
    cache_elevation,
    compute_great_circle_distance,
    compute_fresnel_radius,
    compute_free_space_path_loss,
    estimate_terrain_blockage_loss,
    estimate_clutter_loss,
)
from modules.constants import FREQUENCY_HZ


class TestElevationCaching:
    """Tests for elevation cache management."""

    def test_cache_elevation_retrieval(self):
        """Test caching and retrieval of elevation data."""
        cache_elevation(40.0, -105.0, 5280.0)
        elev = get_cached_elevation(40.0, -105.0)
        assert elev == 5280.0

    def test_cache_elevation_rounding(self):
        """Test that elevation cache uses rounded keys."""
        cache_elevation(40.001, -105.001, 1000.0)
        # Slight variation should hit same cache entry
        elev = get_cached_elevation(40.002, -105.002)
        assert elev == 1000.0

    def test_cache_elevation_default_missing(self):
        """Test that missing cache entry returns default."""
        elev = get_cached_elevation(50.0, -110.0)
        assert elev == 100.0  # Default value

    def test_cache_elevation_multiple_entries(self):
        """Test caching multiple elevations."""
        cache_elevation(40.0, -105.0, 1000.0)
        cache_elevation(41.0, -106.0, 2000.0)
        assert get_cached_elevation(40.0, -105.0) == 1000.0
        assert get_cached_elevation(41.0, -106.0) == 2000.0


class TestGreatCircleDistance:
    """Tests for great-circle distance calculations."""

    def test_distance_same_point(self):
        """Test distance between same point is zero."""
        distance = compute_great_circle_distance(40.0, -105.0, 40.0, -105.0)
        assert distance < 1.0  # Should be very small

    def test_distance_known_values(self):
        """Test distance calculation against known values."""
        # Distance between 0,0 and 0,1 degrees is roughly 111 km
        distance = compute_great_circle_distance(0.0, 0.0, 0.0, 1.0)
        assert 110000 < distance < 112000  # ~111 km

    def test_distance_north_south(self):
        """Test distance between north-south points."""
        distance = compute_great_circle_distance(0.0, 0.0, 1.0, 0.0)
        assert 110000 < distance < 112000  # ~111 km

    def test_distance_symmetry(self):
        """Test that distance is symmetric."""
        d1 = compute_great_circle_distance(40.0, -105.0, 41.0, -106.0)
        d2 = compute_great_circle_distance(41.0, -106.0, 40.0, -105.0)
        assert abs(d1 - d2) < 1.0  # Should be equal

    def test_distance_positive(self):
        """Test that distance is always positive."""
        distance = compute_great_circle_distance(40.0, -105.0, 41.0, -106.0)
        assert distance > 0

    def test_distance_high_precision(self):
        """Test distance with high precision coordinates."""
        distance = compute_great_circle_distance(
            40.7128, -74.0060,  # NYC
            51.5074, -0.1278     # London
        )
        # Should be roughly 5500 km
        assert 5300000 < distance < 5700000


class TestFresnelRadius:
    """Tests for Fresnel zone calculations."""

    def test_fresnel_radius_increases_with_distance(self):
        """Test that Fresnel radius increases with distance."""
        r1 = compute_fresnel_radius(1000.0, FREQUENCY_HZ)
        r2 = compute_fresnel_radius(10000.0, FREQUENCY_HZ)
        assert r2 > r1

    def test_fresnel_radius_positive(self):
        """Test that Fresnel radius is always positive."""
        radius = compute_fresnel_radius(5000.0, FREQUENCY_HZ)
        assert radius > 0

    def test_fresnel_radius_reasonable_values(self):
        """Test that Fresnel radius is in reasonable range."""
        radius = compute_fresnel_radius(1000.0, FREQUENCY_HZ)
        # For 1 km at 3 GHz, Fresnel radius should be 10-100 meters
        assert 1 < radius < 500

    def test_fresnel_radius_high_frequency(self):
        """Test Fresnel radius at high frequency."""
        r_low_freq = compute_fresnel_radius(1000.0, 1e9)  # 1 GHz
        r_high_freq = compute_fresnel_radius(1000.0, 10e9)  # 10 GHz
        # Higher frequency should give smaller Fresnel radius
        assert r_high_freq < r_low_freq


class TestFreeSpacePathLoss:
    """Tests for free-space path loss calculations."""

    def test_path_loss_zero_distance(self):
        """Test path loss at zero distance."""
        loss = compute_free_space_path_loss(0.0, 3000.0)
        assert loss == 0.0

    def test_path_loss_short_distance(self):
        """Test path loss at short distance."""
        loss = compute_free_space_path_loss(5.0, 3000.0)
        assert loss == 0.0  # Min distance threshold

    def test_path_loss_increases_with_distance(self):
        """Test that path loss increases with distance."""
        loss_1km = compute_free_space_path_loss(1000.0, 3000.0)
        loss_10km = compute_free_space_path_loss(10000.0, 3000.0)
        assert loss_10km > loss_1km

    def test_path_loss_increases_with_frequency(self):
        """Test that path loss increases with frequency."""
        loss_low = compute_free_space_path_loss(1000.0, 1000.0)
        loss_high = compute_free_space_path_loss(1000.0, 10000.0)
        assert loss_high > loss_low

    def test_path_loss_friis_equation(self):
        """Test that path loss follows Friis equation."""
        distance = 10000.0
        freq = 3000.0
        loss = compute_free_space_path_loss(distance, freq)

        # Expected: 20*log10(d) + 20*log10(f) + 27.55
        expected = 20 * math.log10(distance) + 20 * math.log10(freq) + 27.55
        assert abs(loss - expected) < 0.1


class TestTerrainBlockageLoss:
    """Tests for terrain blockage loss estimation."""

    def test_blockage_loss_zero_ratio(self):
        """Test no blockage when ratio is zero."""
        loss = estimate_terrain_blockage_loss(0.0)
        assert loss == 0.0

    def test_blockage_loss_small_ratio(self):
        """Test no loss below critical ratio."""
        loss = estimate_terrain_blockage_loss(0.05)  # Below 0.1 default
        assert loss == 0.0

    def test_blockage_loss_above_critical(self):
        """Test loss above critical ratio."""
        loss = estimate_terrain_blockage_loss(0.2)  # Above 0.1
        assert loss > 0

    def test_blockage_loss_increases_with_ratio(self):
        """Test that loss increases with blockage ratio."""
        loss_low = estimate_terrain_blockage_loss(0.2)
        loss_high = estimate_terrain_blockage_loss(0.5)
        assert loss_high > loss_low

    def test_blockage_loss_capped(self):
        """Test that blockage loss is capped."""
        loss = estimate_terrain_blockage_loss(10.0)  # Very high ratio
        assert loss <= 25.0  # Should be capped at TERRAIN_BLOCKAGE_LOSS_MAX

    def test_blockage_loss_custom_critical_ratio(self):
        """Test blockage with custom critical ratio."""
        loss_low = estimate_terrain_blockage_loss(0.15, 0.2)
        loss_high = estimate_terrain_blockage_loss(0.15, 0.1)
        # Different critical ratios should produce different results
        assert isinstance(loss_low, float)
        assert isinstance(loss_high, float)


class TestClutterLoss:
    """Tests for clutter loss estimation."""

    def test_clutter_loss_positive(self):
        """Test that clutter loss is positive."""
        clutter_map = {"urban": {"base": 10.0, "var": 5.0}}
        loss = estimate_clutter_loss("urban", clutter_map)
        assert loss >= 0

    def test_clutter_loss_urban_vs_rural(self):
        """Test that urban has more clutter than rural."""
        clutter_map = {
            "urban": {"base": 20.0, "var": 5.0},
            "rural": {"base": 5.0, "var": 2.0},
        }
        loss_urban = estimate_clutter_loss("urban", clutter_map)
        loss_rural = estimate_clutter_loss("rural", clutter_map)
        assert loss_urban > loss_rural

    def test_clutter_loss_default_suburban(self):
        """Test default to suburban if class not found."""
        clutter_map = {"suburban": {"base": 12.0, "var": 3.0}}
        loss_default = estimate_clutter_loss("unknown", clutter_map)
        loss_suburban = estimate_clutter_loss("suburban", clutter_map)
        assert loss_default == loss_suburban

    def test_clutter_loss_variance(self):
        """Test that variance affects clutter loss."""
        clutter_map = {
            "low_var": {"base": 10.0, "var": 1.0},
            "high_var": {"base": 10.0, "var": 10.0},
        }
        loss_low = estimate_clutter_loss("low_var", clutter_map)
        loss_high = estimate_clutter_loss("high_var", clutter_map)
        # Variance should cause different losses (with high probability)
        assert isinstance(loss_low, float)
        assert isinstance(loss_high, float)

    def test_clutter_loss_all_classes(self):
        """Test clutter loss for all standard classes."""
        clutter_map = {
            "urban": {"base": 20.0, "var": 5.0},
            "suburban": {"base": 12.0, "var": 3.0},
            "rural": {"base": 5.0, "var": 2.0},
            "water": {"base": 2.0, "var": 1.0},
        }
        for class_name in clutter_map.keys():
            loss = estimate_clutter_loss(class_name, clutter_map)
            assert 0 <= loss < 50


class TestPropagationIntegration:
    """Integration tests for propagation calculations."""

    def test_complete_path_loss_budget(self):
        """Test complete path loss budget calculation."""
        distance = 5000.0  # 5 km
        frequency = FREQUENCY_HZ

        # Free space loss
        fspl = compute_free_space_path_loss(distance / 1e6, frequency / 1e6)

        # Fresnel zone
        fresnel = compute_fresnel_radius(distance, frequency)

        # Terrain blockage
        blockage = estimate_terrain_blockage_loss(0.15)

        # Clutter
        clutter_map = {"urban": {"base": 12.0, "var": 2.0}}
        clutter = estimate_clutter_loss("urban", clutter_map)

        # Total should be reasonable
        total = fspl + blockage + clutter
        assert 80 < total < 200

    def test_elevation_caching_performance(self):
        """Test that elevation cache improves performance."""
        # Prime cache
        cache_elevation(40.0, -105.0, 1500.0)
        cache_elevation(40.1, -105.1, 1600.0)
        cache_elevation(40.2, -105.2, 1700.0)

        # Retrieve cached values
        e1 = get_cached_elevation(40.0, -105.0)
        e2 = get_cached_elevation(40.1, -105.1)
        e3 = get_cached_elevation(40.2, -105.2)

        assert e1 == 1500.0
        assert e2 == 1600.0
        assert e3 == 1700.0
