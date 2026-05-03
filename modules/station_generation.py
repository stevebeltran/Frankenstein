"""
Station generation and optimization for drone deployment.

Provides multiple strategies for placing ground stations:
1. OpenStreetMap (OSM) facility detection
2. HIFLD federal facility database
3. Call-density hotspot clustering (fallback)

All approaches are designed to maximize call coverage and response efficiency.
"""

import concurrent.futures as cf
import json
import math
from typing import List, Optional, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
import streamlit as st
import urllib.parse
import urllib.request

from modules.constants import (
    API_TIMEOUT_DEFAULT,
    API_TIMEOUT_STANDARD,
    CONCURRENT_REQUEST_TIMEOUT,
    COORDINATE_PRECISION,
    OSM_MAX_STATIONS,
    OSM_SEARCH_RADIUS_LARGE,
    OSM_SEARCH_RADIUS_SMALL,
    OVERPASS_TIMEOUT,
    SKLEARN_BATCH_SIZE,
    SKLEARN_N_INIT,
    SKLEARN_RANDOM_STATE,
)


def _make_random_stations(
    df_calls: pd.DataFrame,
    n: int = 40,
    boundary_geom: Optional[object] = None,
    epsg_code: Optional[int] = None,
) -> pd.DataFrame:
    """Fallback station generator based on call-density hotspots.

    If a city boundary is supplied, only incidents inside that boundary are used and
    final station coordinates are snapped to the nearest in-boundary incident so every
    suggested site remains inside the geographic area.

    Args:
        df_calls: DataFrame with lat/lon columns representing call locations
        n: Number of stations to generate (default 40)
        boundary_geom: Optional boundary polygon to constrain stations
        epsg_code: Optional EPSG projection code for boundary

    Returns:
        DataFrame with columns: name, lat, lon, type
    """
    if df_calls is None or df_calls.empty:
        return pd.DataFrame()

    work = df_calls.copy()
    work["lat"] = pd.to_numeric(work["lat"], errors="coerce")
    work["lon"] = pd.to_numeric(work["lon"], errors="coerce")
    work = work.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    if work.empty:
        return pd.DataFrame()

    # Filter to boundary if provided
    if boundary_geom is not None and epsg_code is not None:
        try:
            work_gdf = gpd.GeoDataFrame(
                work,
                geometry=gpd.points_from_xy(work.lon, work.lat),
                crs="EPSG:4326",
            ).to_crs(epsg=int(epsg_code))
            inside_mask = work_gdf.within(boundary_geom)
            if inside_mask.any():
                work = work.loc[inside_mask.values].reset_index(drop=True)
        except Exception:
            pass
        if work.empty:
            return pd.DataFrame()

    lats = work["lat"].dropna().values
    lons = work["lon"].dropna().values
    if len(lats) == 0:
        return pd.DataFrame()

    # Remove outliers using IQR method
    q1_la, q3_la = np.percentile(lats, 5), np.percentile(lats, 95)
    q1_lo, q3_lo = np.percentile(lons, 5), np.percentile(lons, 95)
    iqr_la, iqr_lo = q3_la - q1_la, q3_lo - q1_lo
    buf_la, buf_lo = max(iqr_la * 0.5, 0.01), max(iqr_lo * 0.5, 0.01)
    mask = (
        (lats >= q1_la - buf_la)
        & (lats <= q3_la + buf_la)
        & (lons >= q1_lo - buf_lo)
        & (lons <= q3_lo + buf_lo)
    )
    clean_lats, clean_lons = lats[mask], lons[mask]
    if len(clean_lats) == 0:
        clean_lats, clean_lons = lats, lons

    base_coords = np.column_stack([clean_lats, clean_lons])
    if len(base_coords) == 0:
        return pd.DataFrame()

    # Cluster using KMeans or random sampling
    try:
        from sklearn.cluster import MiniBatchKMeans as _KM

        k = min(n, len(base_coords))
        km = _KM(
            n_clusters=k,
            random_state=SKLEARN_RANDOM_STATE,
            batch_size=SKLEARN_BATCH_SIZE,
            n_init=SKLEARN_N_INIT,
        )
        km.fit(base_coords)
        centroids = km.cluster_centers_
    except Exception:
        np.random.seed(SKLEARN_RANDOM_STATE)
        idx = np.random.choice(
            len(base_coords), min(n, len(base_coords)), replace=False
        )
        centroids = base_coords[idx]

    # Snap every centroid to nearest actual call
    snapped = []
    for cen_lat, cen_lon in centroids:
        d2 = (base_coords[:, 0] - cen_lat) ** 2 + (base_coords[:, 1] - cen_lon) ** 2
        nearest = base_coords[int(np.argmin(d2))]
        snapped.append((float(nearest[0]), float(nearest[1])))

    if not snapped:
        return pd.DataFrame()

    deduped = list(
        dict.fromkeys(
            (round(lat, COORDINATE_PRECISION), round(lon, COORDINATE_PRECISION))
            for lat, lon in snapped
        )
    )
    station_lats = np.array([lat for lat, _ in deduped])
    station_lons = np.array([lon for _, lon in deduped])

    k_actual = len(station_lats)
    types = (
        ["Police"] * max(1, math.ceil(k_actual * 0.5))
        + ["Fire"] * max(1, math.ceil(k_actual * 0.3))
        + ["School"] * max(1, math.ceil(k_actual * 0.2))
    )[: k_actual]
    return pd.DataFrame(
        {
            "name": [f"{types[i]} Station {i+1}" for i in range(k_actual)],
            "lat": station_lats,
            "lon": station_lons,
            "type": types,
        }
    )


