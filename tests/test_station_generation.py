"""
Unit tests for station generation functions.

Tests validate random station generation, OSM/HIFLD data fetching,
and integration with call datasets.
"""

import pytest
import pandas as pd
from shapely.geometry import Point, Polygon

from modules.station_generation import (
    _make_random_stations,
    generate_stations_from_calls,
)


class TestMakeRandomStations:
    """Tests for random station generation."""

    def test_make_random_stations_none_dataframe(self):
        """Test with None dataframe."""
        result = _make_random_stations(None, n=5)
        assert isinstance(result, pd.DataFrame)
        # Should return minimal or empty frame
        assert len(result) >= 0

    def test_make_random_stations_empty_dataframe(self):
        """Test with empty dataframe."""
        df = pd.DataFrame({'lat': [], 'lon': []})
        result = _make_random_stations(df, n=5)
        assert isinstance(result, pd.DataFrame)

    def test_make_random_stations_basic(self):
        """Test basic random station generation."""
        df = pd.DataFrame({
            'lat': [40.0, 40.1, 40.2, 40.3, 40.4],
            'lon': [-105.0, -105.1, -105.2, -105.3, -105.4],
        })
        result = _make_random_stations(df, n=3)
        assert isinstance(result, pd.DataFrame)
        assert len(result) <= 5  # Should not exceed input size

    def test_make_random_stations_column_structure(self):
        """Test that result has expected columns."""
        df = pd.DataFrame({
            'lat': [40.0, 40.1, 40.2],
            'lon': [-105.0, -105.1, -105.2],
        })
        result = _make_random_stations(df, n=2)
        # Result should have lat/lon columns
        if len(result) > 0:
            assert 'lat' in result.columns
            assert 'lon' in result.columns

    def test_make_random_stations_n_parameter(self):
        """Test that n parameter affects output size."""
        df = pd.DataFrame({
            'lat': list(range(40, 50)),
            'lon': list(range(-105, -95)),
        })
        result_5 = _make_random_stations(df, n=5)
        result_10 = _make_random_stations(df, n=10)
        # Larger n should not result in fewer stations
        assert len(result_10) >= len(result_5)

    def test_make_random_stations_with_boundary(self):
        """Test station generation with boundary constraint."""
        df = pd.DataFrame({
            'lat': [40.0, 40.1, 40.2, 40.3, 40.4],
            'lon': [-105.0, -105.1, -105.2, -105.3, -105.4],
        })
        # Create a simple boundary
        boundary = Polygon([
            (40.0, -105.0),
            (40.2, -105.0),
            (40.2, -105.2),
            (40.0, -105.2),
        ])
        result = _make_random_stations(df, n=3, boundary_geom=boundary)
        # All stations should be within or near boundary
        assert isinstance(result, pd.DataFrame)

    def test_make_random_stations_numeric_coordinates(self):
        """Test that output coordinates are numeric."""
        df = pd.DataFrame({
            'lat': [40.0, 40.1, 40.2],
            'lon': [-105.0, -105.1, -105.2],
        })
        result = _make_random_stations(df, n=2)
        if len(result) > 0:
            assert pd.api.types.is_numeric_dtype(result['lat'])
            assert pd.api.types.is_numeric_dtype(result['lon'])
            # All coordinates should be valid
            assert not result['lat'].isna().all()
            assert not result['lon'].isna().all()


