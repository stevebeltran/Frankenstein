# Copyright (c) Steven Beltran. Created by Steven Beltran in partnership with BRINC Drones.
import warnings
warnings.filterwarnings(
    "ignore",
    message=r"authlib\.jose module is deprecated, please use joserfc instead\.",
    category=DeprecationWarning,
)

# Standard library imports
import base64
import concurrent.futures as cf
import datetime
import glob
import hashlib
import heapq
import hmac
import html
import io
import itertools
import json
import math
import os
import random
import re
import smtplib
import sys
import tempfile
import time
import traceback
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse
import urllib.request

# Set CWD to the project root so every relative asset path (parquets, shapefiles,
# logos, etc.) resolves correctly regardless of how the process was launched.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Third-party imports
import geopandas as gpd
import numpy as np
import plotly.graph_objects as go
import pyproj
import streamlit as st
from PIL import Image
from google.oauth2.service_account import Credentials
from shapely.geometry import Point, Polygon, MultiPolygon, box, shape
from shapely.ops import unary_union
from shapely.wkb import loads as _wkb_loads

import gspread
import pulp
import simplekml
import streamlit.components.v1 as components
from streamlit.components.v1 import declare_component

APP_DIR = Path(__file__).resolve().parent
MODULES_DIR = APP_DIR / "modules"


def _load_local_module(module_name: str):
    """Load a local modules.* file defensively for Streamlit/Python import edge cases."""
    import importlib
    import importlib.util as _importlib_util

    package_name = "modules"
    full_name = f"{package_name}.{module_name}"

    try:
        return importlib.import_module(full_name)
    except KeyError:
        package_path = MODULES_DIR / "__init__.py"
        package_mod = sys.modules.get(package_name)
        if package_mod is None or not getattr(package_mod, "__path__", None):
            package_spec = _importlib_util.spec_from_file_location(
                package_name,
                package_path,
                submodule_search_locations=[str(MODULES_DIR)],
            )
            if package_spec is None or package_spec.loader is None:
                raise
            package_mod = _importlib_util.module_from_spec(package_spec)
            sys.modules[package_name] = package_mod
            package_spec.loader.exec_module(package_mod)

        module_path = MODULES_DIR / f"{module_name}.py"
        module_spec = _importlib_util.spec_from_file_location(full_name, module_path)
        if module_spec is None or module_spec.loader is None:
            raise
        module = _importlib_util.module_from_spec(module_spec)
        sys.modules[full_name] = module
        module_spec.loader.exec_module(module)
        return module

# ── Module imports ────────────────────────────────────────────────────────────
from modules.constants import (
    API_TIMEOUT_DEFAULT, API_TIMEOUT_QUICK, API_TIMEOUT_STANDARD, API_TIMEOUT_LONG,
    API_TIMEOUT_EXTENDED, API_TIMEOUT_VERY_LONG, OVERPASS_TIMEOUT, CONCURRENT_REQUEST_TIMEOUT,
    METERS_PER_DEGREE_LATITUDE, FREQUENCY_HZ, FREQUENCY_MHZ, FSPL_COEFFICIENT,
    TX_ALTITUDE_M, RX_ALTITUDE_M, FRESNEL_BLOCKAGE_THRESHOLD, TERRAIN_BLOCKAGE_CRITICAL_RATIO,
    TERRAIN_BLOCKAGE_LOSS_COEFFICIENT, TERRAIN_BLOCKAGE_LOSS_MAX, CLUTTER_LOSS, FADE_MARGIN_DB,
    OSM_SEARCH_RADIUS_SMALL, OSM_SEARCH_RADIUS_LARGE, OSM_MAX_STATIONS,
    COORDINATE_PRECISION, SKLEARN_RANDOM_STATE, SKLEARN_BATCH_SIZE, SKLEARN_N_INIT
)
from modules.station_generation import (
    _make_random_stations, _fetch_osm_stations_cached, _fetch_hifld_stations_cached,
    generate_stations_from_calls
)
from modules.ui_components import (
    _render_in_app_faq, _render_public_report_route, FAQ_CHANGELOG
)
# Note: FAQ_CHANGELOG will be populated after __version__ and __build_datetime__ are loaded
from modules.coverage_analysis import (
    _estimate_elevation_simple, _estimate_clutter_loss_db, _estimate_terrain_blockage_db,
    _path_loss_advanced
)
from modules.export_handlers import (
    _build_corrected_export_from_merged_fallback
)
from pages import (
    render_onboarding_page, render_simulation_page
)
from modules.config import (
    CONFIG, GUARDIAN_FLIGHT_HOURS_PER_DAY, SIMULATOR_DISCLAIMER_SHORT,
    STATE_FIPS, US_STATES_ABBR, KNOWN_POPULATIONS, DEMO_CITIES, FAST_DEMO_CITIES,
    FAA_CEILING_COLORS, FAA_DEFAULT_COLOR, STATION_COLORS,
    bg_main, bg_sidebar, text_main, text_muted, accent_color, card_bg, card_border,
    card_text, card_title, budget_box_bg, budget_box_border, budget_box_shadow,
    map_style, map_boundary_color, map_incident_color, legend_bg, legend_text,
    get_hero_message, get_faa_message, get_airfield_message,
    get_jurisdiction_message, get_spatial_message
)
try:
    from modules.config import calculate_max_flights_per_day
except ImportError:
    def calculate_max_flights_per_day(
        mission_minutes: float,
        *,
        flight_minutes: float,
        downtime_minutes: float,
        operation_minutes: float = 24 * 60,
    ) -> float:
        mission_minutes = float(mission_minutes or 0.0)
        flight_minutes = float(flight_minutes or 0.0)
        downtime_minutes = max(0.0, float(downtime_minutes or 0.0))
        operation_minutes = max(0.0, float(operation_minutes or 0.0))
        if mission_minutes <= 0.0 or flight_minutes <= 0.0 or operation_minutes <= 0.0:
            return 0.0
        if mission_minutes > flight_minutes + 1e-9:
            return 0.0

        elapsed = 0.0
        flights = 0
        remaining_flight = flight_minutes
        while True:
            if mission_minutes <= remaining_flight + 1e-9:
                if elapsed + mission_minutes > operation_minutes + 1e-9:
                    break
                elapsed += mission_minutes
                flights += 1
                remaining_flight -= mission_minutes
            else:
                if elapsed + downtime_minutes > operation_minutes + 1e-9:
                    break
                elapsed += downtime_minutes
                remaining_flight = flight_minutes
        return float(flights)

_versioning_mod = _load_local_module("versioning")
# No importlib.reload needed here — Streamlit restarts the process on every
# app.py save, so versioning._compute_build_info() already runs fresh each time.
# Reloading on every rerun forced a full re-read of the 8 000-line app.py file
# on every user interaction, for no benefit.
__version__ = _versioning_mod.__version__
__build_revision__ = _versioning_mod.__build_revision__
__build_datetime__ = _versioning_mod.__build_datetime__
__build_line_count__ = _versioning_mod.__build_line_count__
_render_version_badge = _versioning_mod._render_version_badge

# Populate FAQ_CHANGELOG with version info (after versioning module is loaded)
FAQ_CHANGELOG.clear()
FAQ_CHANGELOG.append({
    "version": __version__,
    "timestamp": __build_datetime__,
    "summary": "Added an in-app FAQ launcher in the upper-left with a compact versioned release-notes footer.",
})

from modules.public_reports import (
    _build_public_report_url,
    _get_document_jurisdiction_name,
    _get_public_report_secret,
    _get_query_params_dict,
    _get_request_base_url,
    _publish_public_report_html,
    _public_report_metadata_path,
    _public_report_html_path,
    _resolve_public_reports_dir,
    _sign_public_report_id,
    _slugify,
)
from modules.image_utils import (
    get_base64_of_bin_file, get_themed_logo_base64, get_transparent_product_base64
)
NOTIFICATIONS_AVAILABLE = True
try:
    from modules.notifications import (
        _notify_email, _log_to_sheets, _log_login_to_sheets, _publish_public_report_to_sheets,
        _log_qr_scan_to_sheets,
    )
except Exception as _notifications_import_error:
    NOTIFICATIONS_AVAILABLE = False

    def _notify_email(*args, **kwargs):
        return None

    def _log_to_sheets(*args, **kwargs):
        return None

    def _log_login_to_sheets(*args, **kwargs):
        return None

    def _publish_public_report_to_sheets(*args, **kwargs):
        return None

    def _log_qr_scan_to_sheets(*args, **kwargs):
        return None

    print(f"Notifications disabled at startup: {_notifications_import_error}")
from modules.cad_parser import (
    aggressive_parse_calls, _extract_file_meta, _get_annualized_calls
)
_census_batch_mod = _load_local_module("census_batch")
build_census_staging = _census_batch_mod.build_census_staging
make_census_batch_chunks = _census_batch_mod.make_census_batch_chunks
make_census_batch_zip = _census_batch_mod.make_census_batch_zip
make_sample_census_batch = _census_batch_mod.make_sample_census_batch
parse_census_result_files = _census_batch_mod.parse_census_result_files
merge_census_results = _census_batch_mod.merge_census_results
submit_census_batch_chunk = _census_batch_mod.submit_census_batch_chunk
build_census_chunk_payload = _census_batch_mod.build_census_chunk_payload


build_corrected_export_from_merged = getattr(
    _census_batch_mod,
    "build_corrected_export_from_merged",
    _build_corrected_export_from_merged_fallback,
)
from modules.geospatial import (
    _load_uploaded_boundary_overlay, _boundary_overlay_status,
    _count_points_within_boundary, find_jurisdictions_by_coordinates
)
from modules import faa_rf, optimization, html_reports
_session_state_mod = _load_local_module("session_state")
init_session_state = _session_state_mod.init_session_state
from modules.dashboard_helpers import log_map_build_event_once, resolve_master_boundary, render_sidebar_jurisdiction_selector, render_data_filters, render_display_options, render_deployment_strategy, prepare_station_candidates, manage_custom_stations, prepare_runtime_context, optimize_fleet_selection, compute_station_suggestions, render_station_suggestions
from modules import onboarding as _onboarding_mod
from modules.highway_corridor import (
    STATE_PRIMARY_INTERSTATES,
    fetch_highway_geometry,
    build_corridor_polygon,
    estimate_corridor_calls,
    build_corridor_demo,
)


detect_brinc_file = _onboarding_mod.detect_brinc_file
load_brinc_save_data = _onboarding_mod.load_brinc_save_data
restore_brinc_session = _onboarding_mod.restore_brinc_session
split_uploaded_files = _onboarding_mod.split_uploaded_files
load_station_file = _onboarding_mod.load_station_file
detect_location_from_calls = _onboarding_mod.detect_location_from_calls
resolve_uploaded_boundaries = _onboarding_mod.resolve_uploaded_boundaries
split_simulation_optional_files = _onboarding_mod.split_simulation_optional_files
load_simulation_boundary_overlay = _onboarding_mod.load_simulation_boundary_overlay
load_simulation_custom_stations = _onboarding_mod.load_simulation_custom_stations
build_demo_boundaries = _onboarding_mod.build_demo_boundaries
build_demo_calls = _onboarding_mod.build_demo_calls
resolve_demo_stations = _onboarding_mod.resolve_demo_stations


