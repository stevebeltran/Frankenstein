"""
Unit tests for export handler utilities.

Tests validate DataFrame cleaning and preparation for export.
"""

import pandas as pd
import pytest

from modules.export_handlers import _build_corrected_export_from_merged_fallback


class TestBuildCorrectedExport:
    """Tests for DataFrame export preparation."""

    def test_export_none_input(self):
        """Test that None input returns empty DataFrame."""
        result = _build_corrected_export_from_merged_fallback(None)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_export_removes_merge_columns(self):
        """Test that temporary merge columns are removed."""
        df = pd.DataFrame({
            'lat': [40.0, 41.0],
            'lon': [-105.0, -106.0],
            '_census_merge_key': ['key1', 'key2'],
            '_census_filled': [False, True],
            'name': ['A', 'B'],
        })
        result = _build_corrected_export_from_merged_fallback(df)
        assert '_census_merge_key' not in result.columns
        assert '_census_filled' not in result.columns
        assert 'lat' in result.columns
        assert 'lon' in result.columns
        assert 'name' in result.columns

    def test_export_preserves_data_rows(self):
        """Test that data rows are preserved."""
        df = pd.DataFrame({
            'lat': [40.0, 41.0, 42.0],
            'lon': [-105.0, -106.0, -107.0],
            'name': ['A', 'B', 'C'],
        })
        result = _build_corrected_export_from_merged_fallback(df)
        assert len(result) == 3
        assert list(result['name']) == ['A', 'B', 'C']

    def test_export_numeric_lat_lon(self):
        """Test that lat/lon are converted to numeric."""
        df = pd.DataFrame({
            'lat': ['40.0', '41.0', 'invalid'],
            'lon': ['-105.0', '-106.0', '-107.0'],
            'name': ['A', 'B', 'C'],
        })
        result = _build_corrected_export_from_merged_fallback(df)
        assert pd.api.types.is_numeric_dtype(result['lat'])
        assert pd.api.types.is_numeric_dtype(result['lon'])
        # Invalid value should be NaN
        assert pd.isna(result.loc[2, 'lat'])

    def test_export_missing_columns_ignored(self):
        """Test that missing columns don't cause errors."""
        df = pd.DataFrame({
            'name': ['A', 'B'],
            'value': [1, 2],
        })
        # Should not raise error even though lat/lon are missing
        result = _build_corrected_export_from_merged_fallback(df)
        assert len(result) == 2
        assert 'name' in result.columns

    def test_export_resets_index(self):
        """Test that index is reset."""
        df = pd.DataFrame({
            'lat': [40.0, 41.0],
            'lon': [-105.0, -106.0],
        }, index=[10, 20])
        result = _build_corrected_export_from_merged_fallback(df)
        assert list(result.index) == [0, 1]

    def test_export_copies_dataframe(self):
        """Test that the result is a copy, not reference."""
        df = pd.DataFrame({
            'lat': [40.0, 41.0],
            'lon': [-105.0, -106.0],
        })
        result = _build_corrected_export_from_merged_fallback(df)
        # Modify result
        result.loc[0, 'lat'] = 99.0
        # Original should be unchanged
        assert df.loc[0, 'lat'] == 40.0

    def test_export_with_extra_columns(self):
        """Test that extra columns are preserved."""
        df = pd.DataFrame({
            'lat': [40.0],
            'lon': [-105.0],
            '_census_merge_key': ['key1'],
            'incidents': [5],
            'population': [10000],
        })
        result = _build_corrected_export_from_merged_fallback(df)
        assert '_census_merge_key' not in result.columns
        assert 'incidents' in result.columns
        assert 'population' in result.columns
        assert result.loc[0, 'incidents'] == 5


class TestExportIntegration:
    """Integration tests for export workflows."""

    def test_typical_merged_dataframe(self):
        """Test with typical merged call+census dataframe."""
        df = pd.DataFrame({
            'lat': [40.0, 40.5, 41.0],
            'lon': [-105.0, -105.5, -106.0],
            'incident_id': [1, 2, 3],
            'census_block': ['block1', 'block2', 'block3'],
            'population': [100, 200, 150],
            '_census_merge_key': ['key1', 'key2', 'key3'],
            '_census_filled': [False, True, False],
        })
        result = _build_corrected_export_from_merged_fallback(df)
        assert len(result) == 3
        assert list(result.columns) == ['lat', 'lon', 'incident_id', 'census_block', 'population']
        assert pd.api.types.is_numeric_dtype(result['lat'])
        assert pd.api.types.is_numeric_dtype(result['lon'])

    def test_export_with_missing_values(self):
        """Test export with missing values in various columns."""
        df = pd.DataFrame({
            'lat': [40.0, None, 41.0],
            'lon': [-105.0, -105.5, None],
            'incident_id': [1, 2, 3],
            '_census_merge_key': ['key1', 'key2', 'key3'],
        })
        result = _build_corrected_export_from_merged_fallback(df)
        assert len(result) == 3
        assert pd.isna(result.loc[1, 'lat'])
        assert pd.isna(result.loc[2, 'lon'])
