"""Canadian jurisdiction lookups: postal code, boundary, and population resolution.

Mirrors the US functions in modules/boundaries.py, backed by bundled StatCan
data, so callers can dispatch by region abbreviation without duplicating
StatCan-specific logic in every US call site.
"""
import os
import re
import json
import urllib.request

import streamlit as st
import geopandas as gpd
from shapely.geometry import Point

from modules.config import PROVINCE_FIPS

US_ZIP_RE = re.compile(r'^\d{5}(-\d{4})?$')
CA_POSTAL_RE = re.compile(r'^[A-Za-z]\d[A-Za-z]\s?\d?[A-Za-z]?\d?$')

_CA_NAME_SUFFIXES = (
    ' regional municipality', ' district municipality', ' rural municipality',
    ' county', ' municipality', ' township', ' village', ' town', ' city',
    ' parish', ' canton', ' ville',
)


def is_ca_region(state_or_province_abbr):
    """True if the given 2-letter region code is a Canadian province/territory."""
    return str(state_or_province_abbr or '').strip().upper() in PROVINCE_FIPS


def detect_country_from_postal(code):
    """Classify a postal/ZIP code string as 'US', 'CA', or None if unrecognized."""
    code = str(code or '').strip()
    if US_ZIP_RE.match(code):
        return 'US'
    if CA_POSTAL_RE.match(code):
        return 'CA'
    return None


def lookup_postal_code_ca(postal_code: str):
    """
    Look up a Canadian postal code (or bare FSA) and return
    (city, province_abbr, province_name) using the free Zippopotam.us API —
    the same provider already used for US ZIP lookups. Only the Forward
    Sortation Area (first 3 characters) is significant to the API.
    Returns (None, None, None) on failure or non-Canadian input.
    """
    postal_code = re.sub(r'\s+', '', str(postal_code or '')).upper()
    if not CA_POSTAL_RE.match(postal_code):
        return None, None, None
    fsa = postal_code[:3]
    try:
        url = f"https://api.zippopotam.us/ca/{fsa}"
        req = urllib.request.Request(url, headers={'User-Agent': 'BRINC_COS_Optimizer/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        place = data['places'][0]
        city = place['place name']
        province = place['state abbreviation']
        return city, province, place.get('state', '')
    except Exception:
        return None, None, None


def _normalize_ca_name(name):
    text = str(name or '').lower().strip()
    text = re.sub(r'[^a-z0-9\s-]', ' ', text)
    for suffix in _CA_NAME_SUFFIXES:
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
            break
    return re.sub(r'\s+', ' ', text).strip()


def _match_ca_boundary_rows(gdf, pruid, search_name):
    province_rows = gdf[gdf['PRUID'].astype(str) == str(pruid)].copy()
    if province_rows.empty:
        return None
    province_rows['_norm_name'] = province_rows['NAME'].astype(str).apply(_normalize_ca_name)
    match = province_rows[province_rows['_norm_name'] == search_name]
    if match.empty:
        match = province_rows[province_rows['_norm_name'].str.startswith(search_name)]
        if not match.empty:
            match = match.copy()
            match['_diff'] = match['NAME'].astype(str).str.len() - len(search_name)
            match = match.sort_values('_diff').head(1)
    return match if not match.empty else None


@st.cache_data
def fetch_cd_boundary_local(province_abbr, cd_name_input):
    """Look up a Census Division boundary from the bundled cd_lite.parquet."""
    pruid = PROVINCE_FIPS.get(str(province_abbr or '').strip().upper())
    if not pruid or not os.path.exists("cd_lite.parquet"):
        return False, None
    search_name = _normalize_ca_name(cd_name_input)
    try:
        gdf = gpd.read_parquet("cd_lite.parquet")
        match = _match_ca_boundary_rows(gdf, pruid, search_name)
        if match is not None and not match.empty:
            return True, match[["NAME", "geometry"]]
    except Exception as e:
        print(f"[BRINC] fetch_cd_boundary_local failed: {e}")
    return False, None


@st.cache_data
def fetch_csd_boundary_local(province_abbr, csd_name_input):
    """Look up a Census Subdivision (city/town/municipality) boundary from csd_lite.parquet."""
    pruid = PROVINCE_FIPS.get(str(province_abbr or '').strip().upper())
    if not pruid or not os.path.exists("csd_lite.parquet"):
        return False, None
    search_name = _normalize_ca_name(csd_name_input)
    try:
        gdf = gpd.read_parquet("csd_lite.parquet")
        match = _match_ca_boundary_rows(gdf, pruid, search_name)
        if match is not None and not match.empty:
            return True, match[["NAME", "geometry"]]
    except Exception as e:
        print(f"[BRINC] fetch_csd_boundary_local failed: {e}")
    return False, None


def fetch_cd_by_centroid(df_calls, province_abbr):
    """Find the CD boundary containing the median centroid of the call data."""
    pruid = PROVINCE_FIPS.get(str(province_abbr or '').strip().upper())
    if not pruid or not os.path.exists("cd_lite.parquet"):
        return False, None
    try:
        lat = float(df_calls['lat'].dropna().median())
        lon = float(df_calls['lon'].dropna().median())
    except Exception:
        return False, None
    try:
        gdf = gpd.read_parquet("cd_lite.parquet")
        province_rows = gdf[gdf['PRUID'].astype(str) == str(pruid)].copy()
        if province_rows.empty:
            return False, None
        pt = Point(lon, lat)
        containing = province_rows[province_rows.geometry.contains(pt)]
        if containing.empty:
            province_rows['_dist'] = province_rows.geometry.distance(pt)
            containing = province_rows.nsmallest(1, '_dist')
        if not containing.empty:
            return True, containing[['NAME', 'geometry']].copy()
    except Exception as e:
        print(f"[BRINC] fetch_cd_by_centroid failed: {e}")
    return False, None


def fetch_ca_population(province_abbr, name, boundary_kind='place'):
    """Look up bundled StatCan population for a province, CD, or CSD."""
    pruid = PROVINCE_FIPS.get(str(province_abbr or '').strip().upper())
    if not pruid:
        return None
    file_for_kind = {
        'state': 'provinces_lite.parquet',
        'county': 'cd_lite.parquet',
        'place': 'csd_lite.parquet',
    }.get(boundary_kind, 'csd_lite.parquet')
    if not os.path.exists(file_for_kind):
        return None
    try:
        gdf = gpd.read_parquet(file_for_kind)
        if boundary_kind == 'state':
            match = gdf[gdf['PRUID'].astype(str) == str(pruid)]
        else:
            match = _match_ca_boundary_rows(gdf, pruid, _normalize_ca_name(name))
        if match is not None and not match.empty:
            return int(match.iloc[0]['POPULATION'])
    except Exception as e:
        print(f"[BRINC] fetch_ca_population failed: {e}")
    return None
