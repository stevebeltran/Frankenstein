# Canada Mapping Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend jurisdiction boundary + population lookup (currently US-only) to also resolve Canadian province / census-division / census-subdivision jurisdictions, with country routing detected automatically — no UI toggle.

**Architecture:** A new `modules/boundaries_ca.py` module holds all StatCan-backed logic (postal lookup, boundary lookup, bundled population). The two existing call sites — `modules/boundaries.py` (the "library" copy, consumed by `modules/stations.py`, `modules/onboarding.py`, `modules/geospatial_utils.py`) and `app.py` (a near-identical inline duplicate that is the live path for the main manual-entry UI) — each get a thin dispatch branch added to their existing functions: if the region abbreviation is a Canadian province, call into `boundaries_ca`; otherwise fall through to the unchanged US logic. Canadian boundary geometry is bundled (not live-fetched) because Streamlit Cloud's filesystem is ephemeral.

**Tech Stack:** Python, GeoPandas/Shapely, Streamlit `@st.cache_data`, `urllib.request` (no new dependencies).

**Spec:** `docs/superpowers/specs/2026-09-12-canada-mapping-expansion-design.md`

## Global Constraints

- No new UI toggle — country routing is automatic (postal-code pattern, or province abbreviation already present in `state_abbr`/`active_state`).
- Canadian boundary geometry (province, CD, CSD) is bundled as committed parquet, not live-fetched — mirrors why the US path bundles `counties_lite.parquet`/`places_lite.parquet`.
- Population is bundled as a `POPULATION` column in the same lite parquet files (StatCan has no simple by-name REST lookup like the US Census API; discovered during planning — see spec update below).
- Out of scope: regulatory airspace overlay (FAA UASFM/LAANC/NAV Canada), geocoding rework, any UI country selector.
- Don't touch `app.py`'s `lookup_zip_code` — confirmed dead code (zero callers anywhere in the repo); wiring it would be unrequested scope creep on unused code.
- Don't deduplicate `app.py`'s and `modules/boundaries.py`'s parallel US implementations — that refactor is not required by this task and the repo rules forbid refactoring shared code unless the task requires it.

**Spec correction (found during planning):** the spec's population row ("StatCan Census Profile via WDS API — Live") is superseded. StatCan's Web Data Service has no simple "population by name" REST endpoint analogous to the US Census Bureau API; the practical option is to join population once at lite-parquet build time and bundle it as a `POPULATION` column, alongside the boundary geometry it's already bundling. This is a strict simplification (one less live integration, one less runtime failure mode) and doesn't change scope or the country-routing design.

---

### Task 1: Add Canadian province lookup tables to `modules/config.py`

**Files:**
- Modify: `modules/config.py` (insert after the `US_STATES_ABBR` block, i.e. after line 118, before `KNOWN_POPULATIONS`)
- Test: `tests/test_config_ca_provinces.py`

**Interfaces:**
- Produces: `PROVINCE_FIPS: dict[str, str]` (province/territory abbreviation → StatCan PRUID code), `CA_PROVINCES_ABBR: dict[str, str]` (full name → abbreviation). Both consumed by `modules/boundaries_ca.py` in Task 2.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config_ca_provinces.py
from modules.config import PROVINCE_FIPS, CA_PROVINCES_ABBR, STATE_FIPS


def test_province_fips_covers_all_thirteen_provinces_and_territories():
    assert len(PROVINCE_FIPS) == 13
    assert PROVINCE_FIPS["ON"] == "35"
    assert PROVINCE_FIPS["BC"] == "59"


def test_province_abbreviations_do_not_collide_with_us_state_abbreviations():
    assert not (set(PROVINCE_FIPS) & set(STATE_FIPS))