def _infer_simulation_targets_from_station_file_fallback(*args, **kwargs):
    return [], ''


infer_simulation_targets_from_station_file = getattr(
    _onboarding_mod,
    'infer_simulation_targets_from_station_file',
    _infer_simulation_targets_from_station_file_fallback,
)

APP_DIR = Path(__file__).resolve().parent
QUICK_PIN_COMPONENT_DIR = APP_DIR / "quick_pin_component"
QUICK_PIN_COMPONENT = (
    declare_component(
        "quick_pin_component",
        path=str(QUICK_PIN_COMPONENT_DIR),
    )
    if QUICK_PIN_COMPONENT_DIR.is_dir()
    else None
)


def _uploaded_files_signature(files):
    parts = []
    for idx, uploaded_file in enumerate(files or []):
        try:
            size = len(uploaded_file.getvalue())
        except Exception:
            size = 0
        parts.append(f"{idx}:{uploaded_file.name}:{size}")
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest() if parts else ""


def _reset_census_state(session_state):
    session_state['census_pending'] = False
    session_state['census_source_signature'] = ''
    session_state['census_stage_df'] = None
    session_state['census_original_df'] = None
    session_state['census_partial_calls_df'] = None
    session_state['_census_batch_started_at'] = None
    session_state['census_batch_zip_bytes'] = b""
    session_state['census_batch_zip_name'] = ""
    session_state['census_sample_bytes'] = b""
    session_state['census_sample_name'] = ""
    session_state['census_summary'] = {}
    session_state['census_conversion_summary'] = {}
    session_state['census_corrected_bytes'] = b""
    session_state['census_corrected_name'] = ""
    session_state['census_corrected_format'] = "csv"
    session_state['census_download_notice'] = False




def _select_best_boundary_for_calls(df_calls: pd.DataFrame, city_text: str, state_abbr: str, prefer_county: bool = False) -> Optional[Tuple[Any, int, Any]]:
    """Try place and county boundaries and keep the candidate containing the most uploaded calls."""
    candidates = []

    try:
        place_success, place_gdf = fetch_place_boundary_local(state_abbr, city_text)
        if place_success and place_gdf is not None and not place_gdf.empty:
            candidates.append(('place', place_gdf, _count_points_within_boundary(df_calls, place_gdf)))
    except Exception:
        pass

    county_names = [city_text]
    if not str(city_text).lower().endswith(" county"):
        county_names.append(f"{city_text} County")

    for cname in county_names:
        try:
            county_success, county_gdf = fetch_county_boundary_local(state_abbr, cname)
            if county_success and county_gdf is not None and not county_gdf.empty:
                candidates.append(('county', county_gdf, _count_points_within_boundary(df_calls, county_gdf)))
                break
        except Exception:
            pass

    if not candidates:
        # ── TIGER fallback: parquet not present or city not found — download from Census ──
        state_fips = STATE_FIPS.get(state_abbr)
        if state_fips:
            try:
                tiger_success, tiger_gdf = fetch_tiger_city_shapefile(state_fips, city_text, SHAPEFILE_DIR)
                if tiger_success and tiger_gdf is not None and not tiger_gdf.empty:
                    tiger_gdf = tiger_gdf.copy()
                    if 'NAME' not in tiger_gdf.columns:
                        tiger_gdf['NAME'] = city_text
                    hits = _count_points_within_boundary(df_calls, tiger_gdf)
                    candidates.append(('place', tiger_gdf, hits))
            except Exception:
                pass

    if not candidates:
        return False, None, 'place', 0

    if prefer_county:
        candidates.sort(key=lambda x: (x[2], 1 if x[0] == 'county' else 0), reverse=True)
    else:
        candidates.sort(key=lambda x: (x[2], 1 if x[0] == 'place' else 0), reverse=True)

    best_kind, best_gdf, best_hits = candidates[0]
    return True, best_gdf, best_kind, int(best_hits)

# ============================================================
# Station Generation (moved to modules/station_generation.py)
# ============================================================

# ============================================================
# CACHED DATA FUNCTIONS
# ============================================================
@st.cache_data
def get_address_from_latlon(lat: float, lon: float) -> str:
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'BRINC_DFR_Optimizer_App/2.0'})
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode('utf-8'))
            if 'address' in data:
                addr = data['address']
                road = addr.get('road', '')
                house_number = addr.get('house_number', '')
                city = addr.get('city', addr.get('town', addr.get('village', '')))
                if road:
                    return f"{house_number} {road}, {city}".strip(', ')
    except Exception:
        pass
    # Fallback to coordinates if an exact street address isn't found
    return f"{lat:.5f}, {lon:.5f}"

def _lookup_streamlit_secret(*names: str) -> Any:
    _target_names = {str(_name or '').strip().upper() for _name in names if str(_name or '').strip()}
    if not _target_names:
        return ""

    def _scan_secret_container(_container, _visited=None):
        _visited = _visited or set()
        _obj_id = id(_container)
        if _obj_id in _visited:
            return ""
        _visited.add(_obj_id)

        if hasattr(_container, 'items'):
            try:
                _items = list(_container.items())
            except Exception:
                _items = []

            for _key, _value in _items:
                if str(_key or '').strip().upper() in _target_names and not hasattr(_value, 'items'):
                    _secret_value = str(_value or '').strip()
                    if _secret_value:
                        return _secret_value

            for _, _value in _items:
                if hasattr(_value, 'items'):
                    _nested_value = _scan_secret_container(_value, _visited)
                    if _nested_value:
                        return _nested_value
        return ""

    try:
        _secret_value = _scan_secret_container(st.secrets)
        if _secret_value:
            return _secret_value
    except Exception:
        pass

    for _name in names:
        _env_value = str(os.environ.get(str(_name or '').strip(), '') or '').strip()
        if _env_value:
            return _env_value
    return ""


def _get_google_maps_api_key():
    return _lookup_streamlit_secret(
        "GOOGLE_MAPS_API_KEY",
        "GOOGLE_GEOCODING_API_KEY",
        "GOOGLE_API_KEY",
        "GMAPS_API_KEY",
    )


def _get_mapbox_api_key():
    return _lookup_streamlit_secret(
        "MAPBOX_ACCESS_TOKEN",
        "MAPBOX_API_KEY",
        "MAPBOX_TOKEN",
    )


def _get_geocoder_provider_signature():
    _provider_values = {
        'google': _get_google_maps_api_key(),
        'mapbox': _get_mapbox_api_key(),
    }
    _signature_payload = "|".join(
        f"{_provider}:{hashlib.sha256(str(_value or '').encode('utf-8')).hexdigest()}"
        for _provider, _value in sorted(_provider_values.items())
    )
    return hashlib.sha256(_signature_payload.encode('utf-8')).hexdigest()