@st.cache_data(show_spinner=False)
def _fetch_osm_stations_cached(
    cen_lat_r: float,
    cen_lon_r: float,
    max_stations: int = OSM_MAX_STATIONS,
    bbox_min_lat: Optional[float] = None,
    bbox_min_lon: Optional[float] = None,
    bbox_max_lat: Optional[float] = None,
    bbox_max_lon: Optional[float] = None,
) -> Tuple[Optional[List[dict]], str]:
    """Cache-friendly OSM query keyed on rounded centroid (2 dp ≈ 1 km grid).

    All three Overpass mirrors are queried in parallel — total wait = fastest mirror,
    not sum of all mirrors. When explicit bbox bounds are provided they are used
    instead of the fixed radii so the search covers the entire city/jurisdiction.

    Args:
        cen_lat_r: Rounded centroid latitude
        cen_lon_r: Rounded centroid longitude
        max_stations: Maximum stations to return (default 200)
        bbox_min_lat, bbox_min_lon, bbox_max_lat, bbox_max_lon: Optional explicit bbox

    Returns:
        Tuple of (list_of_station_dicts or None, status_message_str)
    """
    osm_urls = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.openstreetmap.ru/api/interpreter",
    ]

    def _try_mirror(url: str, query: str) -> Optional[dict]:
        try:
            req = urllib.request.Request(
                f"{url}?data={urllib.parse.quote(query)}",
                headers={"User-Agent": "BRINC_COS_Optimizer/1.0"},
            )
            with urllib.request.urlopen(req, timeout=API_TIMEOUT_STANDARD) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

    # When explicit bounds are provided, use a single pass with the full bbox;
    # otherwise fall back to the expanding-radius approach.
    if bbox_min_lat is not None:
        _radii = [None]  # single pass using explicit bounds
    else:
        _radii = [OSM_SEARCH_RADIUS_SMALL, OSM_SEARCH_RADIUS_LARGE]

    for R in _radii:
        if R is None:
            bbox = f"{bbox_min_lat},{bbox_min_lon},{bbox_max_lat},{bbox_max_lon}"
        else:
            bbox = (
                f"{cen_lat_r - R},{cen_lon_r - R},{cen_lat_r + R},{cen_lon_r + R}"
            )
        query = (
            f"[out:json][timeout:{int(OVERPASS_TIMEOUT)}];"
            f'(node["amenity"="fire_station"]({bbox});'
            f'node["amenity"="police"]({bbox});'
            f'node["amenity"="school"]({bbox});'
            f'node["amenity"="hospital"]({bbox});'
            f'node["amenity"="library"]({bbox});'
            f'node["building"="government"]({bbox});'
            f'node["amenity"="ambulance_station"]({bbox});'
            f'node["amenity"="university"]({bbox});'
            f'node["amenity"="college"]({bbox});'
            f'node["amenity"="bus_station"]({bbox});'
            f'node["railway"="station"]({bbox});'
            f'node["amenity"="community_centre"]({bbox});'
            f'node["amenity"="courthouse"]({bbox});'
            f'node["amenity"="social_facility"]({bbox});'
            f'way["amenity"="fire_station"]({bbox});'
            f'way["amenity"="police"]({bbox});'
            f'way["amenity"="school"]({bbox});'
            f'way["amenity"="hospital"]({bbox});'
            f'way["amenity"="library"]({bbox});'
            f'way["building"="government"]({bbox});'
            f'way["amenity"="ambulance_station"]({bbox});'
            f'way["amenity"="university"]({bbox});'
            f'way["amenity"="college"]({bbox});'
            f'way["amenity"="bus_station"]({bbox});'
            f'way["railway"="station"]({bbox});'
            f'way["amenity"="community_centre"]({bbox});'
            f'way["amenity"="courthouse"]({bbox});'
            f'way["amenity"="social_facility"]({bbox});'
            f");out center;"
        )

        # Fire all three mirrors in parallel — first successful response wins
        data = None
        _pool = cf.ThreadPoolExecutor(max_workers=3)
        try:
            futs = {_pool.submit(_try_mirror, url, query): url for url in osm_urls}
            for fut in cf.as_completed(futs):
                result = fut.result()
                if result is not None:
                    data = result
                    break
        finally:
            _pool.shutdown(wait=False, cancel_futures=True)

        if data is None:
            continue

        rows = []
        for el in data.get("elements", []):
            tags = el.get("tags", {})
            lat = el.get("lat") or (el.get("center") or {}).get("lat")
            lon = el.get("lon") or (el.get("center") or {}).get("lon")
            if lat is None or lon is None:
                continue
            amenity = tags.get("amenity", "")
            building = tags.get("building", "")
            railway = tags.get("railway", "")
            type_label = (
                "Fire"
                if amenity == "fire_station"
                else (
                    "Police"
                    if amenity == "police"
                    else (
                        "Hospital"
                        if amenity == "hospital"
                        else (
                            "Library"
                            if amenity == "library"
                            else (
                                "EMS"
                                if amenity == "ambulance_station"
                                else (
                                    "University"
                                    if amenity in ("university", "college")
                                    else (
                                        "Transit"
                                        if amenity == "bus_station"
                                        or railway == "station"
                                        else (
                                            "Community"
                                            if amenity == "community_centre"
                                            else (
                                                "Courthouse"
                                                if amenity == "courthouse"
                                                else (
                                                    "Social Services"
                                                    if amenity == "social_facility"
                                                    else (
                                                        "Government"
                                                        if building == "government"
                                                        else "School"
                                                    )
                                                )
                                            )
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            )
            rows.append(
                {
                    "name": tags.get("name", f"{type_label} Station"),
                    "lat": round(lat, COORDINATE_PRECISION),
                    "lon": round(lon, COORDINATE_PRECISION),
                    "type": type_label,
                }
            )

        if rows:
            df_s = (
                pd.DataFrame(rows)
                .drop_duplicates(subset=["lat", "lon"])
                .reset_index(drop=True)
            )
            counts, new_names = {}, []
            for n in df_s["name"]:
                if n in counts:
                    counts[n] += 1
                    new_names.append(f"{n} ({counts[n]})")
                else:
                    counts[n] = 0
                    new_names.append(n)
            df_s["name"] = new_names
            if len(df_s) > max_stations:
                pri = {
                    "Police": 0,
                    "Fire": 1,
                    "EMS": 2,
                    "School": 3,
                    "Hospital": 4,
                    "University": 5,
                    "Transit": 6,
                    "Courthouse": 7,
                    "Community": 8,
                    "Government": 9,
                    "Social Services": 10,
                    "Library": 11,
                }
                df_s["_pri"] = df_s["type"].map(pri).fillna(3)
                df_s = (
                    df_s.sort_values("_pri")
                    .head(max_stations)
                    .drop(columns="_pri")
                    .reset_index(drop=True)
                )
            return df_s.to_dict("records"), f"Found {len(df_s)} stations from OpenStreetMap."

    return None, "OSM unavailable"


@st.cache_data(show_spinner=False)
def _fetch_hifld_stations_cached(
    min_lat: float, min_lon: float, max_lat: float, max_lon: float
) -> Tuple[Optional[List[dict]], str]:
    """Fetch fire stations and law enforcement from HIFLD (US Federal open data).

    Fire and Police endpoints are queried in parallel to halve wait time.
    HIFLD endpoints are ArcGIS FeatureServer REST services maintained by DHS.

    Args:
        min_lat, min_lon, max_lat, max_lon: Bounding box coordinates

    Returns:
        Tuple of (list_of_station_dicts or None, status_message_str)
    """
    _HIFLD_SOURCES = [
        (
            "https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/Fire_Stations/FeatureServer/0/query",
            "Fire",
            "NAME",
        ),
        (
            "https://services1.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/USA_Law_Enforcement_Locations/FeatureServer/0/query",
            "Police",
            "NAME",
        ),
    ]
    bbox_str = f"{min_lon},{min_lat},{max_lon},{max_lat}"

    def _fetch_one(url: str, type_label: str, name_field: str) -> List[dict]:
        try:
            params = urllib.parse.urlencode(
                {
                    "where": "1=1",
                    "geometry": bbox_str,
                    "geometryType": "esriGeometryEnvelope",
                    "inSR": "4326",
                    "spatialRel": "esriSpatialRelIntersects",
                    "outFields": f"{name_field},CITY,STATE",
                    "outSR": "4326",
                    "f": "json",
                    "resultRecordCount": 500,
                }
            )
            req = urllib.request.Request(
                f"{url}?{params}",
                headers={"User-Agent": "BRINC_COS_Optimizer/1.0"},
            )
            with urllib.request.urlopen(req, timeout=API_TIMEOUT_DEFAULT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            rows = []
            for feat in data.get("features", []):
                geom = feat.get("geometry", {})
                attrs = feat.get("attributes", {})
                lat = geom.get("y")
                lon = geom.get("x")
                if lat is None or lon is None:
                    continue
                name = (attrs.get(name_field) or "").strip() or f"{type_label} Station"
                rows.append(
                    {
                        "name": name,
                        "lat": round(float(lat), COORDINATE_PRECISION),
                        "lon": round(float(lon), COORDINATE_PRECISION),
                        "type": type_label,
                    }
                )
            return rows
        except Exception:
            return []

    # Fetch fire + police in parallel — total wait = max(fire, police), not sum
    all_rows = []
    _pool = cf.ThreadPoolExecutor(max_workers=2)
    try:
        futs = [
            _pool.submit(_fetch_one, url, lbl, fld) for url, lbl, fld in _HIFLD_SOURCES
        ]
        for fut in cf.as_completed(futs):
            all_rows.extend(fut.result())
    finally:
        _pool.shutdown(wait=False, cancel_futures=True)

    if all_rows:
        return all_rows, f"Found {len(all_rows)} stations from HIFLD (US Federal)."
    return None, "HIFLD unavailable"


def generate_stations_from_calls(
    df_calls: pd.DataFrame, max_stations: int = 100
) -> Tuple[Optional[pd.DataFrame], str]:
    """Query OSM and HIFLD in parallel; merge results; fall back to call density.

    Attempts to find real-world facilities from OpenStreetMap and HIFLD federal
    databases, then merges the results. If both sources fail or return no results,
    falls back to generating synthetic stations based on call density clustering.

    Args:
        df_calls: DataFrame with lat/lon columns from parsed CAD data
        max_stations: Maximum number of stations to return (default 100)

    Returns:
        Tuple of (DataFrame with station locations or None, status_message_str)
    """
    lats = df_calls["lat"].dropna().values
    lons = df_calls["lon"].dropna().values
    if len(lats) == 0:
        return None, "No coordinates available to generate stations."

    # Compute centroid and bbox from call data
    q1_la, q3_la = np.percentile(lats, 25), np.percentile(lats, 75)
    q1_lo, q3_lo = np.percentile(lons, 25), np.percentile(lons, 75)
    iqr_la, iqr_lo = q3_la - q1_la, q3_lo - q1_lo
    mask = (
        (lats >= q1_la - 2.5 * iqr_la)
        & (lats <= q3_la + 2.5 * iqr_la)
        & (lons >= q1_lo - 2.5 * iqr_lo)
        & (lons <= q3_lo + 2.5 * iqr_lo)
    )
    if not np.any(mask):
        mask = np.ones(len(lats), dtype=bool)
    cen_lat_r = round(float(lats[mask].mean()), 2)
    cen_lon_r = round(float(lons[mask].mean()), 2)

    # Derive bbox from actual data spread
    _pad = 0.05  # small buffer (~5.5 km) beyond outermost calls
    min_lat_r = round(float(lats[mask].min()) - _pad, 2)
    max_lat_r = round(float(lats[mask].max()) + _pad, 2)
    min_lon_r = round(float(lons[mask].min()) - _pad, 2)
    max_lon_r = round(float(lons[mask].max()) + _pad, 2)

    osm_rows, osm_note = None, "OSM unavailable"
    hifld_rows, hifld_note = None, "HIFLD unavailable"

    pool = cf.ThreadPoolExecutor(max_workers=2)
    try:
        futures = {
            "OSM": pool.submit(
                _fetch_osm_stations_cached,
                cen_lat_r,
                cen_lon_r,
                max_stations,
                min_lat_r,
                min_lon_r,
                max_lat_r,
                max_lon_r,
            ),
            "HIFLD": pool.submit(
                _fetch_hifld_stations_cached, min_lat_r, min_lon_r, max_lat_r, max_lon_r
            ),
        }
        _, not_done = cf.wait(futures.values(), timeout=CONCURRENT_REQUEST_TIMEOUT)

        for name, fut in futures.items():
            if fut in not_done:
                fut.cancel()
                print(f"[BRINC] generate_stations_from_calls: {name} timed out")
                continue
            try:
                rows, note = fut.result()
            except Exception as e:
                rows, note = None, f"{name} unavailable"
                print(f"[BRINC] generate_stations_from_calls: {name} raised {e}")
            if name == "OSM":
                osm_rows, osm_note = rows, note
            else:
                hifld_rows, hifld_note = rows, note
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    combined = []
    if osm_rows:
        combined.extend(osm_rows)
    if hifld_rows:
        combined.extend(hifld_rows)

    if combined:
        df_combined = pd.DataFrame(combined)
        df_combined = df_combined.round({"lat": 3, "lon": 3})
        df_combined = df_combined.drop_duplicates(subset=["lat", "lon"]).reset_index(
            drop=True
        )
        _pri_map = {
            "Police": 0,
            "Fire": 1,
            "School": 2,
            "Hospital": 3,
            "Government": 4,
            "Library": 5,
        }
        df_combined["_pri"] = df_combined["type"].map(_pri_map).fillna(9)
        df_combined = (
            df_combined.sort_values("_pri")
            .head(max_stations)
            .drop(columns="_pri")
            .reset_index(drop=True)
        )
        sources = [s for s, r in [("OSM", osm_rows), ("HIFLD", hifld_rows)] if r]
        note = f"Found {len(df_combined)} candidate sites from {' + '.join(sources)}."
        return df_combined, note

    df_fallback = _make_random_stations(df_calls, n=40)
    if not df_fallback.empty:
        notes = [n for n in [osm_note, hifld_note] if n]
        return df_fallback, "Fallback stations generated from call data. " + " | ".join(
            notes
        )
    return None, "Could not generate stations — no valid call coordinates."
