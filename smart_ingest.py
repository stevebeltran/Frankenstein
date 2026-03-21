"""
smart_ingest.py — BRINC Drones · Smart CAD File Ingestion Engine  v2.0
=======================================================================
Drop-in replacement for the manual CSV uploader in the BRINC COS
Optimizer (app.py).  Handles the full range of real-world CAD export
formats with zero configuration from the user:

  FORMAT A  Standard lat/lon columns  (any casing / abbreviation)
  FORMAT B  Separate address columns  (street + city + state + zip)
  FORMAT C  Single combined address   ("123 Main St, Orlando FL 32801")
  FORMAT D  Intersection format       ("Main St & Oak Ave, Orlando FL")
  FORMAT E  Block-level address       ("100 Block of Main St, Orlando FL")
  FORMAT F  X/Y projected coordinates (State Plane, UTM, Web Mercator)

Column detection — two-stage pipeline:
  Stage 1  Regex heuristics  (fast, covers ~95 % of real CAD exports)
  Stage 2  TF-IDF + Logistic Regression on char-level n-grams (fallback)

Confidence-gated UI:
  HIGH confidence  → badges shown, mapping panel collapsed (silent)
  LOW confidence   → mapping panel forced open, user must confirm

Station auto-fetch when no stations file is uploaded:
  1. Try OSM Overpass API  (real police / fire / EMS)
  2. Fall back to 100 synthetic stations uniformly distributed

Integration — replace the entire `with path_upload_col:` block in app.py:

    from smart_ingest import render_smart_uploader

    with path_upload_col:
        render_smart_uploader(
            accent_color=accent_color,
            text_muted=text_muted,
            card_bg=card_bg,
            card_border=card_border,
        )
"""

from __future__ import annotations

import io
import json
import math
import random
import re
import time
import urllib.parse
import urllib.request
import warnings
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

warnings.filterwarnings("ignore")

# ───────────────────────────────────────────────────────────────
# TYPE ALIASES
# ───────────────────────────────────────────────────────────────
ClassifyResult = dict[str, str]    # col_name  → semantic label
ConfidenceMap  = dict[str, float]  # col_name  → 0.0–1.0

# ───────────────────────────────────────────────────────────────
# CONSTANTS
# ───────────────────────────────────────────────────────────────
_COORD_LABELS      = {"lat", "lon", "x_proj", "y_proj", "address"}
_HIGH_CONF         = 0.75   # ML must beat this to assign silently
_LOW_CONF          = 0.55   # below this → always show review UI
_LABEL_OPTIONS     = ["lat","lon","x_proj","y_proj","address","city",
                      "state","zip","priority","nature","date","ignore"]
_LABEL_ICONS       = {
    "lat":"🌐 Latitude","lon":"🌐 Longitude",
    "x_proj":"📐 X (projected)","y_proj":"📐 Y (projected)",
    "address":"📍 Address","city":"🏙 City","state":"🗺 State",
    "zip":"📮 ZIP","priority":"🚨 Priority",
    "nature":"📋 Call Type","date":"📅 Date/Time","ignore":"— ignore",
}
_CONF_COLOR        = {"HIGH":"#00D2FF","MEDIUM":"#FFD700","LOW":"#FF4B4B"}
_US_STATES         = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN",
    "IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV",
    "NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN",
    "TX","UT","VT","VA","WA","WV","WI","WY","DC",
}

# ═══════════════════════════════════════════════════════════════
# §1  COLUMN CLASSIFIER
# ═══════════════════════════════════════════════════════════════