@st.cache_data(show_spinner=False)
def _search_address_candidates_cached(address_str, limit=6, preferred_city="", preferred_state="", provider_signature=""):
    address_str = str(address_str or '').strip()
    if not address_str:
        try:
            st.session_state['_last_geocode_trace'] = {
                'input': '',
                'preferred_city': str(preferred_city or '').strip(),
                'preferred_state': str(preferred_state or '').strip().upper(),
                'queries': [],
                'providers': [],
                'candidate_count': 0,
            }
        except Exception:
            pass
        return []

    limit = max(1, min(int(limit or 6), 10))
    preferred_city = str(preferred_city or '').strip()
    preferred_state = str(preferred_state or '').strip().upper()
    # Full state name for providers (OSM) that return "Nebraska" instead of "NE"
    _abbr_to_full = {v: k for k, v in US_STATES_ABBR.items()}
    preferred_state_full = _abbr_to_full.get(preferred_state, '').lower()
    candidates = []
    seen = set()

    def _normalize_text(value):
        return str(value or "").strip().lower()

    def _normalize_address_variants(raw_value):
        raw_value = str(raw_value or '').strip()
        if not raw_value:
            return []
        variants = [raw_value]
        compact = re.sub(r'\s+', ' ', raw_value).strip()
        if compact and compact.lower() != raw_value.lower():
            variants.append(compact)

        word_to_num = {
            'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
            'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10',
        }
        street_suffix_map = {
            'street': 'st',
            'avenue': 'ave',
            'boulevard': 'blvd',
            'road': 'rd',
            'drive': 'dr',
            'lane': 'ln',
            'court': 'ct',
            'place': 'pl',
            'parkway': 'pkwy',
            'circle': 'cir',
            'terrace': 'ter',
        }

        def _transform_variant(text):
            text = re.sub(r'\s+', ' ', str(text or '').strip())
            if not text:
                return []
            out = [text]
            parts = text.split(' ', 1)
            if parts:
                first = parts[0].lower().rstrip('.,')
                if first in word_to_num and len(parts) > 1:
                    out.append(f"{word_to_num[first]} {parts[1]}")
            replaced = text
            for suffix, abbr in street_suffix_map.items():
                replaced = re.sub(rf'\b{suffix}\b', abbr, replaced, flags=re.IGNORECASE)
            if replaced.lower() != text.lower():
                out.append(replaced)
            out2 = []
            for candidate in out:
                parts2 = candidate.split(' ', 1)
                if parts2:
                    first2 = parts2[0].lower().rstrip('.,')
                    if first2 in word_to_num and len(parts2) > 1:
                        candidate = f"{word_to_num[first2]} {parts2[1]}"
                replaced2 = candidate
                for suffix, abbr in street_suffix_map.items():
                    replaced2 = re.sub(rf'\b{suffix}\b', abbr, replaced2, flags=re.IGNORECASE)
                out2.append(candidate)
                if replaced2.lower() != candidate.lower():
                    out2.append(replaced2)
            deduped = []
            seen_local = set()
            for candidate in out2:
                cleaned = re.sub(r'\s+', ' ', str(candidate or '').strip())
                key = cleaned.lower()
                if cleaned and key not in seen_local:
                    seen_local.add(key)
                    deduped.append(cleaned)
            return deduped

        expanded = []
        seen_expanded = set()
        for variant in variants:
            for candidate in _transform_variant(variant):
                key = candidate.lower()
                if candidate and key not in seen_expanded:
                    seen_expanded.add(key)
                    expanded.append(candidate)
        return expanded

    def _query_variants():
        _variants = []
        for _base_variant in _normalize_address_variants(address_str):
            _variants.append(_base_variant)
            _has_city = preferred_city and preferred_city.lower() in _base_variant.lower()
            _has_state = preferred_state and preferred_state.lower() in _base_variant.lower()
            if preferred_city and preferred_state and (not _has_city or not _has_state):
                _variants.append(f"{_base_variant}, {preferred_city}, {preferred_state}")
            if preferred_state and not _has_state:
                _variants.append(f"{_base_variant}, {preferred_state}")
        ordered = []
        seen_variants = set()
        for _variant in _variants:
            _clean = str(_variant or '').strip()
            if _clean and _clean.lower() not in seen_variants:
                seen_variants.add(_clean.lower())
                ordered.append(_clean)
        return ordered

    def _candidate_score(candidate):
        _label = _normalize_text(candidate.get('matched_address') or candidate.get('label'))
        _source = str(candidate.get('source', ''))
        _score = {
            'Google': 500,
            'Mapbox': 425,
            'Census': 350,
            'OSM': 250,
        }.get(_source, 0)

        if preferred_state:
            _state_token = f", {preferred_state.lower()}"
            _full_token = f", {preferred_state_full}" if preferred_state_full else None
            _in_label = (
                _state_token in _label
                or _label.endswith(f" {preferred_state.lower()}")
                or (_full_token and _full_token in _label)
            )
            if _in_label:
                _score += 220
            else:
                _score -= 180
        if preferred_city:
            if preferred_city.lower() in _label:
                _score += 150
            else:
                _score -= 80

        _typed = _normalize_text(address_str)
        if _typed and _typed in _label:
            _score += 80
        elif _typed:
            _score += max(0, 30 - min(len(_typed), 30))
        return _score

    def _add_candidate(label, lat, lon, source, raw_match=''):
        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except Exception:
            return
        dedupe_key = (round(lat_f, 6), round(lon_f, 6), str(label).strip().lower())
        if dedupe_key in seen:
            return
        seen.add(dedupe_key)
        candidates.append({
            'label': str(label).strip() or str(raw_match).strip() or address_str,
            'matched_address': str(raw_match).strip() or str(label).strip() or address_str,
            'lat': lat_f,
            'lon': lon_f,
            'source': source,
            '_score': 0,
        })

    _queries = _query_variants()
    _provider_trace = []

    for _query in _queries:
        try:
            _params = urllib.parse.urlencode({
                'address': _query,
                'benchmark': '2020',
                'format': 'json'
            })
            _url = f"https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?{_params}"
            _req = urllib.request.Request(_url, headers={'User-Agent': 'BRINC_COS_Optimizer/1.0'})
            with urllib.request.urlopen(_req, timeout=8) as _resp:
                _data = json.loads(_resp.read().decode('utf-8'))
            _matches = _data.get('result', {}).get('addressMatches', [])[:limit]
            _provider_trace.append({'provider': 'Census', 'query': _query, 'used': True, 'match_count': len(_matches), 'status': 'ok'})
            for _match in _matches:
                _coords = _match.get('coordinates', {})
                _add_candidate(
                    _match.get('matchedAddress', _query),
                    _coords.get('y'),
                    _coords.get('x'),
                    'Census',
                    raw_match=_match.get('matchedAddress', _query),
                )
        except Exception:
            _provider_trace.append({'provider': 'Census', 'query': _query, 'used': True, 'match_count': 0, 'status': 'error'})

    _google_api_key = _get_google_maps_api_key()
    if _google_api_key:
        for _query in _queries:
            try:
                _params = urllib.parse.urlencode({
                    'address': _query,
                    'key': _google_api_key,
                    'components': f'country:US|administrative_area:{preferred_state}' if preferred_state else 'country:US',
                })
                _url = f"https://maps.googleapis.com/maps/api/geocode/json?{_params}"
                _req = urllib.request.Request(_url, headers={'User-Agent': 'BRINC_COS_Optimizer/1.0'})
                with urllib.request.urlopen(_req, timeout=8) as _resp:
                    _data = json.loads(_resp.read().decode('utf-8'))
                _matches = _data.get('results', [])[:limit]
                _provider_trace.append({'provider': 'Google', 'query': _query, 'used': True, 'match_count': len(_matches), 'status': _data.get('status', 'ok')})
                for _match in _matches:
                    _geometry = _match.get('geometry', {}).get('location', {})
                    _label = _match.get('formatted_address', _query)
                    _add_candidate(_label, _geometry.get('lat'), _geometry.get('lng'), 'Google', raw_match=_label)
            except Exception:
                _provider_trace.append({'provider': 'Google', 'query': _query, 'used': True, 'match_count': 0, 'status': 'error'})
    else:
        _provider_trace.append({'provider': 'Google', 'query': '', 'used': False, 'match_count': 0, 'status': 'missing_api_key'})

    _mapbox_key = _get_mapbox_api_key()
    if _mapbox_key:
        for _query in _queries:
            try:
                _params = urllib.parse.urlencode({
                    'q': _query,
                    'access_token': _mapbox_key,
                    'country': 'US',
                    'limit': str(limit),
                    'autocomplete': 'true',
                    'types': 'address,street',
                })
                _url = f"https://api.mapbox.com/search/geocode/v6/forward?{_params}"
                _req = urllib.request.Request(_url, headers={'User-Agent': 'BRINC_COS_Optimizer/1.0'})
                with urllib.request.urlopen(_req, timeout=8) as _resp:
                    _data = json.loads(_resp.read().decode('utf-8'))
                _matches = _data.get('features', [])[:limit]
                _provider_trace.append({'provider': 'Mapbox', 'query': _query, 'used': True, 'match_count': len(_matches), 'status': 'ok'})
                for _match in _matches:
                    _coords = (_match.get('geometry') or {}).get('coordinates') or [None, None]
                    _props = _match.get('properties') or {}
                    _label = (
                        _props.get('full_address')
                        or _match.get('place_name')
                        or _match.get('name')
                        or _query
                    )
                    _add_candidate(_label, _coords[1], _coords[0], 'Mapbox', raw_match=_label)
            except Exception:
                _provider_trace.append({'provider': 'Mapbox', 'query': _query, 'used': True, 'match_count': 0, 'status': 'error'})
    else:
        _provider_trace.append({'provider': 'Mapbox', 'query': '', 'used': False, 'match_count': 0, 'status': 'missing_api_key'})

    for _query in _queries:
        try:
            _params = urllib.parse.urlencode({
                'format': 'jsonv2',
                'q': _query,
                'limit': str(limit),
                'countrycodes': 'us',
                'addressdetails': '1',
            })
            _url = f"https://nominatim.openstreetmap.org/search?{_params}"
            _req = urllib.request.Request(_url, headers={'User-Agent': 'BRINC_COS_Optimizer/1.0'})
            with urllib.request.urlopen(_req, timeout=8) as _resp:
                _data = json.loads(_resp.read().decode('utf-8'))
            _matches = _data[:limit]
            _provider_trace.append({'provider': 'OSM', 'query': _query, 'used': True, 'match_count': len(_matches), 'status': 'ok'})
            for _match in _matches:
                _label = _match.get('display_name', _query)
                _add_candidate(_label, _match.get('lat'), _match.get('lon'), 'OSM', raw_match=_label)
        except Exception:
            _provider_trace.append({'provider': 'OSM', 'query': _query, 'used': True, 'match_count': 0, 'status': 'error'})

    for _candidate in candidates:
        _candidate['_score'] = _candidate_score(_candidate)
    candidates.sort(key=lambda _item: (-_item.get('_score', 0), _item.get('matched_address', '')))
    try:
        st.session_state['_last_geocode_trace'] = {
            'input': address_str,
            'preferred_city': preferred_city,
            'preferred_state': preferred_state,
            'queries': _queries,
            'providers': _provider_trace,
            'candidate_count': len(candidates),
            'top_candidate': candidates[0]['matched_address'] if candidates else '',
        }
    except Exception:
        pass
    return [{k: v for k, v in _candidate.items() if k != '_score'} for _candidate in candidates[:limit]]


def search_address_candidates(address_str: str, limit: int = 6, preferred_city: str = "", preferred_state: str = "") -> List[Dict[str, Any]]:
    return _search_address_candidates_cached(
        address_str,
        limit=limit,
        preferred_city=preferred_city,
        preferred_state=preferred_state,
        provider_signature=_get_geocoder_provider_signature(),
    )

_PUBLIC_FACILITY_QUERY_TERMS = {
    'Police': ['police department', 'police station', 'sheriff office', 'public safety'],
    'Fire': ['fire station', 'fire department', 'fire hall', 'rescue station'],
    'School': ['school', 'elementary school', 'middle school', 'high school', 'academy'],
    'Government': ['city hall', 'town hall', 'public works', 'municipal building', 'municipal services', 'government center', 'civic center'],
    'Library': ['library', 'public library', 'library branch'],
}

def _normalize_public_facility_type(facility_type):
    raw = str(facility_type or '').strip().lower()
    if not raw:
        return ''
    if 'police' in raw or 'law enforcement' in raw or 'sheriff' in raw:
        return 'Police'
    if 'fire' in raw or 'ems' in raw or 'ambulance' in raw or 'rescue' in raw:
        return 'Fire'
    if 'school' in raw or 'academy' in raw:
        return 'School'
    if 'library' in raw:
        return 'Library'
    if 'government' in raw or 'public works' in raw or 'city hall' in raw or 'town hall' in raw or 'municipal' in raw or 'civic' in raw:
        return 'Government'
    return ''


def _looks_like_street_address(text):
    raw = str(text or '').strip().lower()
    if not raw:
        return False
    if not re.search(r'\d', raw):
        return False
    street_tokens = (
        ' st', ' street', ' rd', ' road', ' ave', ' avenue', ' blvd', ' boulevard',
        ' dr', ' drive', ' ln', ' lane', ' ct', ' court', ' pkwy', ' parkway',
        ' hwy', ' highway', ' ter', ' terrace', ' cir', ' circle', ' way', ' pl',
        ' place', ' n ', ' s ', ' e ', ' w ',
    )
    return any(token in raw for token in street_tokens)


def _public_facility_query_variants(query_str, facility_type, preferred_city="", preferred_state=""):
    query_str = str(query_str or '').strip()
    if not query_str:
        return []

    facility_key = _normalize_public_facility_type(facility_type)
    terms = _PUBLIC_FACILITY_QUERY_TERMS.get(facility_key, [])
    if not terms:
        return []

    preferred_city = str(preferred_city or '').strip()
    preferred_state = str(preferred_state or '').strip().upper()
    variants = []

    base_queries = [query_str]
    _lower_query = query_str.lower()
    if preferred_city and preferred_state and preferred_city.lower() not in _lower_query and preferred_state.lower() not in _lower_query:
        base_queries.append(f"{query_str}, {preferred_city}, {preferred_state}")

    for base_query in base_queries:
        for term in terms:
            variants.append(f"{base_query}, {term}")
            variants.append(f"{base_query} {term}")

    ordered = []
    seen = set()
    for variant in variants:
        clean = re.sub(r'\s+', ' ', str(variant or '').strip())
        key = clean.lower()
        if clean and key not in seen:
            seen.add(key)
            ordered.append(clean)
    return ordered


def _public_facility_type_is_plausible(feature_type, facility_key):
    feature_type = str(feature_type or '').strip().lower()
    if not feature_type:
        return False
    if facility_key == 'Fire':
        return feature_type == 'fire_station'
    if facility_key == 'Police':
        return feature_type in {'police', 'police_station', 'public_bldg'}
    if facility_key == 'School':
        return feature_type in {'school', 'college', 'university'}
    if facility_key == 'Library':
        return feature_type == 'library'
    if facility_key == 'Government':
        return feature_type in {'townhall', 'city_hall', 'public_bldg', 'government', 'civic'}
    return False


def _public_facility_label_is_plausible(label, facility_key):
    label = str(label or '').strip().lower()
    if not label:
        return False
    if facility_key == 'Fire':
        return any(token in label for token in ('fire station', 'fire department', 'fire hall', 'rescue station', 'fire rescue', 'station'))
    if facility_key == 'Police':
        return any(token in label for token in ('police', 'sheriff', 'public safety', 'law enforcement', 'precinct', 'marshal'))
    if facility_key == 'School':
        return any(token in label for token in ('school', 'academy', 'elementary', 'middle school', 'high school', 'campus'))
    if facility_key == 'Library':
        return 'library' in label
    if facility_key == 'Government':
        return any(token in label for token in ('city hall', 'town hall', 'public works', 'municipal', 'government', 'civic center', 'administration'))
    return False


