# USGS Stations and Jurisdiction Call Share Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add boundary-only USGS fire/EMS and police station candidates and display correct independent call-containment percentages for nested jurisdictions.

**Architecture:** Add a focused USGS ArcGIS adapter to the existing station-generation module, normalize and merge its rows with existing facility sources, then filter all generated facilities against the selected boundary before optimization. Preserve the coordinate detector's existing `call_share` value and make sidebar label generation a pure helper so nested-boundary behavior is directly testable.

**Tech Stack:** Python, pandas, GeoPandas, Shapely, Streamlit cache, urllib, ArcGIS REST JSON, pytest.

## Global Constraints

- USGS candidates must fall strictly inside the selected jurisdiction boundary.
- Fire/EMS is FCode 74026; law enforcement is FCode 74034.
- External-source failure must degrade gracefully to the existing source chain.
- Synthetic candidates must not be described as actual police or fire stations.
- Preserve unrelated work and avoid optimizer or UI redesign.

---

### Task 1: USGS National Structures adapter

**Files:**
- Modify: `modules/stations.py`
- Create: `tests/test_usgs_station_lookup.py`

**Interfaces:**
- Produces: `_fetch_usgs_nsd_stations_cached(min_lat, min_lon, max_lat, max_lon) -> tuple[list[dict] | None, str]`
- Produces normalized rows containing `name`, `address`, `lat`, `lon`, `type`, and `source`.

- [ ] Write failing tests for Fire/EMS and Police ArcGIS responses, allowed FCodes, malformed coordinates, timeouts, and empty results.
- [ ] Run `python -m pytest tests/test_usgs_station_lookup.py -q` and confirm failures are caused by the missing adapter.
- [ ] Implement the two layer queries with explicit envelope parameters, `outSR=4326`, bounded timeout, FCode validation, and `USGS_NSD` source tagging.
- [ ] Run the focused test and confirm it passes.

### Task 2: Candidate merge, deduplication, and fallback names

**Files:**
- Modify: `modules/stations.py`
- Modify: `tests/test_usgs_station_lookup.py`

**Interfaces:**
- Consumes: normalized USGS rows from Task 1.
- Produces: merged candidate rows with USGS preferred over duplicate HIFLD, OSM, or public-geocoder facilities.

- [ ] Add failing tests proving USGS is queried alongside existing sources, preferred during proximity/type deduplication, and retained when another source fails.
- [ ] Add a failing test proving synthetic fallback names use `Proposed Call-Density Site` and do not claim Police or Fire identity.
- [ ] Run the focused tests and confirm the expected failures.
- [ ] Integrate USGS into both jurisdiction-context and bounding-box lookup paths; implement minimal deduplication and fallback-label changes.
- [ ] Run the focused tests and confirm they pass.

### Task 3: Strict jurisdiction-boundary filtering

**Files:**
- Modify: `modules/dashboard_helpers.py`
- Modify: `tests/test_usgs_station_lookup.py`

**Interfaces:**
- Consumes: generated candidate DataFrame and selected boundary geometry.
- Produces: candidate DataFrame containing only points strictly within the active boundary for non-uploaded stations.

- [ ] Add a failing test with one USGS point inside and one outside a test polygon.
- [ ] Run the test and verify the outside point is currently retained.
- [ ] Apply the existing non-uploaded station boundary mask consistently to generated USGS candidates before optimization.
- [ ] Run the focused test and confirm only the inside point remains.

### Task 4: Independent jurisdiction call-share labels

**Files:**
- Modify: `modules/onboarding.py`
- Modify: `modules/dashboard_helpers.py`
- Create: `tests/test_jurisdiction_call_share.py`

**Interfaces:**
- Preserves: `call_share: float` from coordinate detection through `master_gdf_override`.
- Produces: `build_jurisdiction_labels(master_gdf) -> pandas.DataFrame` or equivalent pure label helper used by the sidebar.

- [ ] Add failing tests with Raleigh `call_share=0.9806` and Wake County `call_share=0.9998`, expecting `98.1% of calls` and `100.0% of calls` rather than normalized 49.5%/50.5%.
- [ ] Add a compatibility test for rows without `call_share`.
- [ ] Run the focused tests and confirm the nested-boundary test fails.
- [ ] Preserve `call_share` in onboarding and implement the pure label calculation used by the sidebar.
- [ ] Run the focused tests and confirm they pass.

### Task 5: Attribution and complete verification

**Files:**
- Modify: `app.py`
- Modify: `modules/html_reports.py`

**Interfaces:**
- Updates visible and exported station-source attribution only.

- [ ] Update live and exported source strings to name `USGS National Structures Dataset` while retaining HIFLD and OpenStreetMap attribution.
- [ ] Run `python -m pytest tests/test_usgs_station_lookup.py tests/test_jurisdiction_call_share.py -q`.
- [ ] Run `python -m pytest -q` and require zero failures.
- [ ] Run `python -m py_compile app.py modules/stations.py modules/onboarding.py modules/dashboard_helpers.py modules/html_reports.py`.
- [ ] Run `git diff --check` and inspect `git diff --stat` plus the complete diff.
- [ ] Run a Raleigh CSV smoke script that parses valid coordinates, queries the USGS adapter, clips results to the selected boundary, and prints Raleigh/Wake independent call shares without writing files.