_TRAIN: list[tuple[str, str]] = [
    # latitude
    ("lat","lat"),("latitude","lat"),("y_coord","lat"),("y","lat"),
    ("incident_lat","lat"),("call_lat","lat"),("gps_lat","lat"),
    ("lat_decimal","lat"),("ycoord","lat"),("ylat","lat"),
    ("geoy","lat"),("northing_dd","lat"),("lat_deg","lat"),
    ("y_wgs84","lat"),("lat_dd","lat"),("map_lat","lat"),("scene_lat","lat"),
    # longitude
    ("lon","lon"),("lng","lon"),("longitude","lon"),("x_coord","lon"),
    ("x","lon"),("incident_lon","lon"),("call_lon","lon"),("gps_lon","lon"),
    ("lon_decimal","lon"),("xcoord","lon"),("xlon","lon"),
    ("geox","lon"),("easting_dd","lon"),("lon_deg","lon"),
    ("x_wgs84","lon"),("lon_dd","lon"),("map_lon","lon"),("scene_lon","lon"),
    # projected X (needs reprojection)
    ("easting","x_proj"),("state_plane_x","x_proj"),("utm_e","x_proj"),
    ("x_sp","x_proj"),("xsp","x_proj"),("sp_e","x_proj"),
    ("x_meters","x_proj"),("x_feet","x_proj"),("x_ft","x_proj"),
    ("sp_x","x_proj"),("map_x","x_proj"),("x_nad83","x_proj"),
    # projected Y
    ("northing","y_proj"),("state_plane_y","y_proj"),("utm_n","y_proj"),
    ("y_sp","y_proj"),("ysp","y_proj"),("sp_n","y_proj"),
    ("y_meters","y_proj"),("y_feet","y_proj"),("y_ft","y_proj"),
    ("sp_y","y_proj"),("map_y","y_proj"),("y_nad83","y_proj"),
    # street address
    ("address","address"),("street","address"),("location","address"),
    ("incident_address","address"),("call_address","address"),
    ("addr","address"),("full_address","address"),("site_address","address"),
    ("premise_address","address"),("dispatch_address","address"),
    ("blk_addr","address"),("block_address","address"),
    ("street_address","address"),("scene_address","address"),
    ("geo_address","address"),("address_1","address"),("addr1","address"),
    # city
    ("city","city"),("incident_city","city"),("call_city","city"),
    ("municipality","city"),("place","city"),("town","city"),
    ("city_name","city"),("jurisdiction","city"),
    # state
    ("state","state"),("st","state"),("incident_state","state"),
    ("state_code","state"),("state_abbr","state"),
    # zip
    ("zip","zip"),("zipcode","zip"),("zip_code","zip"),
    ("postal","zip"),("postal_code","zip"),("zip4","zip"),
    # priority
    ("priority","priority"),("call_priority","priority"),
    ("incident_priority","priority"),("pri","priority"),
    ("urgency","priority"),("level","priority"),("severity","priority"),
    ("calltype_priority","priority"),("ems_priority","priority"),
    ("response_priority","priority"),("prio","priority"),
    ("response_level","priority"),("priority_code","priority"),
    # call type / nature
    ("nature","nature"),("call_type","nature"),("calltype","nature"),
    ("type","nature"),("incident_type","nature"),("call_nature","nature"),
    ("description","nature"),("desc","nature"),("offense","nature"),
    ("event_type","nature"),("rms_type","nature"),("call_desc","nature"),
    ("nature_code","nature"),("problem","nature"),("call_reason","nature"),
    ("disposition","nature"),("call_category","nature"),
    # date / time
    ("date","date"),("datetime","date"),("call_date","date"),
    ("incident_date","date"),("reported_date","date"),
    ("call_time","date"),("occurred_date","date"),
    ("dispatch_date","date"),("entry_date","date"),
    ("received_dttm","date"),("received_date","date"),
    ("call_received","date"),("time_received","date"),
    ("incident_datetime","date"),("event_date","date"),("dispatch","date"),
    # ignore
    ("id","ignore"),("incident_id","ignore"),("run_num","ignore"),
    ("case_num","ignore"),("record_id","ignore"),("objectid","ignore"),
    ("shape","ignore"),("geometry","ignore"),("globalid","ignore"),
    ("fid","ignore"),("oid","ignore"),("gid","ignore"),
    ("cad_incident_id","ignore"),("master_incident_number","ignore"),
]


@st.cache_resource
def _get_classifier() -> Pipeline:
    names, labels = zip(*_TRAIN)
    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(2,4), min_df=1)),
        ("clf",   LogisticRegression(max_iter=600, C=5.0, class_weight="balanced")),
    ])
    pipe.fit(list(names), list(labels))
    return pipe


# ═══════════════════════════════════════════════════════════════
# §2  HEURISTIC RULES
# ═══════════════════════════════════════════════════════════════

_RE_LAT   = re.compile(r"\b(lat(itude)?|geoy|ylat|y_wgs84|y_4326)\b", re.I)
_RE_LON   = re.compile(r"\b(lo?ng?(itude)?|geox|xlon|x_wgs84|x_4326)\b", re.I)
_RE_XPROJ = re.compile(r"\b(easting|utm_?e|state_?plane_?x|sp_?[ex]|xsp|x_?sp|x_?ft|x_?feet|x_?meters|x_?nad|map_?x)\b", re.I)
_RE_YPROJ = re.compile(r"\b(northing|utm_?n|state_?plane_?y|sp_?[ny]|ysp|y_?sp|y_?ft|y_?feet|y_?meters|y_?nad|map_?y)\b", re.I)
_RE_XCOORD = re.compile(r"\bx_?coord(inate)?\b", re.I)   # ambiguous — resolve by values below
_RE_YCOORD = re.compile(r"\by_?coord(inate)?\b", re.I)   # ambiguous — resolve by values below
_RE_ADDR  = re.compile(r"\b(addr(ess)?|street|location|premise|dispatch_addr|site_addr|block_addr|blk_addr|full_addr|scene_addr)\b", re.I)
_RE_CITY  = re.compile(r"\b(city|municipality|place|town|jurisdiction)\b", re.I)
_RE_STATE = re.compile(r"\b(state(_?(code|abbr))?)\b", re.I)
_RE_ZIP   = re.compile(r"\b(zip(_?code)?|postal(_?code)?|zip4)\b", re.I)
_RE_PRI   = re.compile(r"\b(priority|prio|pri|urgency|severity|response_level)\b", re.I)
_RE_NAT   = re.compile(r"\b(nature|call_?type|calltype|type|incident_?type|event_?type|offense|problem|call_reason|call_category)\b", re.I)
_RE_DATE  = re.compile(r"(date|datetime|received|dispatch|occurred|reported|entry_date|event_date|call_date|incident_date|call_time|incident_time)", re.I)
_RE_JUNK  = re.compile(r"\b(objectid|globalid|shape|geometry|fid|oid|gid|master_incident)\b", re.I)