@st.cache_data(show_spinner=False)
def _reverse_geocode_public_facility_meta(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lon}&zoom=18&addressdetails=1&namedetails=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'BRINC_COS_Optimizer/1.0'})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _public_facility_candidate_is_plausible(candidate, facility_key):
    try:
        lat = float(candidate.get('lat'))
        lon = float(candidate.get('lon'))
    except Exception:
        return False

    reverse_meta = _reverse_geocode_public_facility_meta(lat, lon) or {}
    reverse_type = str(reverse_meta.get('type') or '').strip().lower()
    reverse_class = str(reverse_meta.get('class') or '').strip().lower()
    display_name = str(reverse_meta.get('display_name') or '').strip().lower()
    address_blob = ' '.join(
        str(value).strip().lower()
        for value in (reverse_meta.get('address') or {}).values()
        if value
    )
    combined = ' '.join([reverse_type, reverse_class, display_name, address_blob]).strip()

    if any(bad in combined for bad in ('golf course', 'golf_course', 'house', 'residential', 'apartment', 'apartments')):
        return False
    return True


def _public_facility_candidate_score(candidate, facility_type, preferred_city="", preferred_state=""):
    facility_key = _normalize_public_facility_type(facility_type)
    label = str(candidate.get('matched_address') or candidate.get('label') or '').strip().lower()
    feature_type = str(candidate.get('feature_type') or '').strip().lower()
    score = 100

    if facility_key == 'Police':
        if any(token in label for token in ('police', 'sheriff', 'public safety', 'law enforcement', 'precinct', 'marshal')):
            score += 200
        else:
            score -= 500
    elif facility_key == 'Fire':
        if any(token in label for token in ('fire station', 'fire department', 'fire hall', 'rescue')):
            score += 200
        else:
            score -= 500
    elif facility_key == 'School':
        if any(token in label for token in ('school', 'academy', 'elementary', 'middle school', 'high school')):
            score += 180
        else:
            score -= 500
    elif facility_key == 'Library':
        if 'library' in label:
            score += 200
        else:
            score -= 500
    elif facility_key == 'Government':
        if any(token in label for token in ('city hall', 'town hall', 'public works', 'municipal', 'government', 'civic center', 'administration')):
            score += 180
        else:
            score -= 500

    if _public_facility_type_is_plausible(feature_type, facility_key):
        score += 250
    else:
        score -= 600

    if preferred_state:
        _state = preferred_state.lower()
        _abbr_to_full = {v: k for k, v in US_STATES_ABBR.items()}
        _full = _abbr_to_full.get(preferred_state.upper(), '').lower()
        if f", {_state}" in label or label.endswith(f" {_state}") or (_full and _full in label):
            score += 35
        else:
            score -= 20
    if preferred_city:
        if preferred_city.lower() in label:
            score += 25
        else:
            score -= 10
    return score


@st.cache_data(show_spinner=False)
def search_public_facility_candidates(query_str, facility_type, limit=6, preferred_city="", preferred_state=""):
    query_str = str(query_str or '').strip()
    if not query_str:
        return []

    facility_key = _normalize_public_facility_type(facility_type)
    if not facility_key:
        return []

    limit = max(1, min(int(limit or 6), 10))
    preferred_city = str(preferred_city or '').strip()
    preferred_state = str(preferred_state or '').strip().upper()
    queries = _public_facility_query_variants(query_str, facility_key, preferred_city, preferred_state)
    if not queries:
        return []

    candidates = []
    seen = set()
    provider_trace = []
    address_search_hits = 0

    def _add_candidate(label, lat, lon, raw_match=''):
        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except Exception:
            return None
        dedupe_key = (round(lat_f, 6), round(lon_f, 6), str(label).strip().lower())
        if dedupe_key in seen:
            return None
        seen.add(dedupe_key)
        candidate = {
            'label': str(label).strip() or str(raw_match).strip() or query_str,
            'matched_address': str(raw_match).strip() or str(label).strip() or query_str,
            'lat': lat_f,
            'lon': lon_f,
            'source': 'OSM',
            'feature_type': '',
            'feature_class': '',
            '_score': 0,
        }
        candidates.append(candidate)
        return candidate

    def _ingest_address_matches(matches, source_name, query_text):
        nonlocal address_search_hits
        kept = 0
        for _match in matches or []:
            _label = str(_match.get('matched_address') or _match.get('label') or '').strip()
            if not _public_facility_label_is_plausible(_label, facility_key):
                continue
            _candidate = _add_candidate(
                _label,
                _match.get('lat'),
                _match.get('lon'),
                raw_match=_label,
            )
            if _candidate is not None:
                _candidate['source'] = str(_match.get('source') or source_name or 'lookup')
                _candidate['feature_type'] = str(_match.get('feature_type') or '').strip().lower()
                _candidate['feature_class'] = str(_match.get('feature_class') or '').strip().lower()
                if not _public_facility_candidate_is_plausible(_candidate, facility_key):
                    candidates.pop()
                    continue
                kept += 1
        address_search_hits += kept
        provider_trace.append({
            'provider': source_name,
            'query': query_text,
            'used': True,
            'match_count': kept,
            'status': 'ok',
        })

    for _query in queries:
        try:
            addr_matches = search_address_candidates(
                _query,
                limit=limit,
                preferred_city=preferred_city,
                preferred_state=preferred_state,
            )
            _ingest_address_matches(addr_matches, 'validated_address_search', _query)
        except Exception:
            provider_trace.append({'provider': 'validated_address_search', 'query': _query, 'used': True, 'match_count': 0, 'status': 'error'})

    if not candidates:
        for _query in queries:
            try:
                _params = urllib.parse.urlencode({
                    'format': 'jsonv2',
                    'q': _query,
                    'limit': str(limit),
                    'countrycodes': 'us',
                    'addressdetails': '1',
                })
                _url = f"https://nominatim.openstreetmap.org/search?{_params}"
                _req = urllib.request.Request(_url, headers={'User-Agent': 'BRINC_COS_Optimizer/1.0'})
                with urllib.request.urlopen(_req, timeout=8) as _resp:
                    _data = json.loads(_resp.read().decode('utf-8'))
                _matches = _data[:limit]
                provider_trace.append({'provider': 'OSM_POI', 'query': _query, 'used': True, 'match_count': len(_matches), 'status': 'ok'})
                for _match in _matches:
                    _label = _match.get('display_name', _query)
                    _feature_type = str(_match.get('type') or '').strip().lower()
                    _feature_class = str(_match.get('class') or '').strip().lower()
                    if not (_public_facility_type_is_plausible(_feature_type, facility_key) or _public_facility_label_is_plausible(_label, facility_key)):
                        continue
                    _candidate = _add_candidate(_label, _match.get('lat'), _match.get('lon'), raw_match=_label)
                    if _candidate is not None:
                        _candidate['source'] = 'OSM'
                        _candidate['feature_type'] = _feature_type
                        _candidate['feature_class'] = _feature_class
                        if not _public_facility_candidate_is_plausible(_candidate, facility_key):
                            candidates.pop()
                            continue
            except Exception:
                provider_trace.append({'provider': 'OSM_POI', 'query': _query, 'used': True, 'match_count': 0, 'status': 'error'})

    for _candidate in candidates:
        _candidate['_score'] = _public_facility_candidate_score(_candidate, facility_key, preferred_city=preferred_city, preferred_state=preferred_state)

    candidates = [c for c in candidates if c.get('_score', -999) > 0]
    candidates.sort(key=lambda item: (-item.get('_score', 0), item.get('matched_address', '')))

    try:
        st.session_state['_last_geocode_trace'] = {
            'input': query_str,
            'facility_type': facility_key,
            'preferred_city': preferred_city,
            'preferred_state': preferred_state,
            'queries': queries,
            'providers': provider_trace,
            'candidate_count': len(candidates),
            'top_candidate': candidates[0]['matched_address'] if candidates else '',
            'public_facility_lookup': True,
        }
    except Exception:
        pass

    return [{k: v for k, v in _candidate.items() if k != '_score'} for _candidate in candidates[:limit]]

@st.cache_data(show_spinner=False)
def forward_geocode(address_str):
    _matches = search_address_candidates(
        address_str,
        limit=1,
        preferred_city=st.session_state.get('active_city', ''),
        preferred_state=st.session_state.get('active_state', ''),
    )
    if _matches:
        return float(_matches[0]['lat']), float(_matches[0]['lon'])
    return None, None

