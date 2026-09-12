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
| Population (province/CD/CSD) | StatCan 2021 Population and Dwelling Counts | Bundled as a `POPULATION` column, joined at build time |
| Postal code → city/province | `api.zippopotam.us/ca/{FSA}` | Live, same provider already used for US |

**Revised during implementation planning:** population is bundled, not a
live call. StatCan's Web Data Service has no simple "population by name"
REST endpoint analogous to the US Census Bureau API (`fetch_census_population`
in the US path) — the practical option is joining population once at
lite-parquet build time and shipping it as a `POPULATION` column alongside
the boundary geometry it's already bundling. One fewer live integration,
one fewer runtime failure mode; no scope change.

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

Unlike the US TIGER lite files (a partial subset needing a live fallback
for misses), the bundled CA set is StatCan's *complete* province/CD/CSD
list — so no live StatCan boundary-fetch fallback is needed at all.

Only the postal-code lookup stays live, matching how the US path already
treats `lookup_zip_code` (not bundled today either) — no reliability
regression introduced.

## Code Shape (additive, minimal-diff)

New module: `modules/boundaries_ca.py`
- `is_ca_region()` / `detect_country_from_postal()` — country routing helpers.
- `lookup_postal_code_ca()` — CA equivalent of `lookup_zip_code()`, calls
  `api.zippopotam.us/ca/{fsa}`.
- `fetch_cd_boundary_local()` / `fetch_csd_boundary_local()` / `fetch_cd_by_centroid()`
  — read bundled `cd_lite.parquet` / `csd_lite.parquet` (no live fallback needed;
  see "Why bundle the boundary geometry" above).
- `fetch_ca_population()` — reads the bundled `POPULATION` column from
  `provinces_lite.parquet` / `cd_lite.parquet` / `csd_lite.parquet`.

**Revised during implementation planning — there are two call sites, not
one.** `modules/boundaries.py` is a "library" copy consumed by
`modules/stations.py`, `modules/onboarding.py`, and
`modules/geospatial_utils.py`. But `app.py` — the live entry point for the
main manual-entry UI — does **not** import `modules/boundaries.py`; it has
its own near-identical inline duplicate of `lookup_zip_code`,
`fetch_county_boundary_local`, `fetch_place_boundary_local`,
`fetch_county_by_centroid`, and the population functions. Both copies need
the same thin dispatch branch added (detect country, route to
`boundaries_ca` or fall through to existing US logic unchanged) — this
mirrors the duplication already present in the repo rather than
introducing a refactor to deduplicate it, per the "don't refactor shared
code unless required" repo rule. `app.py`'s own `lookup_zip_code` is
confirmed dead code (no callers anywhere in the repo) and is left
untouched.

New bundled files (repo root, same convention as existing `*_lite.parquet`):
- `provinces_lite.parquet`
- `cd_lite.parquet`
- `csd_lite.parquet`

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

**Implementation note:** the lat/lon + Nominatim `country_code` mechanism
above was superseded during implementation. Every call site in this
codebase resolves a state/province abbreviation before reaching a boundary
or population lookup, so dispatch was implemented once, at that point, via
`is_ca_region(state_abbr)` checks. This is a strict superset of the
`country_code` mechanism — there was never a code path that had lat/lon
but not an abbreviation — so the reverse-geocode branch was a deliberate
simplification, not an oversight.

## Error Handling

Bundled lite parquet lookup only (fast, offline) — no live fallback, since
the bundled CD/CSD set is StatCan's complete list rather than a partial
subset. A miss returns `(False, None)` the same way the US path does for
an unmatched county/place.

`suggest_boundary_matches()` (fuzzy name suggestions used in onboarding
warning messages) is not extended for Canada in this pass — out of scope;
it degrades gracefully (returns `[]`) for a CA province abbreviation since
`STATE_FIPS.get()` returns `None` for it.

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