def _heuristic_classify(col: str, series: "Optional[pd.Series]" = None) -> Optional[str]:
    c = col.strip().lower().replace(" ","_").replace("-","_")
    if _RE_JUNK.search(c):   return "ignore"
    if _RE_LAT.search(c):    return "lat"
    if _RE_LON.search(c):    return "lon"
    if _RE_XPROJ.search(c):  return "x_proj"
    if _RE_YPROJ.search(c):  return "y_proj"
    # X-Coordinate / Y-Coordinate are ambiguous — use actual values to decide
    if _RE_XCOORD.search(c):
        if series is not None and _looks_like_lon(series):      return "lon"
        if series is not None and _looks_like_projected(series): return "x_proj"
        return "lon"   # safe default: assume decimal degrees
    if _RE_YCOORD.search(c):
        if series is not None and _looks_like_lat(series):      return "lat"
        if series is not None and _looks_like_projected(series): return "y_proj"
        return "lat"   # safe default: assume decimal degrees
    if _RE_ADDR.search(c):   return "address"
    if _RE_CITY.search(c):   return "city"
    if _RE_STATE.search(c) and len(c) <= 12: return "state"
    if _RE_ZIP.search(c):    return "zip"
    if _RE_PRI.search(c):    return "priority"
    if _RE_NAT.search(c):    return "nature"
    if _RE_DATE.search(c):   return "date"
    return None


# ═══════════════════════════════════════════════════════════════
# §3  FULL CLASSIFICATION  →  mapping + per-column confidence
# ═══════════════════════════════════════════════════════════════

def classify_columns(df: pd.DataFrame) -> tuple[ClassifyResult, ConfidenceMap]:
    clf = _get_classifier()
    mapping:     ClassifyResult = {}
    confidences: ConfidenceMap  = {}

    for col in df.columns:
        # Pass the actual column values so ambiguous names (X-Coordinate, Y-Coordinate)
        # can be resolved by inspecting whether values look like degrees or projected units
        label = _heuristic_classify(col, df[col])
        if label == "ignore":
            confidences[col] = 1.0
            continue
        if label is not None:
            if label not in mapping.values():
                mapping[col]     = label
                confidences[col] = 1.0
        else:
            c_norm   = col.strip().lower().replace(" ","_").replace("-","_")
            proba    = _get_classifier().predict_proba([c_norm])[0]
            best_p   = float(max(proba))
            pred     = clf.classes_[int(np.argmax(proba))]
            confidences[col] = best_p
            if best_p >= _LOW_CONF and pred != "ignore":
                if pred not in mapping.values():
                    mapping[col] = pred

    # ── KEY RULE: if lat+lon are present, drop address to avoid geocoding ──
    has_latlon = "lat" in mapping.values() and "lon" in mapping.values()
    if has_latlon:
        mapping = {c: l for c, l in mapping.items() if l != "address"}

    return mapping, confidences


def _is_high_confidence(mapping: ClassifyResult, confidences: ConfidenceMap) -> bool:
    coord = set(mapping.values()) & _COORD_LABELS
    if not coord:
        return False
    has_latlon  = "lat" in coord and "lon" in coord
    has_proj    = "x_proj" in coord and "y_proj" in coord
    has_address = "address" in coord
    if not (has_latlon or has_proj or has_address):
        return False
    for col in mapping:
        if confidences.get(col, 0.0) < _HIGH_CONF:
            return False
    return True


# ═══════════════════════════════════════════════════════════════
# §4  VALUE-LEVEL SNIFF HELPERS
# ═══════════════════════════════════════════════════════════════

def _looks_like_lat(s: pd.Series) -> bool:
    # Threshold 0.60: real CAD files often have 30-40% garbage rows mixed into
    # coordinate columns (e.g. address strings, notes, blank rows). We only
    # evaluate rows that parse as numeric, then check that >=60% are plausible lats.
    v = pd.to_numeric(s, errors="coerce").dropna()
    if len(v) < 5: return False
    return bool((v.abs() <= 90).mean() > 0.60 and (v.abs() > 0.01).mean() > 0.60)

def _looks_like_lon(s: pd.Series) -> bool:
    v = pd.to_numeric(s, errors="coerce").dropna()
    if len(v) < 5: return False
    return bool((v.abs() <= 180).mean() > 0.60 and (v.abs() > 0.01).mean() > 0.60)

def _looks_like_projected(s: pd.Series) -> bool:
    v = pd.to_numeric(s, errors="coerce").dropna()
    return len(v) >= 5 and bool((v.abs() > 1_000).mean() > 0.8)


# ═══════════════════════════════════════════════════════════════
# §5  ADDRESS NORMALIZATION
#     Handles all four address formats before Nominatim geocoding.
# ═══════════════════════════════════════════════════════════════

_RE_INTERSECTION  = re.compile(r"\s+(?:and|&|@|/|\\|at)\s+", re.I)
_RE_BLOCK         = re.compile(r"^(\d+)\s+(?:blk|block)\s+(?:of\s+)?(.+)$", re.I)
_RE_LEADING_JUNK  = re.compile(r"^(?:call\s+at|incident\s+at|response\s+to|reported\s+at|scene\s+at)\s+", re.I)
_RE_TRAILING_CSZ  = re.compile(r",\s*([^,]+),\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)?$")
_RE_TRAILING_SZ   = re.compile(r",\s*([^,]+)\s+([A-Z]{2})\s*(\d{5}(?:-\d{4})?)?$")