@st.cache_data(show_spinner=False)
def lookup_zip_code(zip_code: str):
    """
    Look up a US ZIP code and return (city, state_abbr, county) using the free
    Zippopotam.us API.  Returns (None, None, None) on failure.
    """
    zip_code = zip_code.strip()
    if not re.match(r'^\d{5}$', zip_code):
        return None, None, None
    try:
        url = f"https://api.zippopotam.us/us/{zip_code}"
        req = urllib.request.Request(url, headers={'User-Agent': 'BRINC_COS_Optimizer/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        place = data['places'][0]
        city  = place['place name']
        state = place['state abbreviation']
        return city, state, place.get('state', '')
    except Exception:
        return None, None, None

@st.cache_data
def normalize_jurisdiction_name(name: str) -> str:
    if not name:
        return ""
    name = str(name).lower().strip()
    name = re.sub(r'\bst\b\.?', 'saint', name)
    name = re.sub(r'[^a-z0-9\s-]', ' ', name)
    for suffix in [' city', ' town', ' village', ' borough', ' township', ' cdp', ' municipality', ' county', ' parish']:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
            break
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def lookup_county_for_city(city_name: str, state_abbr: str) -> Optional[str]:
    """Use Nominatim reverse-geocode to find the county name for a city that
    doesn't directly match a county name in the local parquet."""
    try:
        lat, lon = forward_geocode(f"{city_name}, {state_abbr}, USA")
        if lat is None: return None
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=8&addressdetails=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'BRINC_COS_Optimizer/1.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        county_raw = data.get('address', {}).get('county', '')
        # Nominatim returns "Winnebago County" — strip the suffix
        county_name = county_raw.replace(' County', '').replace(' Parish', '').replace(' Borough', '').strip()
        return county_name if county_name else None
    except Exception:
        return None

def fetch_county_by_centroid(df_calls: pd.DataFrame, state_abbr: str) -> Optional[str]:
    """Find the county boundary that contains the median centroid of the call data.

    Uses a pure spatial lookup against counties_lite.parquet — no network calls,
    no name-matching.  Returns (True, GeoDataFrame) or (False, None).
    """
    local_file = "counties_lite.parquet"
    if not os.path.exists(local_file):
        return False, None

    state_fips = STATE_FIPS.get(state_abbr)
    if not state_fips:
        return False, None

    try:
        lat = float(df_calls['lat'].dropna().median())
        lon = float(df_calls['lon'].dropna().median())
    except Exception:
        return False, None

    try:
        gdf = gpd.read_parquet(local_file)
        state_rows = gdf[gdf['STATEFP'] == state_fips].copy()
        if state_rows.empty:
            return False, None

        from shapely.geometry import Point
        pt = Point(lon, lat)  # geographic order: (x=lon, y=lat)

        containing = state_rows[state_rows.geometry.contains(pt)]
        if containing.empty:
            # Fall back to nearest centroid in case the point lands on a boundary
            state_rows = state_rows.copy()
            state_rows['_dist'] = state_rows.geometry.distance(pt)
            containing = state_rows.nsmallest(1, '_dist')

        if not containing.empty:
            result = containing[['NAME', 'geometry']].copy()
            result['NAME'] = result['NAME'].astype(str) + " County"
            return True, result
    except Exception as e:
        print(f"[BRINC] fetch_county_by_centroid failed: {e}")

    return False, None


@st.cache_data
def fetch_county_boundary_local(state_abbr, county_name_input):
    # 1. Clean the input
    search_name = normalize_jurisdiction_name(county_name_input)
        
    state_fips = STATE_FIPS.get(state_abbr)
    if not state_fips: return False, None
    
    # 2. Look for our new ultra-compressed parquet file
    local_file = "counties_lite.parquet"
    if not os.path.exists(local_file):
        print(f"[BRINC] Missing {local_file} — ensure it is present in the repository.")
        return False, None

    # 3. Read directly from the Parquet file instantly
    try:
        # Geopandas reads Parquet files in milliseconds!
        gdf = gpd.read_parquet(local_file)

        # Filter for the exact State FIPS code and County Name
        match = gdf[(gdf['STATEFP'] == state_fips) & (gdf['NAME'].str.lower() == search_name)]

        if not match.empty:
            # Put the word "County" back on for the UI displays
            match = match.copy()
            match['NAME'] = match['NAME'] + " County"
            return True, match[['NAME', 'geometry']]
    except Exception as e:
        print(f"[BRINC] fetch_county_boundary_local failed: {e}")

    return False, None

@st.cache_data
def fetch_place_boundary_local(state_abbr, place_name_input):
    """Look up a city/town/CDP boundary from the local places_lite.parquet.
    Returns (True, GeoDataFrame) on success, (False, None) if not found or
    the file doesn't exist yet (falls back to county lookup in caller)."""
    local_file = "places_lite.parquet"
    if not os.path.exists(local_file):
        return False, None   # file not yet added — caller falls back to county

    state_fips = STATE_FIPS.get(state_abbr)
    if not state_fips: return False, None

    search_name = normalize_jurisdiction_name(place_name_input)

    try:
        gdf = gpd.read_parquet(local_file)
        state_rows = gdf[gdf["STATEFP"] == state_fips]

        state_rows = state_rows.copy()
        state_rows['_norm_name'] = state_rows['NAME'].astype(str).apply(normalize_jurisdiction_name)
        if 'NAMELSAD' in state_rows.columns:
            state_rows['_norm_lsad'] = state_rows['NAMELSAD'].astype(str).apply(normalize_jurisdiction_name)
        else:
            state_rows['_norm_lsad'] = state_rows['_norm_name']

        # Exact normalized match first
        match = state_rows[(state_rows['_norm_name'] == search_name) | (state_rows['_norm_lsad'] == search_name)]

        # Partial normalized match fallback (e.g. Fort Worth / Fort Worth city)
        if match.empty:
            match = state_rows[
                state_rows['_norm_name'].str.startswith(search_name) |
                state_rows['_norm_lsad'].str.startswith(search_name)
            ]
            if not match.empty:
                match = match.copy()
                match['_diff'] = match['NAME'].astype(str).str.len() - len(search_name)
                match = match.sort_values('_diff').head(1)

        if match.empty:
            return False, None

        result = match.copy()
        # Use NAMELSAD for display if available (e.g. "Rockford city"), else NAME
        name_col = "NAMELSAD" if "NAMELSAD" in result.columns else "NAME"
        result["NAME"] = result[name_col].astype(str)
        return True, result[["NAME", "geometry"]]

    except Exception:
        return False, None

@st.cache_data
def reverse_geocode_state(lat, lon):
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10&addressdetails=1"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'BRINC_COS_Optimizer/1.0'})
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode('utf-8'))
            address = data.get('address', {})
            state = address.get('state', '')
            city = (
                address.get('city')
                or address.get('town')
                or address.get('village')
                or address.get('municipality')
                or address.get('hamlet')
            )
            return state, city
    except Exception:
        return None, None

_PLACE_SUFFIXES = (
    ' city', ' town', ' village', ' borough', ' township', ' cdp', ' municipality',
    ' county', ' parish', ' census area', ' city and borough', ' borough county',
    ' urban county', ' unified government', ' metro government',
)


def _normalize_population_lookup_name(value):
    text = str(value or '').strip().lower()
    text = text.replace('&', ' and ')
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    for suffix in _PLACE_SUFFIXES:
        if text.endswith(suffix):
            text = text[:-len(suffix)].strip()
            break
    return text


def _population_lookup_aliases(value):
    base = _normalize_population_lookup_name(value)
    aliases = {base} if base else set()
    if not base:
        return aliases
    aliases.add(base.replace('saint ', 'st '))
    aliases.add(base.replace('st ', 'saint '))
    aliases.add(base.replace('-', ' '))
    aliases.add(base.replace('saint ', 'st ').replace('-', ' '))
    aliases.add(base.replace('st ', 'saint ').replace('-', ' '))
    return {alias.strip() for alias in aliases if alias.strip()}


def _lookup_known_population(place_name):
    direct = KNOWN_POPULATIONS.get(place_name)
    if direct is not None:
        return direct
    aliases = _population_lookup_aliases(place_name)
    for known_name, pop in KNOWN_POPULATIONS.items():
        if _normalize_population_lookup_name(known_name) in aliases:
            return pop
    return None


def _lookup_population_for_boundary(state_abbr, city_name, boundary_kind='place'):
    state_fips = STATE_FIPS.get(str(state_abbr or '').strip().upper(), '')
    if not state_fips:
        return None
    if boundary_kind == 'state':
        return fetch_census_state_population(state_fips)
    lookup_name = city_name or state_abbr
    return fetch_census_population(state_fips, lookup_name, is_county=(boundary_kind == 'county'))


def _refresh_reference_population(session_state, selected_names=None):
    state_abbr = str(session_state.get('active_state', '') or '').strip().upper()
    boundary_kind = str(session_state.get('boundary_kind', 'place') or 'place').strip().lower()
    if session_state.get('use_county_boundary'):
        boundary_kind = 'county'

    targets = []
    for name in (selected_names or []):
        clean_name = str(name or '').strip()
        if clean_name and clean_name not in targets:
            targets.append(clean_name)

    if not targets:
        fallback_name = session_state.get('active_city') or session_state.get('active_state') or ''
        fallback_name = str(fallback_name or '').strip()
        if fallback_name:
            targets.append(fallback_name)

    total_population = 0
    all_targets_resolved = bool(targets)

    if boundary_kind == 'state':
        resolved = _lookup_population_for_boundary(state_abbr, state_abbr, boundary_kind='state')
        total_population = int(resolved or 0)
        all_targets_resolved = bool(resolved)
    elif state_abbr and targets:
        for target_name in targets:
            resolved = _lookup_population_for_boundary(
                state_abbr,
                target_name,
                boundary_kind=boundary_kind,
            )
            if resolved:
                total_population += int(resolved)
            else:
                all_targets_resolved = False
    else:
        all_targets_resolved = False

    session_state['estimated_pop'] = int(total_population or 0)
    session_state['_pop_resolved'] = bool(total_population) and all_targets_resolved
    session_state['population_reference_kind'] = boundary_kind
    session_state['population_reference_targets'] = targets
    return int(total_population or 0)


@st.cache_data
def fetch_census_population(state_fips, place_name, is_county=False):
    if is_county:
        url = f"https://api.census.gov/data/2020/dec/pl?get=P1_001N,NAME&for=county:*&in=state:{state_fips}"
    else:
        url = f"https://api.census.gov/data/2020/dec/pl?get=P1_001N,NAME&for=place:*&in=state:{state_fips}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            search_aliases = _population_lookup_aliases(place_name)
            exact_match = None
            prefix_match = None
            for row in data[1:]:
                place_full = str(row[1]).split(',')[0].strip()
                place_aliases = _population_lookup_aliases(place_full)
                if search_aliases & place_aliases:
                    exact_match = int(row[0])
                    break
                for search_name in search_aliases:
                    if any(
                        alias.startswith(search_name + ' ')
                        or alias.startswith(search_name + '-')
                        for alias in place_aliases
                    ):
                        prefix_match = int(row[0])
                        break
                if prefix_match is not None:
                    break
            if exact_match is not None:
                return exact_match
            if prefix_match is not None:
                return prefix_match
    except Exception:
        pass
    return _lookup_known_population(place_name)

@st.cache_data
def fetch_census_state_population(state_fips):
    url = f"https://api.census.gov/data/2020/dec/pl?get=P1_001N,NAME&for=state:{state_fips}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            if len(data) > 1 and len(data[1]) > 0:
                return int(data[1][0])
    except Exception:
        pass
    return None

SHAPEFILE_DIR = "jurisdiction_data"
if not os.path.exists(SHAPEFILE_DIR): os.makedirs(SHAPEFILE_DIR)

def _sanitize_boundary_token(value):
    return str(value or "").strip().replace(" ", "_").replace("/", "_")

def _boundary_shp_base(kind, name, state_abbr):
    return os.path.join(SHAPEFILE_DIR, f"{kind}__{_sanitize_boundary_token(name)}_{state_abbr}")

def save_boundary_gdf(boundary_gdf, kind, name, state_abbr):
    """Save boundary to a type-specific shapefile base so place/county do not overwrite each other."""
    try:
        base = _boundary_shp_base(kind, name, state_abbr)
        # Remove older files for this exact base so a fresh write wins cleanly
        for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
            fp = base + ext
            if os.path.exists(fp):
                try:
                    os.remove(fp)
                except Exception as e:
                    print(f"[BRINC] Could not remove old shapefile {fp}: {e}")
        boundary_gdf.to_file(base + ".shp")
        return base + ".shp"
    except Exception as e:
        print(f"[BRINC] save_boundary_gdf failed for {kind}/{name}/{state_abbr}: {e}")
        return None

def load_saved_boundary(kind, name, state_abbr):
    """Load a previously saved boundary, preferring the exact typed name."""
    try:
        exact = _boundary_shp_base(kind, name, state_abbr) + ".shp"
        if os.path.exists(exact):
            gdf = gpd.read_file(exact)
            if gdf.crs is None:
                gdf = gdf.set_crs(epsg=4269)
            return gdf.to_crs(epsg=4326)
    except Exception as e:
        print(f"[BRINC] load_saved_boundary failed for {kind}/{name}/{state_abbr}: {e}")
    return None

@st.cache_data
def fetch_tiger_state_shapefile(state_fips, state_abbr, output_dir):
    temp_dir = os.path.join(output_dir, "temp_tiger_states")
    cached_shp = os.path.join(temp_dir, "tl_2023_us_state.shp")
    gdf = None

    if os.path.exists(cached_shp):
        try:
            gdf = gpd.read_file(cached_shp)
        except Exception:
            gdf = None

    if gdf is None:
        for year in ["2023", "2022"]:
            url = f"https://www2.census.gov/geo/tiger/TIGER{year}/STATE/tl_{year}_us_state.zip"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "BRINC_COS_Optimizer/1.0"})
                with urllib.request.urlopen(req, timeout=API_TIMEOUT_VERY_LONG) as resp:
                    zip_data = resp.read()
                zip_file = zipfile.ZipFile(io.BytesIO(zip_data))
                os.makedirs(temp_dir, exist_ok=True)
                zip_file.extractall(temp_dir)
                shp_files = glob.glob(os.path.join(temp_dir, "*.shp"))
                if shp_files:
                    gdf = gpd.read_file(shp_files[0])
                    break
            except Exception:
                continue

    if gdf is None:
        return False, None

    try:
        state_gdf = gdf[gdf['STATEFP'].astype(str) == str(state_fips)].copy()
        if state_gdf.empty:
            return False, None
        if 'STUSPS' in state_gdf.columns:
            _abbr_rows = state_gdf[state_gdf['STUSPS'].astype(str).str.upper() == str(state_abbr).upper()].copy()
            if not _abbr_rows.empty:
                state_gdf = _abbr_rows
        state_gdf = state_gdf.dissolve().reset_index(drop=True)
        state_gdf['NAME'] = str(state_abbr).upper()
        if state_gdf.crs is None:
            state_gdf = state_gdf.set_crs(epsg=4269)
        state_gdf = state_gdf.to_crs(epsg=4326)
        save_path = os.path.join(output_dir, f"state_{state_abbr.upper()}_{state_fips}.shp")
        state_gdf.to_file(save_path)
        return True, state_gdf[['NAME', 'geometry']]
    except Exception as e:
        print(f"[BRINC] fetch_tiger_state_shapefile failed for {state_abbr}: {e}")
        return False, None

