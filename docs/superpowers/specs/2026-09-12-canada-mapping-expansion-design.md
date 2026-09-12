# Canada Mapping Expansion — Design

## Goal

Extend jurisdiction boundary + population lookup (currently US-only, backed
by Census TIGER / US Census API) to also resolve Canadian jurisdictions, so
station-siting works for Canadian incident/CAD data on the same Streamlit
Cloud (GitHub-backed) deployment.

## Scope

In scope:
- Jurisdiction boundary resolution: province, census division (CD, ≈ county),
  census subdivision (CSD, ≈ city/place).
- Population lookup for CD/CSD.
- Postal-code lookup (Canadian FSA) analogous to existing US ZIP lookup.
- Country auto-detection at existing lookup entry points.

Out of scope (explicitly deferred):
- Regulatory airspace overlay (NAV Canada RPAS zones / FAA UASFM-LAANC
  equivalent). FAA-specific code and data (`download_regulatory_layers.py`,
  `faa_uasfm.parquet`) are untouched.
- Geocoding rework. `modules/geocoding.py` already calls Nominatim
  (worldwide-capable); no changes needed beyond what country-detection
  requires.

## Current US Architecture (for reference)

`modules/boundaries.py`:
- `lookup_zip_code()` — live call to `api.zippopotam.us/us/{zip}`.
- `fetch_county_boundary_local()` / `fetch_place_boundary_local()` — read
  bundled lite parquet (`counties_lite.parquet`, `places_lite.parquet`,
  `county_subdivisions_lite.parquet`) committed to the repo.
- `fetch_tiger_state_shapefile()` / `fetch_tiger_county_subdivision_shapefile()`
  / `fetch_tiger_city_shapefile()` — live Census TIGER fetch, used as
  fallback when the bundled lite parquet lacks a geometry.
- `fetch_census_population()` / `fetch_census_state_population()` — live
  Census API calls (not bundled).
- `suggest_boundary_matches()` / `_best_boundary_name_matches()` — fuzzy
  name matching, operates on whatever boundary rows are loaded regardless
  of source country.

## Data Sources (Canada)

| Purpose | Source | Bundled or live |
|---|---|---|
| Province/territory boundary | StatCan Cartographic Boundary Files (CBF) | Bundled lite parquet |
| Census Division (CD) boundary | StatCan CBF | Bundled lite parquet |
| Census Subdivision (CSD) boundary | StatCan CBF | Bundled lite parquet |
| Population (CD/CSD) | StatCan Census Profile (WDS API) | Live, mirrors existing `fetch_census_population` |
| Postal code → city/province | `api.zippopotam.us/ca/{FSA}` | Live, same provider already used for US |

### Why bundle the boundary geometry

Streamlit Cloud's filesystem is ephemeral — no persistent disk cache across
redeploys, so a live-fetch-only design re-hits StatCan's API on every cold
start. The existing US design avoids this by committing lite parquet
straight to the repo; Canada follows the same pattern.

Size estimate: US bundled set (`counties_lite` + `county_subdivisions_lite`
+ `places_lite`) is ~11.8MB total, covering 3,143 counties / ~35k places.
Canada has 13 provinces/territories, ~293 census divisions, ~5,000 census
subdivisions — expect a bundled CA set well under US size (rough estimate
2-4MB), comfortably inside GitHub's per-file limits and Streamlit Cloud's
repo size ceiling.

Population and postal lookups stay live-only (no bundling), matching how
the US path already treats those two (`fetch_census_population` and
`lookup_zip_code` are not bundled today either) — no reliability
regression introduced.

## Code Shape (additive, minimal-diff)

New module: `modules/boundaries_ca.py`
- `lookup_postal_code()` — CA equivalent of `lookup_zip_code()`, calls
  `api.zippopotam.us/ca/{fsa}`.
- `fetch_cd_boundary_local()` / `fetch_csd_boundary_local()` — read bundled
  `cd_lite.parquet` / `csd_lite.parquet`.
- `fetch_statcan_province_shapefile()` / `fetch_statcan_cd_shapefile()` /
  `fetch_statcan_csd_shapefile()` — live StatCan CBF fetch, fallback only.
- `fetch_census_profile_population()` — live StatCan WDS call, mirrors
  `fetch_census_population()`.

`modules/boundaries.py` changes: thin dispatch shim at existing entrypoints
only — detect country, route to existing US logic or `boundaries_ca`
functions. No rewrite of US logic, no shared abstraction layer forced in
(YAGNI — revisit if a third country is ever added).

New bundled files (repo root, same convention as existing `*_lite.parquet`):
- `cd_lite.parquet`
- `csd_lite.parquet`
- (province boundary set is tiny — may fold into one of the above or its
  own `provinces_lite.parquet`, decided during implementation based on
  actual StatCan CBF schema)

`download_regulatory_layers.py`, `faa_uasfm.parquet`,
`modules/geocoding.py`: untouched.

## Country Detection

At existing lookup entry points (`lookup_zip_code` callers, forward-geocode
paths):
- Postal-code input: regex — `^\d{5}$` → US ZIP, `^[A-Za-z]\d[A-Za-z]` →
  Canadian FSA. Route accordingly.
- Lat/lon input: Nominatim reverse-geocode already returns `country_code`;
  use it to route instead of re-deriving from postal code.

No user-facing country toggle — routing is internal and automatic.

## Error Handling

Same fallback chain as the US path:
1. Bundled lite parquet lookup (fast, offline).
2. On miss, live StatCan CBF fetch, cached to disk for the session.
3. On no match, falls through to existing `suggest_boundary_matches()`
   fuzzy matcher — works unmodified once CA boundary rows are loaded,
   since it matches on name strings without a country-specific branch.

## Testing

New fixtures mirroring `tests/test_boundary_suggestions.py`: a handful of
known CA postal codes / CD / CSD names (e.g. Toronto ON, Calgary AB)
verifying the full resolve → boundary → population chain, plus a
country-detection unit test covering the US-ZIP / CA-FSA regex branch and
the Nominatim `country_code` branch.

## Workflow

Repo currently has unrelated uncommitted local work (`app.py`,
`modules/dashboard_helpers.py`, `modules/stations.py`, a new untracked
test file) — left untouched per repo rules. This feature should be done
on its own branch or worktree (e.g. `feature/canada-mapping`) to avoid
colliding with that in-progress work.