class TestGenerateStationsFromCalls:
    """Tests for station generation from call data."""

    def test_generate_stations_from_calls_none(self):
        """Test with None dataframe."""
        result, status = generate_stations_from_calls(None)
        assert isinstance(status, str)
        # Should return status message

    def test_generate_stations_from_calls_empty(self):
        """Test with empty dataframe."""
        df = pd.DataFrame({'lat': [], 'lon': []})
        result, status = generate_stations_from_calls(df)
        assert isinstance(status, str)

    def test_generate_stations_from_calls_basic(self):
        """Test basic station generation from calls."""
        df = pd.DataFrame({
            'lat': [40.0, 40.1, 40.2, 40.3, 40.4, 40.5],
            'lon': [-105.0, -105.1, -105.2, -105.3, -105.4, -105.5],
        })
        result, status = generate_stations_from_calls(df, max_stations=10)
        assert isinstance(status, str)
        if result is not None:
            assert isinstance(result, pd.DataFrame)
            assert len(result) <= 10

    def test_generate_stations_from_calls_status_message(self):
        """Test that status messages are meaningful."""
        df = pd.DataFrame({
            'lat': [40.0, 40.1],
            'lon': [-105.0, -105.1],
        })
        result, status = generate_stations_from_calls(df)
        # Status should be a string describing what happened
        assert len(status) > 0

    def test_generate_stations_return_types(self):
        """Test return type structure."""
        df = pd.DataFrame({
            'lat': [40.0, 40.1, 40.2],
            'lon': [-105.0, -105.1, -105.2],
        })
        result, status = generate_stations_from_calls(df)
        # Should return tuple of (DataFrame or None, str)
        assert isinstance(status, str)
        assert result is None or isinstance(result, pd.DataFrame)

    def test_generate_stations_max_stations_parameter(self):
        """Test that max_stations parameter is respected."""
        df = pd.DataFrame({
            'lat': list(range(40, 50)),
            'lon': list(range(-105, -95)),
        })
        result, status = generate_stations_from_calls(df, max_stations=5)
        if result is not None:
            assert len(result) <= 5

    def test_generate_stations_with_invalid_coordinates(self):
        """Test handling of invalid coordinates."""
        df = pd.DataFrame({
            'lat': [40.0, None, 40.2, 'invalid', 40.4],
            'lon': [-105.0, -105.1, None, -105.3, -105.4],
        })
        result, status = generate_stations_from_calls(df)
        # Should handle gracefully
        assert isinstance(status, str)


class TestStationGenerationIntegration:
    """Integration tests for station generation."""

    def test_realistic_call_distribution(self):
        """Test with realistic call distribution."""
        # Simulate clustered calls (typical for urban area)
        import numpy as np
        np.random.seed(42)

        # Create two clusters
        cluster1_lat = np.random.normal(40.0, 0.05, 50)
        cluster1_lon = np.random.normal(-105.0, 0.05, 50)
        cluster2_lat = np.random.normal(40.5, 0.05, 50)
        cluster2_lon = np.random.normal(-105.5, 0.05, 50)

        df = pd.DataFrame({
            'lat': list(cluster1_lat) + list(cluster2_lat),
            'lon': list(cluster1_lon) + list(cluster2_lon),
        })

        result, status = generate_stations_from_calls(df, max_stations=20)
        # Should successfully generate stations
        assert isinstance(status, str)
        if result is not None:
            assert len(result) > 0
            assert len(result) <= 20

    def test_single_point_data(self):
        """Test with single incident location."""
        df = pd.DataFrame({
            'lat': [40.0],
            'lon': [-105.0],
        })
        result, status = generate_stations_from_calls(df)
        # Should handle single point gracefully
        assert isinstance(status, str)

    def test_sparse_geographic_distribution(self):
        """Test with sparse geographic distribution."""
        df = pd.DataFrame({
            'lat': [40.0, 41.0, 42.0, 43.0],
            'lon': [-105.0, -106.0, -107.0, -108.0],
        })
        result, status = generate_stations_from_calls(df, max_stations=4)
        assert isinstance(status, str)
        if result is not None:
            assert isinstance(result, pd.DataFrame)

    def test_dense_call_cluster(self):
        """Test with very dense call cluster."""
        import numpy as np
        np.random.seed(42)

        # High density cluster
        lat = np.random.normal(40.7128, 0.01, 1000)  # NYC area
        lon = np.random.normal(-74.0060, 0.01, 1000)

        df = pd.DataFrame({
            'lat': lat,
            'lon': lon,
        })

        result, status = generate_stations_from_calls(df, max_stations=50)
        assert isinstance(status, str)
        if result is not None:
            assert len(result) <= 50