@st.cache_data
def fetch_tiger_city_shapefile(state_fips, city_name, output_dir):
    # Check if we already downloaded and cached this state's places file
    temp_dir = os.path.join(output_dir, f"temp_tiger_{state_fips}")
    cached_shp = os.path.join(temp_dir, f"tl_2023_{state_fips}_place.shp")
    gdf = None

    if os.path.exists(cached_shp):
        try:
            gdf = gpd.read_file(cached_shp)
        except Exception:
            gdf = None

    if gdf is None:
        # Download from Census TIGER — try 2023 then 2022 as fallback
        for year in ["2023", "2022"]:
            url = f"https://www2.census.gov/geo/tiger/TIGER{year}/PLACE/tl_{year}_{state_fips}_place.zip"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "BRINC_COS_Optimizer/1.0"})
                with urllib.request.urlopen(req, timeout=API_TIMEOUT_VERY_LONG) as resp:
                    zip_data = resp.read()
                zip_file = zipfile.ZipFile(io.BytesIO(zip_data))
                os.makedirs(temp_dir, exist_ok=True)
                zip_file.extractall(temp_dir)
                shp_files = glob.glob(os.path.join(temp_dir, "*.shp"))
                if shp_files:
                    gdf = gpd.read_file(shp_files[0])
                    break
            except Exception:
                continue

    if gdf is None:
        return False, None

    try:
        search_name = city_name.lower().strip()
        exact_mask = gdf['NAME'].str.lower().str.strip() == search_name
        if exact_mask.any():
            city_gdf = gdf[exact_mask].copy()
        else:
            # Partial match — prefer the longest name match to avoid tiny place with same substring
            partial = gdf[gdf['NAME'].str.lower().str.contains(search_name, case=False, na=False)].copy()
            if partial.empty:
                return False, None
            # Pick the row whose NAME most closely matches (shortest extra chars)
            partial['_diff'] = partial['NAME'].str.len() - len(search_name)
            city_gdf = partial.sort_values('_diff').head(1)

        if city_gdf.empty:
            return False, None

        city_gdf = city_gdf.dissolve(by='NAME').reset_index()
        if city_gdf.crs is None:
            city_gdf = city_gdf.set_crs(epsg=4269)
        city_gdf = city_gdf.to_crs(epsg=4326)
        save_path = os.path.join(output_dir, f"{city_name.replace(' ', '_')}_{state_fips}.shp")
        city_gdf.to_file(save_path)
        return True, city_gdf
    except Exception as e:
        print(f"[BRINC] fetch_tiger_city_shapefile failed for {city_name}: {e}")
        return False, None

def add_cell_towers_layer_to_plotly(fig, state_abbr, minx, miny, maxx, maxy):
    """Add OpenCelliD cell tower markers to map."""
    try:
        gdf = faa_rf.load_cached_regulatory_layers(state_abbr, "cell_towers")
        if gdf.empty: return

        # Clip to bounding box
        pad = 0.05
        bbox = box(minx-pad, miny-pad, maxx+pad, maxy+pad)
        clipped = gdf[gdf.geometry.intersects(bbox)]

        if not clipped.empty:
            fig.add_trace(go.Scattermap(
                lat=clipped.geometry.y,
                lon=clipped.geometry.x,
                mode='markers',
                marker=dict(size=5, color='#ff9500', opacity=0.6),
                name='Cell Towers',
                hovertext=['Cell Tower' for _ in clipped],
                hoverinfo='text',
                showlegend=True,
            ))
    except Exception as e:
        print(f"[BRINC] add_cell_towers_layer_to_plotly failed: {e}")

def add_no_fly_zones_layer_to_plotly(fig, minx, miny, maxx, maxy):
    """Add no-fly zones (parks, water, restricted areas) to map."""
    try:
        gdf = faa_rf.load_cached_regulatory_layers("US", "no_fly_zones")
        if gdf.empty: return

        # Clip to bounding box
        pad = 0.05
        bbox = box(minx-pad, miny-pad, maxx+pad, maxy+pad)
        clipped = gdf[gdf.geometry.intersects(bbox)]

        if not clipped.empty:
            for _, row in clipped.iterrows():
                geom = row.geometry
                if geom.geom_type == 'Polygon':
                    lon, lat = zip(*geom.exterior.coords)
                    fig.add_trace(go.Scattermap(
                        lat=lat, lon=lon,
                        mode='lines', fill='toself',
                        fillcolor='rgba(100,100,255,0.15)',
                        line=dict(color='#6464ff', width=1),
                        name='No-Fly Zone',
                        hovertext=row.get('zone_type', 'No-Fly Zone'),
                        hoverinfo='text',
                        showlegend=False,
                    ))
    except Exception as e:
        print(f"[BRINC] add_no_fly_zones_layer_to_plotly failed: {e}")

def _prepare_sampling_polygon(polygon):
    if polygon is None:
        return None
    try:
        if isinstance(polygon, MultiPolygon):
            non_empty = [p for p in polygon.geoms if p is not None and not p.is_empty]
            polygon = MultiPolygon(non_empty) if non_empty else None
        if polygon is None or polygon.is_empty:
            return None
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        if polygon is None or polygon.is_empty:
            return None
        return polygon
    except Exception:
        return None


def generate_random_points_in_polygon(polygon, num_points):
    polygon = _prepare_sampling_polygon(polygon)
    target = max(0, int(num_points))
    if target == 0 or polygon is None:
        return []

    points = []
    seen = set()
    minx, miny, maxx, maxy = polygon.bounds

    for _ in range(200):
        if len(points) >= target:
            break
        x_coords = np.random.uniform(minx, maxx, 1000)
        y_coords = np.random.uniform(miny, maxy, 1000)
        for x, y in zip(x_coords, y_coords):
            if len(points) >= target:
                break
            pt = Point(x, y)
            if polygon.covers(pt):
                key = (round(y, 8), round(x, 8))
                if key not in seen:
                    seen.add(key)
                    points.append((y, x))

    if len(points) < target:
        rep = polygon.representative_point()
        fallback = (rep.y, rep.x)
        while len(points) < target:
            points.append(fallback)
    return points


def generate_clustered_calls(polygon, num_points):
    polygon = _prepare_sampling_polygon(polygon)
    target = max(0, int(num_points))
    if target == 0 or polygon is None:
        return []

    minx, miny, maxx, maxy = polygon.bounds
    hotspots = []
    hotspot_target = min(max(1, random.randint(5, 15)), target)

    for _ in range(5000):
        if len(hotspots) >= hotspot_target:
            break
        hx, hy = random.uniform(minx, maxx), random.uniform(miny, maxy)
        if polygon.covers(Point(hx, hy)):
            hotspots.append((hx, hy))

    if not hotspots:
        rep = polygon.representative_point()
        hotspots = [(rep.x, rep.y)]

    points = []
    target_clustered = int(target * 0.75)
    sigma_x = max((maxx - minx) / 18.0, 1e-4)
    sigma_y = max((maxy - miny) / 18.0, 1e-4)

    for _ in range(max(target * 60, 2000)):
        if len(points) >= target_clustered:
            break
        hx, hy = random.choice(hotspots)
        px, py = np.random.normal(hx, sigma_x), np.random.normal(hy, sigma_y)
        if polygon.covers(Point(px, py)):
            points.append((py, px))

    remaining = target - len(points)
    if remaining > 0:
        points.extend(generate_random_points_in_polygon(polygon, remaining))

    if len(points) > target:
        points = points[:target]
    np.random.shuffle(points)
    return points

def estimate_grants(population):
    if population > 1000000: return "$1.5M - $3.0M+"
    elif population > 500000: return "$500k - $1.5M"
    elif population > 250000: return "$250k - $500k"
    elif population > 100000: return "$100k - $250k"
    else: return "$25k - $100k"

def get_circle_coords(lat, lon, r_mi=2.0):
    angles = np.linspace(0, 2*np.pi, 100)
    c_lats = lat + (r_mi/69.172) * np.sin(angles)
    c_lons = lon + (r_mi/(69.172 * np.cos(np.radians(lat)))) * np.cos(angles)
    return c_lats, c_lons


# ── 4G LTE coverage overlay ───────────────────────────────────────────────────
# Analysis results are keyed by (state_abbr, wkb_hex) — geometry args can't be
# serialized by @st.cache_data, so we keep a manual dict stored in a
# @st.cache_resource singleton (one dict per worker process, persists for the
# lifetime of the server, safe under concurrent access).

@st.cache_resource
def _get_coverage_analysis_cache() -> dict:
    """Returns the shared analysis-result dict for this worker process."""
    return {}


def _coverage_geom_cache_key(geom):
    if geom is None or geom.is_empty:
        return None
    try:
        return geom.wkb_hex
    except Exception:
        try:
            return geom.wkb.hex()
        except Exception:
            return str(geom.bounds)


