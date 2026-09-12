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