def normalize_address(raw: str, city_hint: str = "", state_hint: str = "") -> str:
    """
    Normalize any CAD address format into a clean Nominatim-ready string.

    Examples
    --------
    "100 Block of Main St, Orlando FL"  → "100 Main St, Orlando FL"
    "Main St & Oak Ave, Orlando FL"     → "Main St and Oak Ave, Orlando FL"
    "CALL AT 123 Main St"               → "123 Main St"
    "123 Main St" (+ hints Orlando, FL) → "123 Main St, Orlando, FL"
    """
    addr = str(raw or "").strip()
    if not addr or addr.lower() in ("nan","none","unknown",""):
        return ""

    # 1. Strip leading CAD phrases
    addr = _RE_LEADING_JUNK.sub("", addr).strip()

    # 2. Block-level: "100 Block of Main St …" → "100 Main St …"
    street_part = addr.split(",")[0].strip()
    m = _RE_BLOCK.match(street_part)
    if m:
        blk  = (int(m.group(1)) // 100) * 100
        rest = m.group(2).strip()
        tail = (",".join(addr.split(",")[1:])).strip().lstrip(",").strip()
        addr = f"{blk} {rest}" + (f", {tail}" if tail else "")

    # 3. Intersection: "Main St & Oak Ave" → "Main St and Oak Ave"
    #    Nominatim understands "X and Y" for intersections
    street_part = addr.split(",")[0]
    if _RE_INTERSECTION.search(street_part):
        normalized = _RE_INTERSECTION.sub(" and ", street_part).strip()
        tail       = ",".join(addr.split(",")[1:])
        addr       = normalized + ("," + tail if tail else "")

    # 4. Append city/state hints if nothing is already there
    has_state = bool(re.search(r",\s*[A-Z]{2}(\s+\d{5})?$", addr))
    if not has_state:
        hints = [p for p in (city_hint, state_hint) if p and p.lower() not in ("nan","")]
        if hints:
            addr = addr.rstrip(", ") + ", " + ", ".join(hints)

    return addr.strip()


def _split_combined_address(addr: str) -> tuple[str, str, str]:
    """
    Try to split "123 Main St, Orlando, FL 32801" into (street, city, state).
    Returns (addr, "", "") if split fails.
    """
    for pat in (_RE_TRAILING_CSZ, _RE_TRAILING_SZ):
        m = pat.search(addr)
        if m:
            city  = m.group(1).strip()
            state = m.group(2).strip().upper()
            if state in _US_STATES:
                street = addr[:m.start()].strip().rstrip(",")
                return street, city, state
    return addr, "", ""


# ═══════════════════════════════════════════════════════════════
# §6  PROJECTED COORDINATE REPROJECTION
# ═══════════════════════════════════════════════════════════════

def _detect_epsg(x_arr: np.ndarray, y_arr: np.ndarray) -> Optional[int]:
    xm, ym = float(np.median(x_arr)), float(np.median(y_arr))
    if abs(xm) > 1_000_000 and abs(ym) > 1_000_000:
        return 3857                                  # Web Mercator
    if 100_000 < xm < 900_000 and 0 < ym < 10_000_000:
        zone = 17 if ym > 3_000_000 else 14         # UTM guess
        return int(f"326{zone}")
    if 200_000 < xm < 3_500_000 and 0 < ym < 1_500_000:
        return 2248                                  # FL East State Plane (feet)
    return None


def _project_to_wgs84(x: np.ndarray, y: np.ndarray, epsg: int) -> tuple[np.ndarray, np.ndarray]:
    try:
        from pyproj import Transformer
        t = Transformer.from_crs(epsg, 4326, always_xy=True)
        return t.transform(x, y)
    except ImportError:
        pass

    if epsg == 3857:
        lons = x / 20_037_508.34 * 180
        lats = np.degrees(2*np.arctan(np.exp(y/20_037_508.34*math.pi)) - math.pi/2)
        return lons, lats

    if str(epsg).startswith(("326","327")):
        zone   = int(str(epsg)[3:])
        hemi_n = str(epsg).startswith("326")
        a, e2  = 6_378_137.0, 0.006_694_379_990_14
        k0, E0 = 0.9996, 500_000.0
        N0     = 0.0 if hemi_n else 10_000_000.0
        lon0   = math.radians(-183 + zone*6)
        lats_o, lons_o = [], []
        for xi, yi in zip(x.astype(float), y.astype(float)):
            e  = xi - E0;  n = yi - N0
            M  = n / k0
            mu = M / (a*(1-e2/4-3*e2**2/64-5*e2**3/256))
            e1 = (1-math.sqrt(1-e2))/(1+math.sqrt(1-e2))
            p1 = (mu+(3*e1/2-27*e1**3/32)*math.sin(2*mu)
                  +(21*e1**2/16-55*e1**4/32)*math.sin(4*mu)
                  +(151*e1**3/96)*math.sin(6*mu))
            N1 = a/math.sqrt(1-e2*math.sin(p1)**2)
            T1 = math.tan(p1)**2
            C1 = e2/(1-e2)*math.cos(p1)**2
            R1 = a*(1-e2)/(1-e2*math.sin(p1)**2)**1.5
            D  = e/(N1*k0)
            lat_r = p1-(N1*math.tan(p1)/R1)*(D**2/2-(5+3*T1+10*C1-4*C1**2-9*e2)*D**4/24)
            lon_r = lon0+(D-(1+2*T1+C1)*D**3/6)/math.cos(p1)
            lats_o.append(math.degrees(lat_r))
            lons_o.append(math.degrees(lon_r))
        return np.array(lons_o), np.array(lats_o)

    # Last resort: assume feet, convert to meters, retry as UTM 17N
    return _project_to_wgs84(x*0.3048, y*0.3048, 32617)


# ═══════════════════════════════════════════════════════════════
# §7  NOMINATIM GEOCODING  (throttled, all 4 address formats)
# ═══════════════════════════════════════════════════════════════

def _nominatim_geocode(address: str, city: str="", state: str="", zip_: str="") -> tuple[Optional[float], Optional[float]]:
    parts = [p for p in [address, city, state, zip_] if p and p.lower() not in ("nan","none","")]
    if not parts:
        return None, None
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q":", ".join(parts),"format":"json","limit":1,"countrycodes":"us"}
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"BRINC_COS_Optimizer/2.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            data = json.loads(r.read())
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None, None


def _batch_geocode(
    df: pd.DataFrame,
    mapping: ClassifyResult,
    max_rows: int = 5_000,
    progress_cb=None,
) -> pd.DataFrame:
    addr_col  = next((c for c,l in mapping.items() if l=="address"), None)
    city_col  = next((c for c,l in mapping.items() if l=="city"),    None)
    state_col = next((c for c,l in mapping.items() if l=="state"),   None)
    zip_col   = next((c for c,l in mapping.items() if l=="zip"),     None)
    if addr_col is None:
        return df

    sample = df.head(max_rows).copy()
    total  = len(sample)
    lats, lons = [], []

    for i, (_, row) in enumerate(sample.iterrows()):
        raw   = str(row.get(addr_col)  or "")
        city  = str(row.get(city_col)  or "") if city_col  else ""
        state = str(row.get(state_col) or "") if state_col else ""
        zip_  = str(row.get(zip_col)   or "") if zip_col   else ""

        # Try to split city/state from combined address when not in separate columns
        if not city and not state:
            raw, city, state = _split_combined_address(raw)

        clean = normalize_address(raw, city_hint=city, state_hint=state)
        if not clean:
            lats.append(None); lons.append(None)
        else:
            lat, lon = _nominatim_geocode(clean, city, state, zip_)
            lats.append(lat); lons.append(lon)

        if progress_cb and i % 10 == 0:
            progress_cb(i / total)
        time.sleep(1.05)

    out = sample.copy()
    out["lat"] = lats
    out["lon"] = lons
    return out.dropna(subset=["lat","lon"]).reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════
# §8  STATION AUTO-FETCH  (Overpass → synthetic fallback)
# ═══════════════════════════════════════════════════════════════

def _fetch_osm_stations(minx: float, miny: float, maxx: float, maxy: float, pad: float=0.08) -> pd.DataFrame:
    b = f"{miny-pad},{minx-pad},{maxy+pad},{maxx+pad}"
    q = (f"[out:json][timeout:20];("
         f'node["amenity"="police"]({b});way["amenity"="police"]({b});'
         f'node["amenity"="fire_station"]({b});way["amenity"="fire_station"]({b});'
         f'node["emergency"="ambulance_station"]({b});way["emergency"="ambulance_station"]({b});'
         f");out center;")
    _TM = {"police":"Police","fire_station":"Fire","ambulance_station":"EMS"}
    try:
        req = urllib.request.Request("https://overpass-api.de/api/interpreter",
                                     data=q.encode("utf-8"),
                                     headers={"User-Agent":"BRINC_COS_Optimizer/2.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        rows = []
        for el in data.get("elements",[]):
            lat = el.get("lat") or el.get("center",{}).get("lat")
            lon = el.get("lon") or el.get("center",{}).get("lon")
            if not lat or not lon: continue
            tags    = el.get("tags",{})
            amenity = tags.get("amenity", tags.get("emergency",""))
            stype   = _TM.get(amenity,"Other")
            name    = tags.get("name") or f"{stype} Station"
            rows.append({"name":name,"lat":float(lat),"lon":float(lon),"type":stype})
        if rows:
            return pd.DataFrame(rows)
    except Exception:
        pass
    return pd.DataFrame()


def _synthetic_stations(minx: float, miny: float, maxx: float, maxy: float, n: int=100) -> pd.DataFrame:
    from shapely.geometry import Point, box as _box
    boundary = _box(minx, miny, maxx, maxy)
    random.seed(42)
    pts: list[tuple[float,float]] = []
    while len(pts) < n:
        px, py = random.uniform(minx,maxx), random.uniform(miny,maxy)
        if boundary.contains(Point(px,py)):
            pts.append((py,px))
    cycle = (["Police","Fire","EMS"] * (n//3+1))[:n]
    return pd.DataFrame({
        "name":[f"Station {i+1}" for i in range(n)],
        "lat":[p[0] for p in pts],"lon":[p[1] for p in pts],"type":cycle
    })


def fetch_stations_with_fallback(df_calls: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Try Overpass, fall back to synthetic. Returns (df, status_message)."""
    lons, lats = df_calls["lon"], df_calls["lat"]
    minx,maxx = float(lons.min()),float(lons.max())
    miny,maxy = float(lats.min()),float(lats.max())

    df_st = _fetch_osm_stations(minx, miny, maxx, maxy)
    if not df_st.empty:
        n = len(df_st)
        if n > 100:
            df_st = df_st.sample(100, random_state=42).reset_index(drop=True)
        msg = (f"✅ Loaded **{min(n,100)}** real police/fire/EMS stations from OpenStreetMap"
               + (f" (sampled from {n})" if n>100 else ""))
        return df_st, msg

    df_st = _synthetic_stations(minx, miny, maxx, maxy)
    msg = ("ℹ️ OpenStreetMap stations unavailable — using 100 synthetic station candidates. "
           "Upload a `stations.csv` for real locations.")
    return df_st, msg


# ═══════════════════════════════════════════════════════════════
# §9  NORMALISE CALLS DATAFRAME  (coordinate extraction pipeline)
# ═══════════════════════════════════════════════════════════════

def normalise_calls(
    df: pd.DataFrame,
    mapping: ClassifyResult,
    geocode_progress_cb=None,
) -> pd.DataFrame:
    """Convert any raw CAD DataFrame → standard calls format (lat, lon, ...)."""
    out = pd.DataFrame()
    rev = {v:k for k,v in mapping.items()}   # label → first col with that label

    # ── PRIORITY ORDER ───────────────────────────────────────────
    # 1. Explicit lat/lon columns                   (always fastest, most accurate)
    # 2. X/Y columns that contain decimal degrees   (e.g. X-Coordinate, Y-Coordinate)
    # 3. Projected X/Y that need reprojection        (UTM, State Plane, Web Mercator)
    # 4. Address strings → Nominatim geocoding       (only when NO numeric coords exist)
    #
    # Crucially: if lat/lon OR numeric coordinate columns are found, the address
    # column is IGNORED entirely — no geocoding is triggered.

    # FORMAT A/B: decimal lat/lon — always preferred over address geocoding
    if "lat" in rev and "lon" in rev:
        lats = pd.to_numeric(df[rev["lat"]], errors="coerce")
        lons = pd.to_numeric(df[rev["lon"]], errors="coerce")
        # Swap if columns appear transposed (lat values > 90 but lon values ≤ 90)
        if lats.dropna().abs().median() > 90 and lons.dropna().abs().median() <= 90:
            lats, lons = lons, lats
        out["lat"] = lats.values
        out["lon"] = lons.values

    # FORMAT F/G: X/Y coordinate columns (projected or already decimal degrees)
    elif "x_proj" in rev and "y_proj" in rev:
        xv = pd.to_numeric(df[rev["x_proj"]], errors="coerce")
        yv = pd.to_numeric(df[rev["y_proj"]], errors="coerce")
        ok = xv.notna() & yv.notna()
        xok, yok = xv[ok].values, yv[ok].values

        # Check if the "projected" columns actually contain decimal degrees already
        # (e.g. "X-Coordinate" = -119.33, "Y-Coordinate" = 36.49 — common in CAD exports)
        x_is_lon = bool(np.percentile(np.abs(xok), 95) <= 180)
        y_is_lat = bool(np.percentile(np.abs(yok), 95) <= 90)

        if x_is_lon and y_is_lat:
            # Already WGS84 decimal degrees — use directly, swap if needed
            if np.median(np.abs(yok)) > np.median(np.abs(xok)):
                # y has larger magnitude → likely lon; swap
                lons_arr, lats_arr = yok, xok
            else:
                lons_arr, lats_arr = xok, yok
            tmp = df[ok].copy()
            tmp["lat"] = lats_arr;  tmp["lon"] = lons_arr
            out = tmp[["lat","lon"]].copy();  df = tmp
        else:
            # Genuine projected coordinates — reproject to WGS84
            epsg = _detect_epsg(xok, yok)
            if not epsg:
                st.warning("⚠️ Projected CRS not identified. Add lat/lon or adjust column mapping.")
                return pd.DataFrame()
            lons_arr, lats_arr = _project_to_wgs84(xok, yok, epsg)
            tmp = df[ok].copy()
            tmp["lat"] = lats_arr;  tmp["lon"] = lons_arr
            out = tmp[["lat","lon"]].copy();  df = tmp

    # FORMATS C/D/E: address strings — ONLY reached when no numeric coords were found
    elif "address" in rev:
        st.info("📍 Address-based file — geocoding via Nominatim (≤1 req/s, max 5,000 rows).")
        geocoded = _batch_geocode(df, mapping, max_rows=5_000, progress_cb=geocode_progress_cb)
        if geocoded.empty:
            st.error("❌ Geocoding returned no results. Check address column content.")
            return pd.DataFrame()
        out = geocoded[["lat","lon"]].copy();  df = geocoded

    else:
        # Last resort: value sniff
        num = df.select_dtypes(include=[np.number]).columns.tolist()
        lcs = [c for c in num if _looks_like_lat(df[c]) and not _looks_like_projected(df[c])]
        lns = [c for c in num if _looks_like_lon(df[c]) and not _looks_like_projected(df[c])]
        best = min(
            ((a,b) for a in lcs for b in lns if a!=b),
            key=lambda ab: abs(df[ab[0]].median()-37)+abs(df[ab[1]].median()+95),
            default=None,
        )
        if best:
            out["lat"] = pd.to_numeric(df[best[0]], errors="coerce").values
            out["lon"] = pd.to_numeric(df[best[1]], errors="coerce").values
        else:
            st.error("❌ Could not identify coordinates. Use the mapping panel to assign columns.")
            return pd.DataFrame()

    # Carry enrichment columns
    for label in ("priority","nature","date"):
        if label in rev and rev[label] in df.columns:
            out[label] = df[rev[label]].values[:len(out)]

    out = out.dropna(subset=["lat","lon"]).reset_index(drop=True)
    mask = (out["lat"].between(-90,90) & out["lon"].between(-180,180)
            & (out["lat"].abs()>0.1) & (out["lon"].abs()>0.1))
    return out[mask].reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════
# §10  CONFIDENCE-GATED MAPPING UI
# ═══════════════════════════════════════════════════════════════

def _render_mapping_ui(
    df: pd.DataFrame,
    mapping: ClassifyResult,
    confidences: ConfidenceMap,
    force_open: bool,
    accent_color: str,
) -> ClassifyResult:
    """
    Column mapping review panel.
    - force_open=True  → expanded, warning shown (low confidence path)
    - force_open=False → collapsed, caption shown (high confidence path)
    """
    title = ("⚠️ Column mapping needs review — please confirm before processing"
             if force_open else "🔍 Auto-detected column mapping (click to adjust if needed)")

    with st.expander(title, expanded=force_open):
        if force_open:
            st.warning(
                "Could not confidently identify all coordinate columns. "
                "Please assign **Latitude** and **Longitude** (or **Address**) "
                "below, then press **▶ Process File**."
            )
        else:
            st.caption("All columns identified with high confidence. Adjust below if anything looks wrong.")

        updated: ClassifyResult = {}
        cols_ui = st.columns(3)

        for i, col in enumerate(df.columns):
            current = mapping.get(col, "ignore")
            conf    = confidences.get(col, 0.0)
            clr     = (_CONF_COLOR["HIGH"]   if conf >= _HIGH_CONF else
                       _CONF_COLOR["MEDIUM"] if conf >= _LOW_CONF  else
                       _CONF_COLOR["LOW"])
            conf_lbl = "HIGH" if conf >= _HIGH_CONF else "MED" if conf >= _LOW_CONF else "LOW"

            cols_ui[i%3].markdown(
                f'<div style="font-size:0.6rem;margin-bottom:1px;">'
                f'<code style="color:#ccc">{col}</code> '
                f'<span style="color:{clr};font-size:0.52rem">●{conf_lbl}</span></div>',
                unsafe_allow_html=True,
            )
            chosen = cols_ui[i%3].selectbox(
                f"col_{col}", options=_LABEL_OPTIONS,
                index=(_LABEL_OPTIONS.index(current) if current in _LABEL_OPTIONS
                       else _LABEL_OPTIONS.index("ignore")),
                key=f"colmap_{col}",
                label_visibility="collapsed",
            )
            if chosen != "ignore":
                updated[col] = chosen

    return updated


# ═══════════════════════════════════════════════════════════════
# §11  MAIN STREAMLIT COMPONENT
# ═══════════════════════════════════════════════════════════════

def render_smart_uploader(
    accent_color: str = "#00D2FF",
    text_muted:   str = "#aaaaaa",
    card_bg:      str = "#111111",
    card_border:  str = "#333333",
) -> None:
    """
    Drop-in replacement for the `with path_upload_col:` block in app.py.

    Session state written:
        df_calls, df_stations, csvs_ready, total_original_calls,
        active_city, active_state
    """

    # ── CARD HEADER ──────────────────────────────────────────
    st.markdown(f"""
    <div style="background:#080808;border:1px solid #1c1c1c;border-radius:10px;
         padding:22px 18px 16px;position:relative;overflow:hidden;">
        <div style="position:absolute;top:0;left:0;right:0;height:3px;
             background:{accent_color};border-radius:10px 10px 0 0;"></div>
        <span style="font-size:1.5rem;display:block;margin-bottom:9px;">📂</span>
        <div style="font-size:0.55rem;font-weight:800;letter-spacing:2.5px;
             text-transform:uppercase;color:{accent_color};margin-bottom:5px;">Path 02</div>
        <div style="font-size:1rem;font-weight:800;color:#fff;
             line-height:1.25;margin-bottom:7px;">Upload Real CAD Data</div>
        <div style="font-size:0.7rem;color:#555;line-height:1.6;">
            Any format — lat/lon, address strings, intersections, block-level,
            state-plane. Station file optional: real police &amp; fire stations
            auto-fetched from OpenStreetMap.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ── FILE UPLOADER ────────────────────────────────────────
    uploaded = st.file_uploader(
        "Drop CAD export(s) here",
        accept_multiple_files=True,
        type=["csv","txt","tsv","xlsx"],
        label_visibility="collapsed",
        help=(
            "Any filename works. Optionally also drop a stations/facilities file.\n"
            "Formats: lat/lon · full address · intersection · block-level · "
            "state-plane (X/Y) · UTM · Web Mercator · CSV / TSV / XLSX"
        ),
    )

    if not uploaded:
        st.markdown(f"""
        <div style="font-size:0.63rem;color:#3a3a3a;line-height:1.85;
             margin-top:10px;border-top:1px solid #141414;padding-top:10px;">
            <b style='color:#555;'>Any column names</b>
            — lat, latitude, y_coord, GeoY, Easting, X_SP…<br>
            <b style='color:#555;'>Any address format</b>
            — full address · intersections ("Main &amp; Oak") · block-level<br>
            <b style='color:#555;'>No stations file?</b>
            — real OSM police/fire/EMS auto-loaded<br>
            <b style='color:#555;'>Accepts</b>
            — CSV, TSV, TXT, XLSX · comma / tab / pipe / semicolon delimited
        </div>
        """, unsafe_allow_html=True)
        return

    # ── FILE ROUTING ─────────────────────────────────────────
    STATION_RE = re.compile(r"station|facility|facilit|precinct|dept|department|firehouse", re.I)
    CALL_RE    = re.compile(r"call|incident|cad|dispatch|event|run|response|crime|offense", re.I)

    call_file = station_file = None
    ambiguous: list = []
    for f in uploaded:
        nm = f.name.lower()
        if STATION_RE.search(nm): station_file = station_file or f
        elif CALL_RE.search(nm) or nm in ("calls.csv","incidents.csv"): call_file = call_file or f
        else: ambiguous.append(f)
    for af in ambiguous:
        if call_file is None:      call_file    = af
        elif station_file is None: station_file = af

    if call_file is None:
        st.warning("⚠️ Could not identify calls file. Include 'calls', 'incidents', or 'cad' in the filename.")
        return

    # ── READ FILE ────────────────────────────────────────────
    def _read(f) -> pd.DataFrame:
        raw = f.read(); f.seek(0)
        if f.name.lower().endswith(".xlsx"):
            return pd.read_excel(io.BytesIO(raw))
        snippet = raw[:8192].decode("utf-8", errors="replace")
        delim   = max((",","\t","|",";"), key=snippet.count)
        return pd.read_csv(io.BytesIO(raw), sep=delim, low_memory=False, on_bad_lines="skip")

    try:
        raw_calls = _read(call_file)
    except Exception as exc:
        st.error(f"❌ Could not read **{call_file.name}**: {exc}")
        return

    raw_calls.columns = [str(c).strip().strip("'\"") for c in raw_calls.columns]
    st.success(f"✅ **{call_file.name}** — {len(raw_calls):,} rows × {len(raw_calls.columns)} columns")

    # ── CLASSIFY ─────────────────────────────────────────────
    with st.spinner("🧠 Identifying columns…"):
        mapping, confidences = classify_columns(raw_calls)

    high_conf = _is_high_confidence(mapping, confidences)

    # ── BADGE ROW ────────────────────────────────────────────
    if set(mapping.values()) & _COORD_LABELS:
        badges = ""
        for col, lbl in mapping.items():
            icon = _LABEL_ICONS.get(lbl, lbl)
            conf = confidences.get(col, 0.0)
            clr  = (accent_color        if conf >= _HIGH_CONF else
                    _CONF_COLOR["MEDIUM"] if conf >= _LOW_CONF  else
                    _CONF_COLOR["LOW"])
            badges += (
                f'<span style="background:#0d1f25;border:1px solid {clr};'
                f'border-radius:4px;padding:2px 8px;font-size:0.58rem;'
                f'color:{clr};margin:2px;display:inline-block;">'
                f'<b>{icon}</b> → <code style="color:#ddd">{col}</code></span>'
            )
        st.markdown(f"<div style='margin:6px 0;'>{badges}</div>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ Could not identify coordinate columns. Assign them in the panel below.")

    # ── MAPPING UI (conditional) ─────────────────────────────
    mapping = _render_mapping_ui(
        raw_calls, mapping, confidences,
        force_open=not high_conf,
        accent_color=accent_color,
    )

    # ── GEOCODE PROGRESS ─────────────────────────────────────
    geo_slot = st.empty()
    def _geo_progress(frac: float) -> None:
        geo_slot.progress(frac, text=f"📍 Geocoding… {frac*100:.0f}%")

    # ── PROCESS BUTTON ───────────────────────────────────────
    btn_label = ("▶ Process File" if high_conf
                 else "▶ Process File  (confirm mapping above first)")
    if st.button(btn_label, use_container_width=True, key="smart_process_btn"):
        geo_slot.empty()
        with st.spinner("⚙️ Extracting coordinates…"):
            df_calls = normalise_calls(raw_calls, mapping, geocode_progress_cb=_geo_progress)
        geo_slot.empty()

        if df_calls.empty:
            st.error("❌ No valid coordinates extracted. Adjust column mapping above.")
            return

        original_n = len(df_calls)
        if original_n > 25_000:
            df_calls = df_calls.sample(25_000, random_state=42).reset_index(drop=True)
            st.toast(f"⚠️ Sampled to 25,000 calls (original: {original_n:,})")

        st.session_state["df_calls"]             = df_calls
        st.session_state["total_original_calls"] = original_n

        # ── STATIONS ─────────────────────────────────────────
        if station_file is not None:
            try:
                raw_st = _read(station_file)
                raw_st.columns = [str(c).strip() for c in raw_st.columns]
                st_map, _ = classify_columns(raw_st)
                df_st     = normalise_calls(raw_st, st_map)
                df_st     = df_st.rename(columns={"nature":"type"})
                nc = next((c for c in raw_st.columns if "name" in c.lower()), None)
                df_st["name"] = (raw_st[nc].astype(str).values[:len(df_st)]
                                 if nc else [f"Station {i+1}" for i in range(len(df_st))])
                if len(df_st) > 100:
                    df_st = df_st.sample(100, random_state=42).reset_index(drop=True)
                st.session_state["df_stations"] = df_st
                st.success(f"✅ Stations loaded from **{station_file.name}**: {len(df_st)} stations")
            except Exception as exc:
                st.warning(f"⚠️ Could not parse stations file ({exc}). Auto-fetching…")
                station_file = None

        if station_file is None:
            with st.spinner("🗺️ Fetching police & fire stations from OpenStreetMap…"):
                df_st, msg = fetch_stations_with_fallback(df_calls)
            st.session_state["df_stations"] = df_st
            (st.success if msg.startswith("✅") else st.info)(msg)

        # ── AUTO-DETECT CITY/STATE ────────────────────────────
        try:
            from app import reverse_geocode_state, US_STATES_ABBR  # type: ignore
            mid_lat = float(df_calls["lat"].median())
            mid_lon = float(df_calls["lon"].median())
            det_state, det_city = reverse_geocode_state(mid_lat, mid_lon)
            if det_state and det_state in US_STATES_ABBR:
                st.session_state["active_state"] = US_STATES_ABBR[det_state]
                if det_city:
                    st.session_state["active_city"] = det_city
                st.toast(f"📍 Detected: {st.session_state['active_city']}, {st.session_state['active_state']}")
        except Exception:
            pass

        # ── PREVIEW ──────────────────────────────────────────
        show = ["lat","lon"] + [c for c in ("priority","nature","date") if c in df_calls.columns]
        st.markdown(f"**Preview — {len(df_calls):,} calls loaded:**")
        st.dataframe(df_calls[show].head(6), use_container_width=True)

        st.session_state["csvs_ready"] = True
        st.rerun()
