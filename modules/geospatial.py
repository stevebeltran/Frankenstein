"""Geospatial utilities - boundaries, geocoding, station generation."""

import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon, MultiPolygon, box
from shapely.ops import unary_union
from pathlib import Path
import os, glob, json, re, zipfile, io, math, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
import tempfile

from modules.config import STATE_FIPS, US_STATES_ABBR, KNOWN_POPULATIONS


def _load_uploaded_boundary_overlay(uploaded_file):
    """Load a boundary GeoDataFrame from an uploaded shapefile ZIP."""
    # This is a placeholder - the actual implementation should be restored from original code
    return None


def _boundary_overlay_status(boundary_geom_4326, overlay_gdf, epsg_code):
    """Check overlay status of a boundary geometry with another GeoDataFrame."""
    if boundary_geom_4326 is None or boundary_geom_4326.is_empty or overlay_gdf is None or overlay_gdf.empty:
        return None
    try:
        _overlay_utm = overlay_gdf.to_crs(epsg=epsg_code)
        _overlay_union = (_overlay_utm.geometry.union_all() if hasattr(_overlay_utm.geometry, 'union_all') else _overlay_utm.geometry.unary_union)
        _boundary_utm = gpd.GeoSeries([boundary_geom_4326], crs='EPSG:4326').to_crs(epsg=epsg_code).iloc[0]
        if _overlay_union.is_empty or _boundary_utm.is_empty:
            return None
        _inter = _overlay_union.intersection(_boundary_utm)
        _overlay_area = float(_overlay_union.area or 0)
        _boundary_area = float(_boundary_utm.area or 0)
        _inter_area = float(_inter.area or 0)
        if _overlay_area <= 0 or _boundary_area <= 0:
            return None
        _pct_overlay_inside = max(0.0, min(100.0, _inter_area / _overlay_area * 100.0))
        _pct_boundary_covered = max(0.0, min(100.0, _inter_area / _boundary_area * 100.0))
        if _inter_area <= 0:
            _status = 'no_overlap'
        elif _pct_overlay_inside >= 95:
            _status = 'inside'
        elif _pct_boundary_covered >= 95:
            _status = 'contains'
        else:
            _status = 'partial'
        return {'status': _status, 'pct_inside': _pct_overlay_inside, 'pct_covered': _pct_boundary_covered}
    except Exception:
        return None


def _count_points_within_boundary(df_calls, boundary_geom_4326):
    """Count calls (points) that fall within a boundary polygon."""
    if df_calls is None or df_calls.empty or boundary_geom_4326 is None:
        return 0
    try:
        _pts = gpd.GeoSeries([Point(row['lon'], row['lat']) for _, row in df_calls.iterrows()], crs='EPSG:4326')
        _cnt = sum(_pts.within(boundary_geom_4326))
        return int(_cnt)
    except Exception:
        return 0


def find_jurisdictions_by_coordinates(df_calls_full, center_lat, center_lon, search_radius_mi=2.0, state_abbr=None):
    """Find jurisdictions (cities/counties) containing calls within a radius of center point."""
    # This is a placeholder - the actual implementation is complex and should be restored from original code
    return None


def build_display_calls(df_calls, max_points=5000, seed=42):
    """Sample/filter calls for display on map."""
    if df_calls is None or df_calls.empty:
        return df_calls
    if len(df_calls) <= max_points:
        return df_calls
    return df_calls.sample(min(max_points, len(df_calls)), random_state=seed)


def get_address_from_latlon(lat, lon):
    """Get a human-readable address from lat/lon coordinates."""
    try:
        # Simple reverse geocoding fallback
        return f"{lat:.4f}, {lon:.4f}"
    except Exception:
        return None