def _decode_coverage_geometry(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        if isinstance(value, (bytes, bytearray, memoryview)):
            return _wkb_loads(bytes(value))
        return _wkb_loads(bytes.fromhex(value))
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def _load_coverage(state_abbr: str):
    """Load raw cell_coverage/{STATE}.parquet rows; returns GeoDataFrame or None."""
    state_abbr = (state_abbr or '').strip().upper()
    if not state_abbr:
        return None
    path = os.path.join('cell_coverage', f'{state_abbr}.parquet')
    if not os.path.exists(path):
        return None
    try:
        try:
            df = pd.read_parquet(path, columns=['carrier', 'color', 'geometry_wkb'])
        except Exception:
            df = pd.read_parquet(path)
        df = df[['carrier', 'color', 'geometry_wkb']].copy()
        df['geometry'] = df['geometry_wkb'].apply(_decode_coverage_geometry)
        gdf = gpd.GeoDataFrame(df[['carrier', 'color']], geometry=df['geometry'], crs='EPSG:4326')
        return gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def _load_dissolved_coverage(state_abbr: str):
    """Load carrier-dissolved statewide coverage, used only for the full-map overlay."""
    state_abbr = (state_abbr or '').strip().upper()
    if not state_abbr:
        return None

    gdf = _load_coverage(state_abbr)
    if gdf is None or gdf.empty:
        return gdf

    dissolved_rows = []
    for (carrier, color), group in gdf.groupby(['carrier', 'color'], sort=False):
        geom = unary_union(group.geometry.tolist())
        if geom is None or geom.is_empty:
            continue
        try:
            geom = geom.simplify(0.0008, preserve_topology=True)
        except Exception:
            pass
        dissolved_rows.append({'carrier': carrier, 'color': color, 'geometry': geom})

    return gpd.GeoDataFrame(dissolved_rows, geometry='geometry', crs='EPSG:4326')


def add_coverage_traces(fig, state_abbr: str, visible=True):
    """Add AT&T / T-Mobile / Verizon 4G LTE polygon traces."""
    gdf = _load_dissolved_coverage(state_abbr)
    if gdf is None or gdf.empty:
        return

    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        carrier = row['carrier']
        color   = row['color']
        rings = []
        if geom.geom_type == 'Polygon':
            rings = [geom.exterior]
        elif geom.geom_type == 'MultiPolygon':
            rings = [p.exterior for p in geom.geoms]
        else:
            continue

        lons_all, lats_all = [], []
        for ring in rings:
            xs, ys = ring.coords.xy
            lons_all.extend(list(xs) + [None])
            lats_all.extend(list(ys) + [None])

        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        fig.add_trace(go.Scattermap(
            lon=lons_all, lat=lats_all,
            mode='lines', fill='toself',
            fillcolor=f"rgba({r},{g},{b},0.25)",
            line=dict(color=color, width=1),
            name=f"{carrier} 4G LTE",
            hoverinfo='name',
            visible=visible,
        ))


def _carrier_coverage_analysis(state_abbr: str, boundary_geom):
    """
    Intersects each carrier's coverage with the jurisdiction boundary.
    Returns list of dicts sorted by coverage % descending:
      {'carrier', 'color', 'pct', 'poly'}
    """
    if not state_abbr or boundary_geom is None or boundary_geom.is_empty:
        return []

    cache_key = ((state_abbr or '').strip().upper(), _coverage_geom_cache_key(boundary_geom))
    _analysis_cache = _get_coverage_analysis_cache()
    if cache_key in _analysis_cache:
        return _analysis_cache[cache_key]

    gdf = _load_coverage(state_abbr)
    if gdf is None or gdf.empty:
        return []

    boundary_area = boundary_geom.area
    if boundary_area <= 0:
        return []

    try:
        from shapely.geometry import box
        from shapely.prepared import prep
        bbox_geom = box(*boundary_geom.bounds)
        try:
            candidate_idx = gdf.sindex.query(bbox_geom, predicate='intersects')
            candidate_gdf = gdf.iloc[candidate_idx]
        except Exception:
            candidate_gdf = gdf[gdf.geometry.intersects(bbox_geom)]
        prepared_boundary = prep(boundary_geom)
    except Exception:
        candidate_gdf = gdf
        prepared_boundary = None

    carrier_meta = list(gdf[['carrier', 'color']].drop_duplicates().itertuples(index=False, name=None))
    clipped_by_carrier = {carrier: [] for carrier, _ in carrier_meta}

    for row in candidate_gdf.itertuples(index=False):
        poly = row.geometry
        if poly is None or poly.is_empty:
            continue
        try:
            if prepared_boundary is not None and not prepared_boundary.intersects(poly):
                continue
            clipped = poly.intersection(boundary_geom)
        except Exception:
            continue
        if clipped is not None and not clipped.is_empty:
            clipped_by_carrier.setdefault(row.carrier, []).append(clipped)

    results = []
    for carrier, color in carrier_meta:
        pieces = clipped_by_carrier.get(carrier) or []
        if not pieces:
            results.append({'carrier': carrier, 'color': color, 'pct': 0.0, 'poly': None})
            continue
        try:
            clipped = unary_union(pieces) if len(pieces) > 1 else pieces[0]
            try:
                clipped = clipped.simplify(0.0005, preserve_topology=True)
            except Exception:
                pass
            pct = min(100.0, clipped.area / boundary_area * 100)
        except Exception:
            clipped = None
            pct = 0.0
        results.append({'carrier': carrier, 'color': color, 'pct': pct, 'poly': clipped})

    results = sorted(results, key=lambda x: x['pct'], reverse=True)
    _analysis_cache[cache_key] = results
    return results


def _build_carrier_mini_map(cinfo, boundary_geom, center_lat, center_lon, zoom, map_style):
    """Build a small Plotly map showing jurisdiction boundary + one carrier's coverage."""
    fig = go.Figure()

    # Jurisdiction outline
    if boundary_geom is not None and not boundary_geom.is_empty:
        geoms = [boundary_geom] if isinstance(boundary_geom, Polygon) else list(boundary_geom.geoms)
        for gi, g in enumerate(geoms):
            bx, by = g.exterior.coords.xy
            fig.add_trace(go.Scattermap(
                mode='lines', lon=list(bx), lat=list(by),
                line=dict(color='#ffffff', width=1.5),
                showlegend=False, hoverinfo='skip'
            ))

    # Coverage fill
    poly = cinfo.get('poly')
    if poly is not None and not poly.is_empty:
        color = cinfo['color']
        r, g_c, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        rings = ([poly.exterior] if poly.geom_type == 'Polygon'
                 else [p.exterior for p in poly.geoms])
        lons, lats = [], []
        for ring in rings:
            xs, ys = ring.coords.xy
            lons.extend(list(xs) + [None])
            lats.extend(list(ys) + [None])
        fig.add_trace(go.Scattermap(
            lon=lons, lat=lats, mode='lines', fill='toself',
            fillcolor=f"rgba({r},{g_c},{b},0.40)",
            line=dict(color=color, width=1),
            showlegend=False, hoverinfo='skip'
        ))

    fig.update_layout(
        map=dict(center=dict(lat=center_lat, lon=center_lon),
                 zoom=max(8, zoom - 1), style=map_style),
        margin=dict(l=0, r=0, t=0, b=0),
        height=210, showlegend=False,
    )
    return fig


# ── RF Link Budget — 3390 MHz Friis free-space model ─────────────────────────

def _get_terrain_cache():
    """Global cache dict for DEM tiles to avoid re-downloading."""
    return {}

def calculate_zoom(min_lon, max_lon, min_lat, max_lat):
    lon_diff = max_lon - min_lon
    lat_diff = max_lat - min_lat
    if lon_diff <= 0 or lat_diff <= 0: return 12
    return min(max(min(np.log2(360/lon_diff), np.log2(180/lat_diff)) + 1.6, 5), 18)

def _df_latlon_signature(df):
    if df is None or len(df) == 0:
        return None
    if 'lat' not in df.columns or 'lon' not in df.columns:
        return ('missing-latlon', len(df), tuple(map(str, df.columns[:8])))

    coords = df[['lat', 'lon']].copy()
    coords['lat'] = pd.to_numeric(coords['lat'], errors='coerce')
    coords['lon'] = pd.to_numeric(coords['lon'], errors='coerce')
    coords = coords.dropna()
    if coords.empty:
        return ('empty', len(df))

    return (
        len(coords),
        round(float(coords['lat'].min()), 5),
        round(float(coords['lat'].max()), 5),
        round(float(coords['lon'].min()), 5),
        round(float(coords['lon'].max()), 5),
    )

def _jurisdiction_scan_signature(calls_df, shapefile_dir, preferred_shp=None):
    shp_meta = []
    for shp_path in sorted(glob.glob(os.path.join(shapefile_dir, "*.shp"))):
        try:
            _stat = os.stat(shp_path)
            shp_meta.append((os.path.basename(shp_path), int(_stat.st_mtime), _stat.st_size))
        except Exception:
            shp_meta.append((os.path.basename(shp_path), 0, 0))

    preferred_meta = None
    if preferred_shp:
        try:
            _pstat = os.stat(preferred_shp)
            preferred_meta = (preferred_shp, int(_pstat.st_mtime), _pstat.st_size)
        except Exception:
            preferred_meta = (preferred_shp, 0, 0)

    return (
        _df_latlon_signature(calls_df),
        tuple(shp_meta),
        preferred_meta,
    )

def get_relevant_jurisdictions_cached(calls_df, shapefile_dir, preferred_shp=None):
    cache_key = _jurisdiction_scan_signature(calls_df, shapefile_dir, preferred_shp)
    if st.session_state.get('_jurisdiction_scan_cache_key') == cache_key:
        cached = st.session_state.get('_jurisdiction_scan_cache_value')
        return cached.copy() if cached is not None else None

    result = find_relevant_jurisdictions(calls_df, shapefile_dir, preferred_shp=preferred_shp)
    st.session_state['_jurisdiction_scan_cache_key'] = cache_key
    st.session_state['_jurisdiction_scan_cache_value'] = result.copy() if result is not None else None
    return result

def find_relevant_jurisdictions(calls_df, shapefile_dir, preferred_shp=None):
    if calls_df is None:
        return None
    full_points = calls_df[['lat', 'lon']].copy()
    full_points = full_points[(full_points.lat.abs() > 1) & (full_points.lon.abs() > 1)]
    scan_points = full_points.sample(50000, random_state=42) if len(full_points) > 50000 else full_points
    points_gdf = gpd.GeoDataFrame(scan_points, geometry=gpd.points_from_xy(scan_points.lon, scan_points.lat), crs="EPSG:4326")
    total_bounds = points_gdf.total_bounds

    # Always scan all saved shapefiles in the directory so multi-jurisdiction
    # uploads show every boundary, not just the first one saved.
    shp_files = glob.glob(os.path.join(shapefile_dir, "*.shp"))
    # If no shapefiles exist at all and a preferred path was given, use just that
    if not shp_files and preferred_shp and os.path.exists(preferred_shp):
        shp_files = [preferred_shp]

    relevant_polys = []
    _calls_minx, _calls_miny, _calls_maxx, _calls_maxy = total_bounds
    for shp_path in shp_files:
        try:
            import fiona
            with fiona.open(shp_path) as _shp_src:
                _shp_bounds = _shp_src.bounds
            _no_overlap = (
                _shp_bounds[2] < _calls_minx or _shp_bounds[0] > _calls_maxx or
                _shp_bounds[3] < _calls_miny or _shp_bounds[1] > _calls_maxy
            )
            if _no_overlap:
                continue
        except Exception:
            pass

        try:
            gdf_chunk = gpd.read_file(shp_path, bbox=tuple(total_bounds))
            if not gdf_chunk.empty:
                if gdf_chunk.crs is None: gdf_chunk.set_crs(epsg=4269, inplace=True)
                gdf_chunk = gdf_chunk.to_crs(epsg=4326)
                hits = gpd.sjoin(gdf_chunk, points_gdf, how="inner", predicate="intersects")
                if not hits.empty:
                    subset = gdf_chunk.loc[hits.index.unique()].copy()
                    subset['data_count'] = hits.index.value_counts()
                    name_col = next((c for c in ['NAME','DISTRICT','NAMELSAD'] if c in subset.columns), subset.columns[0])
                    subset['DISPLAY_NAME'] = subset[name_col].astype(str)
                    relevant_polys.append(subset)
        except Exception: continue
    if not relevant_polys: return None
    master_gdf = pd.concat(relevant_polys, ignore_index=True).sort_values(by='data_count', ascending=False)
    master_gdf = master_gdf.dissolve(by='DISPLAY_NAME', aggfunc={'data_count': 'sum'}).reset_index()
    master_gdf = master_gdf.sort_values(by='data_count', ascending=False)
    if master_gdf['data_count'].sum() > 0:
        master_gdf['pct_share'] = master_gdf['data_count'] / master_gdf['data_count'].sum()
        master_gdf['cum_share'] = master_gdf['pct_share'].cumsum()
        mask = (master_gdf['cum_share'] <= 0.98) | (master_gdf['pct_share'] > 0.01)
        mask.iloc[0] = True
        return master_gdf[mask]
    return master_gdf

@st.cache_data(show_spinner=False)
def build_display_calls(df_calls_full, _city_m, epsg_code, max_points=300000, seed=42, bounds_hash=''):
    if df_calls_full is None or len(df_calls_full) == 0:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    df = df_calls_full.copy()
    if 'lat' not in df.columns or 'lon' not in df.columns:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
    df = df.dropna(subset=['lat', 'lon']).reset_index(drop=True)
    if df.empty:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")
    try:
        gdf_m = gdf.to_crs(epsg=int(epsg_code))
        # Buffer 300 m so calls at polygon edges aren't clipped by precision gaps
        # (especially common when switching to a county boundary)
        _clip_geom = _city_m.buffer(300) if _city_m is not None else None
        calls_in_city = gdf_m[gdf_m.within(_clip_geom)] if _clip_geom is not None else gdf_m
    except Exception:
        calls_in_city = gdf

    if calls_in_city.empty:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    if len(calls_in_city) <= max_points:
        return calls_in_city.to_crs(epsg=4326)

    sampled = calls_in_city.copy()
    minx, miny, maxx, maxy = sampled.total_bounds
    span_x = max(maxx - minx, 1.0)
    span_y = max(maxy - miny, 1.0)
    target_cells = max(25, int(np.sqrt(max_points) * 0.7))
    nx = max(25, min(120, target_cells))
    ny = max(25, min(120, int(target_cells * (span_y / span_x))))

    sampled['_gx'] = np.floor((sampled.geometry.x - minx) / span_x * nx).clip(0, nx - 1).astype(int)
    sampled['_gy'] = np.floor((sampled.geometry.y - miny) / span_y * ny).clip(0, ny - 1).astype(int)
    sampled['_cell'] = sampled['_gx'].astype(str) + '_' + sampled['_gy'].astype(str)

    counts = sampled['_cell'].value_counts()
    alloc = np.maximum(1, np.floor(counts / counts.sum() * max_points).astype(int))
    shortfall = int(max_points - alloc.sum())
    if shortfall > 0:
        remainders = (counts / counts.sum() * max_points) - np.floor(counts / counts.sum() * max_points)
        for cell in remainders.sort_values(ascending=False).index[:shortfall]:
            alloc.loc[cell] += 1

    parts = []
    for cell, group in sampled.groupby('_cell', sort=False):
        take = int(min(len(group), alloc.get(cell, 1)))
        if take >= len(group):
            parts.append(group)
        elif take > 0:
            parts.append(group.sample(take, random_state=seed))

    if not parts:
        display_calls = sampled.sample(max_points, random_state=seed)
    else:
        display_calls = pd.concat(parts, ignore_index=False)
        if len(display_calls) > max_points:
            display_calls = display_calls.sample(max_points, random_state=seed)

    display_calls = display_calls.drop(columns=['_gx', '_gy', '_cell'], errors='ignore')
    return display_calls.to_crs(epsg=4326)

# ============================================================
# PAGE CONFIG — must be the first Streamlit command
# ============================================================
st.set_page_config(
    layout="wide",
    page_title="BRINC Drone-as-First-Responder",
    page_icon="https://brincdrones.com/favicon.ico"
)

# ============================================================
# GOOGLE OAUTH LOGIN GATE
# ============================================================
# Activates only when [auth] section is present in secrets.toml.
# Falls through silently if auth is not configured (local dev without secrets).
try:
    if hasattr(st, 'user') and "auth" in st.secrets:
        if not st.user.is_logged_in:
            try:
                _logo_b64 = base64.b64encode(open("logo.png", "rb").read()).decode()
                _logo_tag = f'<img src="data:image/png;base64,{_logo_b64}" style="height:80px;object-fit:contain;" alt="BRINC">'
            except Exception:
                _logo_tag = '<div style="font-size:2rem;font-weight:900;color:#00D2FF;letter-spacing:4px;">BRINC DFR</div>'
            st.markdown(f"""
            <style>
            section[data-testid="stSidebar"] {{ display: none !important; }}
            [data-testid="collapsedControl"],
            [data-testid="stSidebarCollapsedControl"] {{ display: none !important; }}
            [data-testid="stAppViewContainer"] {{
                background: radial-gradient(ellipse at 50% 30%, #0d1b2e 0%, #060a12 70%) !important;
            }}
            [data-testid="block-container"] {{
                padding-top: 0 !important;
                padding-bottom: 0 !important;
                max-width: 100% !important;
            }}
            div[data-testid="stButton"] {{
                display: flex !important;
                justify-content: center !important;
                margin-top: 0 !important;
            }}
            div[data-testid="stButton"] > button {{
                background: linear-gradient(135deg, #0077b6, #00b4d8) !important;
                color: #fff !important;
                border: none !important;
                border-radius: 10px !important;
                padding: 13px 44px !important;
                font-size: 0.95rem !important;
                font-weight: 600 !important;
                letter-spacing: 0.6px !important;
                box-shadow: 0 4px 24px rgba(0,180,216,0.35) !important;
            }}
            div[data-testid="stButton"] > button:hover {{
                background: linear-gradient(135deg, #005f8a, #009dbf) !important;
                box-shadow: 0 6px 30px rgba(0,180,216,0.5) !important;
            }}
            </style>
            <div style="
                display:flex;flex-direction:column;align-items:center;justify-content:center;
                min-height:85vh;gap:0;
            ">
              <div style="
                background:rgba(255,255,255,0.03);
                border:1px solid rgba(255,255,255,0.08);
                border-radius:20px;
                padding:52px 64px 44px;
                display:flex;flex-direction:column;align-items:center;gap:18px;
                box-shadow:0 20px 60px rgba(0,0,0,0.6);
                backdrop-filter:blur(12px);
                min-width:340px;
              ">
                {_logo_tag}
                <div style="width:48px;height:2px;background:linear-gradient(90deg,transparent,#00b4d8,transparent);margin:2px 0;"></div>
                <div style="color:#8a9bb5;font-size:0.78rem;letter-spacing:2.5px;text-transform:uppercase;font-weight:500;">
                  Drone as First Responder &nbsp;·&nbsp; Optimizer
                </div>
                <div style="height:12px;"></div>
              </div>
            </div>
            """, unsafe_allow_html=True)
            st.button("Sign in with Google", on_click=st.login, args=("google",),
                      type="primary", width="content")
            st.html("""
<script>
(function() {
    var sel = [
        'header', '[data-testid="stHeader"]', '[data-testid="stToolbar"]',
        '[data-testid="stDecoration"]', '[data-testid="stStatusWidget"]',
        '[data-testid="stGithubButton"]', '[data-testid="stActionButton"]',
        '[data-testid="stBaseButton-header"]', '[data-testid="stHeaderActionElements"]',
        '[data-testid="stHeaderActions"]', '[data-testid="stDeployButton"]',
        '[data-testid="stAppDeployButton"]', '.stDeployButton',
        '.viewerBadge_container__', '.viewerBadge_link__', '.viewerBadge_text__',
        '#MainMenu', 'footer', 'iframe[title="streamlit_analytics"]',
        'header a[href*="github.com"]', 'header a[href*="streamlit.io"]',
        'header [aria-label*="GitHub"]', 'header [aria-label*="github"]',
        'header [aria-label*="Streamlit"]', 'header [title*="GitHub"]',
        'header [title*="github"]', 'header [title*="Streamlit"]',
        'button[title*="GitHub"]', 'button[title*="github"]'
    ];
    function sweep(root) {
        if (!root) return;
        try {
            sel.forEach(function(s) {
                root.querySelectorAll(s).forEach(function(el) {
                    el.remove();
                });
            });
            root.querySelectorAll('*').forEach(function(el) {
                if (el.shadowRoot) {
                    sweep(el.shadowRoot);
                }
            });
        } catch(e) {}
    }
    function hide() {
        try {
            sweep(window.parent.document);
        } catch(e) {}
    }
    hide();
    try {
        new MutationObserver(hide).observe(window.parent.document.body, {childList:true, subtree:true});
    } catch(e) {}
    try {
        setInterval(hide, 1000);
    } catch(e) {}
})();
</script>
""", unsafe_allow_javascript=True)
            st.stop()

        # ── Restrict to @brincdrones.com accounts ──────────────────────────
        _user_email = getattr(st.user, "email", "") or ""
        if not _user_email.lower().endswith("@brincdrones.com"):
            st.markdown(
                "<style>section[data-testid='stSidebar'] { display: none !important; }</style>",
                unsafe_allow_html=True
            )
            st.error(
                f"Access restricted to BRINC Drones employees.\n\n"
                f"You are signed in as **{_user_email}**.\n\n"
                "Please sign in with your @brincdrones.com account."
            )
            st.button("Sign out", on_click=st.logout)
            st.stop()

        # ── Populate session state from OAuth identity ──────────────────────
        _authed_email = getattr(st.user, "email", "") or ""
        _authed_name  = getattr(st.user, "name",  "") or _authed_email.split("@")[0]
        if not st.session_state.get('_oauth_logged', False):
            st.session_state['google_user_email'] = _authed_email
            st.session_state['google_user_name']  = _authed_name
            # Derive brinc_user (first.last prefix) from email for backwards compatibility
            _prefix = _authed_email.split("@")[0]
            st.session_state['brinc_user'] = _prefix
            st.session_state['_oauth_logged'] = True
            try:
                _log_login_to_sheets(_authed_email, _authed_name)
            except Exception:
                pass

except Exception:
    pass  # Auth not configured — app runs without login gate

# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================
# This MUST run before any st.session_state checks to prevent KeyError
init_session_state(st.session_state, _slugify, _build_public_report_url)

# ============================================================
# APP FLOW
# ============================================================

def main():
    _render_in_app_faq()
    _render_in_app_faq()
    
    # Route based on data state
    if not st.session_state['csvs_ready']:
        render_onboarding_page()
    else:
        render_simulation_page()
    log_to_sheets=_log_to_sheets,
    notify_email=_notify_email,
)

main()