def test_ca_provinces_abbr_maps_full_name_to_code_present_in_province_fips():
    for full_name, abbr in CA_PROVINCES_ABBR.items():
        assert abbr in PROVINCE_FIPS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config_ca_provinces.py -v`
Expected: FAIL with `ImportError: cannot import name 'PROVINCE_FIPS'`

- [ ] **Step 3: Add the dicts to `modules/config.py`**

Insert immediately after the closing `}` of `US_STATES_ABBR` (currently line 118):

```python
# StatCan PRUID codes — Canadian province/territory equivalent of STATE_FIPS.
PROVINCE_FIPS = {
    "AB": "48", "BC": "59", "MB": "46", "NB": "13", "NL": "10", "NS": "12",
    "NT": "61", "NU": "62", "ON": "35", "PE": "11", "QC": "24", "SK": "47", "YT": "60",
}

CA_PROVINCES_ABBR = {
    "Alberta": "AB", "British Columbia": "BC", "Manitoba": "MB", "New Brunswick": "NB",
    "Newfoundland and Labrador": "NL", "Nova Scotia": "NS", "Northwest Territories": "NT",
    "Nunavut": "NU", "Ontario": "ON", "Prince Edward Island": "PE", "Quebec": "QC",
    "Saskatchewan": "SK", "Yukon": "YT",
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config_ca_provinces.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add modules/config.py tests/test_config_ca_provinces.py
git commit -m "feat(ca): add PROVINCE_FIPS and CA_PROVINCES_ABBR lookup tables"
```

---

### Task 2: `modules/boundaries_ca.py` — country detection + postal lookup

**Files:**
- Create: `modules/boundaries_ca.py`
- Test: `tests/test_boundaries_ca.py`

**Interfaces:**
- Consumes: `PROVINCE_FIPS` from Task 1 (`modules.config`).
- Produces: `is_ca_region(abbr) -> bool`, `detect_country_from_postal(code) -> 'US'|'CA'|None`, `lookup_postal_code_ca(postal_code) -> (city, province_abbr, province_name)`. All consumed by Task 5/6's dispatch edits.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_boundaries_ca.py
import json
import urllib.request

from modules.boundaries_ca import (
    is_ca_region,
    detect_country_from_postal,
    lookup_postal_code_ca,
)


def test_is_ca_region_true_for_province_false_for_state():
    assert is_ca_region("on") is True
    assert is_ca_region("NY") is False
    assert is_ca_region("") is False


def test_detect_country_from_postal_classifies_us_zip_and_ca_postal():
    assert detect_country_from_postal("60614") == "US"
    assert detect_country_from_postal("60614-1234") == "US"
    assert detect_country_from_postal("M5V 2T6") == "CA"
    assert detect_country_from_postal("M5V") == "CA"
    assert detect_country_from_postal("not-a-code") is None


def test_lookup_postal_code_ca_parses_zippopotam_response(monkeypatch):
    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return json.dumps({
                "places": [{
                    "place name": "Toronto",
                    "state abbreviation": "ON",
                    "state": "Ontario",
                }]
            }).encode("utf-8")

    def _fake_urlopen(req, timeout=5):
        assert "api.zippopotam.us/ca/M5V" in req.full_url
        return _FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
    assert lookup_postal_code_ca("M5V 2T6") == ("Toronto", "ON", "Ontario")


def test_lookup_postal_code_ca_rejects_us_zip():
    assert lookup_postal_code_ca("60614") == (None, None, None)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_boundaries_ca.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'modules.boundaries_ca'`

- [ ] **Step 3: Create `modules/boundaries_ca.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_boundaries_ca.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add modules/boundaries_ca.py tests/test_boundaries_ca.py
git commit -m "feat(ca): add country detection and CA postal code lookup"
```

---

### Task 3: Build bundled Canada boundary + population lite parquet files

**Files:**
- Create: `download_ca_boundary_layers.py`
- Create (generated, committed): `provinces_lite.parquet`, `cd_lite.parquet`, `csd_lite.parquet`

**Interfaces:**
- Produces: three parquet files on disk at repo root with columns `PRUID, NAME, POPULATION, geometry` (`csd_lite.parquet` additionally has `NAMELSAD`). Consumed by Task 4.

This is a one-off data-prep script (like the existing `download_regulatory_layers.py`), not called at app runtime.

- [ ] **Step 1: Write the script**

```python
#!/usr/bin/env python3
"""
Download and Build Canada Boundary Lite Parquet Files
======================================================

One-off data-prep script: downloads StatCan cartographic boundary files
(provinces/territories, census divisions, census subdivisions) and StatCan
population/dwelling counts, simplifies geometry, and writes the bundled
"lite" parquet files the app reads at runtime — mirrors how
counties_lite.parquet / places_lite.parquet were built for the US path.

Run this once when Canada boundary data needs to be (re)built. NOT called
at app runtime.

Usage:
  python download_ca_boundary_layers.py

Output (repo root):
  provinces_lite.parquet   (PRUID, NAME, POPULATION, geometry)
  cd_lite.parquet          (PRUID, NAME, POPULATION, geometry)
  csd_lite.parquet         (PRUID, NAME, NAMELSAD, POPULATION, geometry)

Before running: confirm the boundary-file URLs below still match StatCan's
current index (https://www12.statcan.gc.ca/census-recensement/2021/geo/
sip-pis/boundary-limites/index-eng.cfm) — StatCan occasionally moves files
when a new boundary vintage is published, the same reason
modules/boundaries.py tries multiple TIGER years for the US path. If a
column referenced below (e.g. CDNAME) is missing after download, print
`gdf.columns.tolist()` and add the real name to the candidate list in
`_first_present`.
"""
import io
import os
import zipfile
import glob
import urllib.request

import geopandas as gpd
import pandas as pd

STATCAN_BASE = "https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/files-fichiers"
BOUNDARY_FILES = {
    "province": f"{STATCAN_BASE}/lpr_000b21a_e.zip",
    "cd": f"{STATCAN_BASE}/lcd_000b21a_e.zip",
    "csd": f"{STATCAN_BASE}/lcsd000b21a_e.zip",
}

# StatCan "Population and dwelling counts" (2021 Census), full table CSV download.
POPULATION_CSV_URL = "https://www150.statcan.gc.ca/n1/tbl/csv/98100001-eng.zip"

SIMPLIFY_TOLERANCE_DEGREES = 0.001  # ~100m — matches the visual detail of the existing US lite files
TEMP_DIR = "temp_ca_boundary_download"


def _safe_extractall(zip_file, dest_dir):
    root = os.path.abspath(dest_dir)
    for member in zip_file.namelist():
        target = os.path.abspath(os.path.join(root, member))
        if target != root and not target.startswith(root + os.sep):
            raise ValueError(f"Unsafe path in archive: {member}")
    zip_file.extractall(dest_dir)


def _download_and_extract(url, dest_dir):
    req = urllib.request.Request(url, headers={"User-Agent": "BRINC_COS_Optimizer/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        zip_data = resp.read()
    zf = zipfile.ZipFile(io.BytesIO(zip_data))
    os.makedirs(dest_dir, exist_ok=True)
    _safe_extractall(zf, dest_dir)
    shp_files = glob.glob(os.path.join(dest_dir, "*.shp"))
    if not shp_files:
        raise RuntimeError(f"No .shp found after extracting {url}")
    return gpd.read_file(shp_files[0])


def _first_present(columns, candidates):
    for c in candidates:
        if c in columns:
            return c
    raise KeyError(f"None of {candidates} found in columns {list(columns)}")


def _load_population_lookup():
    req = urllib.request.Request(POPULATION_CSV_URL, headers={"User-Agent": "BRINC_COS_Optimizer/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        zip_data = resp.read()
    zf = zipfile.ZipFile(io.BytesIO(zip_data))
    os.makedirs(TEMP_DIR, exist_ok=True)
    csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    zf.extractall(TEMP_DIR, members=csv_names)
    df = pd.read_csv(os.path.join(TEMP_DIR, csv_names[0]), low_memory=False)
    geo_col = _first_present(df.columns, ["GEO_NAME", "Geography", "GEO"])
    val_col = _first_present(df.columns, ["VALUE", "Value"])
    pop = df[df[val_col].notna()].groupby(geo_col)[val_col].first()
    return pop.to_dict()


def _attach_population(gdf, name_col, population_lookup):
    gdf = gdf.copy()
    gdf["POPULATION"] = gdf[name_col].map(population_lookup).fillna(0).astype(int)
    return gdf


def build_provinces_lite(population_lookup):
    gdf = _download_and_extract(BOUNDARY_FILES["province"], os.path.join(TEMP_DIR, "province"))
    pruid_col = _first_present(gdf.columns, ["PRUID"])
    name_col = _first_present(gdf.columns, ["PRENAME", "PRNAME", "PRFNAME"])
    gdf = gdf.rename(columns={pruid_col: "PRUID", name_col: "NAME"})
    gdf["geometry"] = gdf["geometry"].simplify(SIMPLIFY_TOLERANCE_DEGREES, preserve_topology=True)
    gdf = _attach_population(gdf, "NAME", population_lookup)
    out = gdf[["PRUID", "NAME", "POPULATION", "geometry"]]
    out.to_parquet("provinces_lite.parquet")
    return out


def build_cd_lite(population_lookup):
    gdf = _download_and_extract(BOUNDARY_FILES["cd"], os.path.join(TEMP_DIR, "cd"))
    pruid_col = _first_present(gdf.columns, ["PRUID"])
    name_col = _first_present(gdf.columns, ["CDNAME"])
    gdf = gdf.rename(columns={pruid_col: "PRUID", name_col: "NAME"})
    gdf["geometry"] = gdf["geometry"].simplify(SIMPLIFY_TOLERANCE_DEGREES, preserve_topology=True)
    gdf = _attach_population(gdf, "NAME", population_lookup)
    out = gdf[["PRUID", "NAME", "POPULATION", "geometry"]]
    out.to_parquet("cd_lite.parquet")
    return out


def build_csd_lite(population_lookup):
    gdf = _download_and_extract(BOUNDARY_FILES["csd"], os.path.join(TEMP_DIR, "csd"))
    pruid_col = _first_present(gdf.columns, ["PRUID"])
    name_col = _first_present(gdf.columns, ["CSDNAME"])
    type_col = _first_present(gdf.columns, ["CSDTYPE"])
    gdf = gdf.rename(columns={pruid_col: "PRUID", name_col: "NAME"})
    gdf["NAMELSAD"] = gdf["NAME"] + " (" + gdf[type_col].astype(str) + ")"
    gdf["geometry"] = gdf["geometry"].simplify(SIMPLIFY_TOLERANCE_DEGREES, preserve_topology=True)
    gdf = _attach_population(gdf, "NAME", population_lookup)
    out = gdf[["PRUID", "NAME", "NAMELSAD", "POPULATION", "geometry"]]
    out.to_parquet("csd_lite.parquet")
    return out


if __name__ == "__main__":
    print("[CA boundary prep] downloading population lookup...")
    population_lookup = _load_population_lookup()
    print("[CA boundary prep] building provinces_lite.parquet...")
    build_provinces_lite(population_lookup)
    print("[CA boundary prep] building cd_lite.parquet...")
    build_cd_lite(population_lookup)
    print("[CA boundary prep] building csd_lite.parquet...")
    build_csd_lite(population_lookup)
    print("[CA boundary prep] done.")
```

- [ ] **Step 2: Run the script**

Run: `python download_ca_boundary_layers.py`
Expected: prints four `[CA boundary prep] ...` progress lines ending in `done.`, and creates `provinces_lite.parquet`, `cd_lite.parquet`, `csd_lite.parquet` in the repo root.

If a `KeyError: None of [...] found in columns [...]` is raised, print the actual column list it reports and add the real StatCan column name to the relevant `_first_present` candidate list, then re-run.

- [ ] **Step 3: Verify schema and row counts**

Run:
```bash
python -c "
import geopandas as gpd
checks = [
    ('provinces_lite.parquet', {'PRUID','NAME','POPULATION','geometry'}, 10, 14),
    ('cd_lite.parquet', {'PRUID','NAME','POPULATION','geometry'}, 280, 320),
    ('csd_lite.parquet', {'PRUID','NAME','NAMELSAD','POPULATION','geometry'}, 4000, 6000),
]
for fname, cols, lo, hi in checks:
    gdf = gpd.read_parquet(fname)
    assert cols <= set(gdf.columns), f'{fname} missing columns: {cols - set(gdf.columns)}'
    assert lo <= len(gdf) <= hi, f'{fname} has {len(gdf)} rows, expected {lo}-{hi}'
    assert (gdf[\"POPULATION\"] > 0).mean() > 0.9, f'{fname} population mostly zero — check name-matching in _attach_population'
    print(fname, len(gdf), 'rows OK')
"
```
Expected: three `OK` lines, no assertion errors.

- [ ] **Step 4: Check bundled file sizes stay reasonable**

Run: `ls -la provinces_lite.parquet cd_lite.parquet csd_lite.parquet`
Expected: combined well under 20MB (matching the ~11.8MB precedent set by the US `*_lite.parquet` files). If any file is much larger, increase `SIMPLIFY_TOLERANCE_DEGREES` (e.g. to `0.002`) and re-run Steps 2-3.

- [ ] **Step 5: Commit**

```bash
git add download_ca_boundary_layers.py provinces_lite.parquet cd_lite.parquet csd_lite.parquet
git commit -m "feat(ca): bundle StatCan province/CD/CSD boundary + population lite parquet"
```

---

### Task 4: `modules/boundaries_ca.py` — CD/CSD boundary lookup + bundled population

**Files:**
- Modify: `modules/boundaries_ca.py`
- Modify: `tests/test_boundaries_ca.py`

**Interfaces:**
- Consumes: `provinces_lite.parquet`, `cd_lite.parquet`, `csd_lite.parquet` from Task 3; `_normalize_ca_name` from Task 2.
- Produces: `fetch_cd_boundary_local(province_abbr, cd_name) -> (bool, GeoDataFrame|None)`, `fetch_csd_boundary_local(province_abbr, csd_name) -> (bool, GeoDataFrame|None)`, `fetch_cd_by_centroid(df_calls, province_abbr) -> (bool, GeoDataFrame|None)`, `fetch_ca_population(province_abbr, name, boundary_kind='place') -> int|None`. All consumed by Task 5/6's dispatch edits.

No live StatCan fallback is needed here (unlike the US TIGER fallback) — the bundled CD/CSD set from Task 3 is the *complete* StatCan set, not a partial subset, so there's nothing left to fetch on a miss.

- [ ] **Step 1: Write the failing tests**

These run against the real bundled parquet committed in Task 3 (same style as the existing `tests/test_boundary_suggestions.py`, which runs against the real committed US `*_lite.parquet`). The exact literal names below are best-guess for real StatCan CSD/CD naming — if a lookup returns `False`/`None` on first run, open the relevant parquet (`gpd.read_parquet("csd_lite.parquet")[['NAME','PRUID']].query("PRUID == '35'")`) to find the exact StatCan spelling and correct the literal in the test. This is expected first-run calibration against a real external dataset, not a design gap.

```python
# append to tests/test_boundaries_ca.py
from modules.boundaries_ca import (
    fetch_cd_boundary_local,
    fetch_csd_boundary_local,
    fetch_cd_by_centroid,
    fetch_ca_population,
)
import pandas as pd


def test_fetch_csd_boundary_local_finds_toronto_in_ontario():
    success, gdf = fetch_csd_boundary_local("ON", "Toronto")
    assert success is True
    assert gdf is not None and not gdf.empty


def test_fetch_cd_boundary_local_returns_false_for_unknown_name():
    success, gdf = fetch_cd_boundary_local("ON", "Not A Real Census Division")
    assert success is False
    assert gdf is None


def test_fetch_cd_boundary_local_returns_false_for_us_state_abbr():
    success, gdf = fetch_cd_boundary_local("NY", "Erie")
    assert success is False
    assert gdf is None


def test_fetch_cd_by_centroid_finds_containing_division():
    # Median of these points sits inside downtown Toronto, Ontario.
    df_calls = pd.DataFrame({"lat": [43.65, 43.66], "lon": [-79.38, -79.39]})
    success, gdf = fetch_cd_by_centroid(df_calls, "ON")
    assert success is True
    assert gdf is not None and not gdf.empty


def test_fetch_ca_population_reads_bundled_column():
    population = fetch_ca_population("ON", "Toronto", boundary_kind="place")
    assert population is not None and population > 0


def test_fetch_ca_population_returns_none_for_us_state_abbr():
    assert fetch_ca_population("NY", "Buffalo", boundary_kind="place") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_boundaries_ca.py -v`
Expected: FAIL with `ImportError: cannot import name 'fetch_cd_boundary_local'`

- [ ] **Step 3: Add the functions to `modules/boundaries_ca.py`**

Append:

```python
from shapely.geometry import Point


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_boundaries_ca.py -v`
Expected: PASS (all tests). Adjust literal place/CD names per Step 1's note if any fail on exact StatCan spelling.

- [ ] **Step 5: Commit**

```bash
git add modules/boundaries_ca.py tests/test_boundaries_ca.py
git commit -m "feat(ca): add CD/CSD boundary lookup and bundled population reads"
```

---

### Task 5: Wire CA dispatch into `modules/boundaries.py`

**Files:**
- Modify: `modules/boundaries.py` (add import; edit `lookup_zip_code`, `fetch_county_boundary_local`, `fetch_place_boundary_local`, `fetch_county_by_centroid`, `_lookup_population_for_boundary`)
- Test: `tests/test_boundaries_dispatch_ca.py`

**Interfaces:**
- Consumes: everything from `modules.boundaries_ca` (Tasks 2 & 4).
- Produces: no new public names — existing functions now also handle Canadian region abbreviations.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_boundaries_dispatch_ca.py
import modules.boundaries as boundaries


def test_fetch_county_boundary_local_routes_to_ca_for_province_abbr(monkeypatch):
    calls = {}

    def _fake_fetch_cd(province_abbr, name):
        calls['args'] = (province_abbr, name)
        return True, "fake-cd-gdf"

    monkeypatch.setattr(boundaries, "fetch_cd_boundary_local", _fake_fetch_cd)
    assert boundaries.fetch_county_boundary_local("ON", "Waterloo") == (True, "fake-cd-gdf")
    assert calls['args'] == ("ON", "Waterloo")


def test_fetch_place_boundary_local_routes_to_ca_for_province_abbr(monkeypatch):
    monkeypatch.setattr(boundaries, "fetch_csd_boundary_local", lambda p, n: (True, "fake-csd-gdf"))
    assert boundaries.fetch_place_boundary_local("AB", "Calgary") == (True, "fake-csd-gdf")


def test_fetch_county_by_centroid_routes_to_ca_for_province_abbr(monkeypatch):
    monkeypatch.setattr(boundaries, "fetch_cd_by_centroid", lambda df, p: (True, "fake-cd-centroid-gdf"))
    assert boundaries.fetch_county_by_centroid(None, "BC") == (True, "fake-cd-centroid-gdf")


def test_lookup_zip_code_routes_to_ca_postal_lookup(monkeypatch):
    monkeypatch.setattr(boundaries, "lookup_postal_code_ca", lambda code: ("Toronto", "ON", "Ontario"))
    assert boundaries.lookup_zip_code("M5V 2T6") == ("Toronto", "ON", "Ontario")


def test_lookup_population_for_boundary_routes_to_ca(monkeypatch):
    monkeypatch.setattr(boundaries, "fetch_ca_population", lambda p, n, boundary_kind='place': 12345)
    assert boundaries._lookup_population_for_boundary("QC", "Montreal", boundary_kind='place') == 12345


def test_us_paths_are_unaffected_for_us_state_abbr(monkeypatch):
    # Sanity check: a US state abbreviation must never reach the CA functions.
    def _fail(*a, **k):
        raise AssertionError("US state routed to a CA function")

    monkeypatch.setattr(boundaries, "fetch_cd_boundary_local", _fail)
    monkeypatch.setattr(boundaries, "fetch_csd_boundary_local", _fail)
    monkeypatch.setattr(boundaries, "fetch_cd_by_centroid", _fail)
    monkeypatch.setattr(boundaries, "fetch_ca_population", _fail)
    # These will still return False/None (no real data loaded for a fake county),
    # the point is only that they don't raise via the CA branch.
    boundaries.fetch_county_boundary_local("NY", "Erie")
    boundaries.fetch_place_boundary_local("NY", "Buffalo")
    boundaries.fetch_county_by_centroid(None, "NY")
    boundaries._lookup_population_for_boundary("NY", "Buffalo", boundary_kind='place')
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_boundaries_dispatch_ca.py -v`
Expected: FAIL — `AttributeError: module 'modules.boundaries' has no attribute 'fetch_cd_boundary_local'` (nothing to monkeypatch yet since it isn't imported).

- [ ] **Step 3: Add the import and dispatch branches**

In `modules/boundaries.py`, change the import block (currently line 15-16):

```python
from modules.config import STATE_FIPS, KNOWN_POPULATIONS
from modules.geocoding import forward_geocode
from modules.boundaries_ca import (
    is_ca_region,
    detect_country_from_postal,
    lookup_postal_code_ca,
    fetch_cd_boundary_local,
    fetch_csd_boundary_local,
    fetch_cd_by_centroid,
    fetch_ca_population,
)
```

Edit `lookup_zip_code` (currently line 34) — replace the ZIP-format check with country detection:

```python
def lookup_zip_code(zip_code: str):
    """
    Look up a ZIP/postal code and return (city, state_or_province_abbr,
    county_or_cd). Routes to the US or Canadian Zippopotam.us endpoint
    based on the code's format. Returns (None, None, None) on failure or
    an unrecognized format.
    """
    zip_code = zip_code.strip()
    country = detect_country_from_postal(zip_code)
    if country == 'CA':
        return lookup_postal_code_ca(zip_code)
    if country != 'US':
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
```

Edit `fetch_county_boundary_local` (currently line 266) — add as the first line inside the function body, after the `@st.cache_data` decorator stays put:

```python
@st.cache_data
def fetch_county_boundary_local(state_abbr, county_name_input):
    if is_ca_region(state_abbr):
        return fetch_cd_boundary_local(state_abbr, county_name_input)
    # 1. Clean the input
    search_name = normalize_jurisdiction_name(county_name_input)
    ...  # rest unchanged
```

Edit `fetch_place_boundary_local` (currently line 328):

```python
@st.cache_data
def fetch_place_boundary_local(state_abbr, place_name_input):
    """Look up a city/town/CDP boundary from local parquet caches.
    Connecticut and Rhode Island towns fall back to county-subdivision data when needed."""
    if is_ca_region(state_abbr):
        return fetch_csd_boundary_local(state_abbr, place_name_input)
    local_files = ["places_lite.parquet"]
    ...  # rest unchanged
```

Edit `fetch_county_by_centroid` (currently line 219):

```python
def fetch_county_by_centroid(df_calls, state_abbr):
    """Find the county boundary that contains the median centroid of the call data.
    ...
    """
    if is_ca_region(state_abbr):
        return fetch_cd_by_centroid(df_calls, state_abbr)
    local_file = "counties_lite.parquet"
    ...  # rest unchanged
```

Edit `_lookup_population_for_boundary` (currently line 439):

```python
def _lookup_population_for_boundary(state_abbr, city_name, boundary_kind='place'):
    if is_ca_region(state_abbr):
        return fetch_ca_population(state_abbr, city_name or state_abbr, boundary_kind=boundary_kind)
    state_fips = STATE_FIPS.get(str(state_abbr or '').strip().upper(), '')
    ...  # rest unchanged
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_boundaries_dispatch_ca.py tests/test_boundary_suggestions.py -v`
Expected: PASS for all — the dispatch tests pass, and the pre-existing US suggestion tests still pass unchanged (confirms the US branch wasn't disturbed).

- [ ] **Step 5: Commit**

```bash
git add modules/boundaries.py tests/test_boundaries_dispatch_ca.py
git commit -m "feat(ca): route boundary/population/postal lookups to Canada by province abbr"
```

---

### Task 6: Mirror the dispatch into `app.py`'s inline duplicate functions

**Files:**
- Modify: `app.py` (add import near the `modules.config` import block; edit its own inline `fetch_county_boundary_local`, `fetch_place_boundary_local`, `fetch_county_by_centroid`, `_lookup_population_for_boundary`)

**Interfaces:**
- Consumes: `modules.boundaries_ca` (Tasks 2 & 4) directly — `app.py` does not import `modules.boundaries` (confirmed: it has its own parallel inline copies; this is pre-existing duplication in the repo, not introduced by this change).
- No test file: no test in the repo imports `app.py` directly today (Streamlit module-level side effects make that unreliable outside a running app), so this task is not TDD — verify by syntax-compiling the file and a manual Streamlit smoke run.

- [ ] **Step 1: Add the import**

In `app.py`, after the `modules.config` import block (currently ends at line 109), add:

```python
from modules.boundaries_ca import (
    is_ca_region,
    fetch_cd_boundary_local,
    fetch_csd_boundary_local,
    fetch_cd_by_centroid,
    fetch_ca_population,
)
```

- [ ] **Step 2: Edit `app.py`'s `fetch_county_boundary_local` (currently line 2281)**

```python
@st.cache_data
def fetch_county_boundary_local(state_abbr, county_name_input):
    if is_ca_region(state_abbr):
        return fetch_cd_boundary_local(state_abbr, county_name_input)
    # 1. Clean the input
    search_name = normalize_jurisdiction_name(county_name_input)
    ...  # rest unchanged
```

- [ ] **Step 3: Edit `app.py`'s `fetch_place_boundary_local` (currently line 2343)**

```python
@st.cache_data
def fetch_place_boundary_local(state_abbr, place_name_input):
    """Look up a city/town/CDP boundary from local parquet caches.
    Connecticut and Rhode Island towns fall back to county-subdivision data when needed."""
    if is_ca_region(state_abbr):
        return fetch_csd_boundary_local(state_abbr, place_name_input)
    local_files = ["places_lite.parquet"]
    ...  # rest unchanged
```

- [ ] **Step 4: Edit `app.py`'s `fetch_county_by_centroid` (currently line 2234)**

```python
def fetch_county_by_centroid(df_calls, state_abbr):
    """Find the county boundary that contains the median centroid of the call data.
    ...
    """
    if is_ca_region(state_abbr):
        return fetch_cd_by_centroid(df_calls, state_abbr)
    local_file = "counties_lite.parquet"
    ...  # rest unchanged
```

- [ ] **Step 5: Edit `app.py`'s `_lookup_population_for_boundary` (currently line 2454)**

```python
def _lookup_population_for_boundary(state_abbr, city_name, boundary_kind='place'):
    if is_ca_region(state_abbr):
        return fetch_ca_population(state_abbr, city_name or state_abbr, boundary_kind=boundary_kind)
    state_fips = STATE_FIPS.get(str(state_abbr or '').strip().upper(), '')
    ...  # rest unchanged
```

- [ ] **Step 6: Syntax-check the file**

Run: `python -m py_compile app.py`
Expected: no output, exit code 0.

- [ ] **Step 7: Commit**

```bash
git add app.py
git commit -m "feat(ca): mirror Canada dispatch into app.py's inline boundary functions"
```

---

### Task 7: End-to-end smoke check

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `pytest tests/ -v`
Expected: all tests pass, including every test added in Tasks 1-5.

- [ ] **Step 2: Manual UI smoke check (per repo convention — see CLAUDE.md)**

Start the app: `streamlit run app.py`

In the browser:
1. Enter a Canadian jurisdiction manually (e.g. state/province field `ON`, city field `Toronto`) through whichever manual-entry flow exercises `fetch_place_boundary_local`/`fetch_county_boundary_local`.
2. Confirm a boundary renders on the map (not a "boundary not found" warning).
3. Confirm the estimated/reference population field populates with a nonzero value.
4. Repeat once for a US city (e.g. `NY` / `Buffalo`) to confirm the US path is unaffected.

- [ ] **Step 3: Report results**

Record pass/fail for each of the 4 manual checks above. If the boundary or population step fails for the Canadian case, check whether the exact CD/CSD name entered matches the StatCan spelling in `cd_lite.parquet`/`csd_lite.parquet` (per Task 4's note on first-run name calibration) before treating it as a code bug.

No commit for this task — verification only.
