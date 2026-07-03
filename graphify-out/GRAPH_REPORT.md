# Graph Report - Frankenstein  (2026-07-03)

## Corpus Check
- 70 files · ~250,032 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1295 nodes · 2188 edges · 83 communities (75 shown, 8 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 31 edges (avg confidence: 0.76)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5c49474f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]

## God Nodes (most connected - your core abstractions)
1. `main()` - 54 edges
2. `Internal Terms of Use` - 27 edges
3. `main()` - 26 edges
4. `DataFrame` - 24 edges
5. `DataFrame` - 21 edges
6. `render()` - 18 edges
7. `Frankenstein FAQ` - 16 edges
8. `aggressive_parse_calls()` - 14 edges
9. `log_crash()` - 14 edges
10. `Frequently Asked Questions` - 14 edges

## Surprising Connections (you probably didn't know these)
- `resolve_master_boundary()` --calls--> `get_jurisdiction_message()`  [INFERRED]
  _promotion_backup_20260423_191137/modules/dashboard_helpers.py → modules/config.py
- `render_sidebar_jurisdiction_selector()` --calls--> `get_themed_logo_base64()`  [INFERRED]
  _promotion_backup_20260423_191137/modules/dashboard_helpers.py → modules/image_utils.py
- `main()` --calls--> `get_export_disclaimer_text()`  [INFERRED]
  app.py → modules/compliance_guard.py
- `resolve_uploaded_boundaries()` --calls--> `find_jurisdictions_by_coordinates()`  [INFERRED]
  _promotion_backup_20260423_191137/modules/onboarding.py → modules/geospatial.py
- `_render_public_report_route()` --calls--> `_public_report_metadata_path()`  [INFERRED]
  app.py → modules/public_reports.py

## Import Cycles
- None detected.

## Communities (83 total, 8 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.07
Nodes (61): aggressive_parse_calls(), _deduplicate_columns(), _extract_file_meta(), _normalize_jacksonville_cfs_report(), _normalize_loxley_priority_calls_report(), CAD file parser and metadata extraction for BRINC app., # IMPORTANT: keep the full parsed CAD dataset here., Flatten the Jacksonville PD CFS report into one row per incident. (+53 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (51): BaseModel, CrashEvent, FlightTelemetrySnapshot, compute_debris_radius(), compute_impact_energy(), compute_parachute_descent_velocity(), compute_parachute_drift(), parachute_outcome() (+43 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (35): calculate_max_flights_per_day(), get_airfield_message(), get_csm_for_state(), get_faa_message(), get_hero_message(), get_spatial_message(), Global configuration, constants, and theme variables for BRINC Drone-First Respo, Get CSM info for a given state abbreviation. (+27 more)

### Community 3 - "Community 3"
Cohesion: 0.12
Nodes (19): _parse_datetime_series(), _build_cad_charts_html(), build_high_activity_staffing_html(), _build_unit_cards_html(), _detect_datetime_series_for_labels(), estimate_high_activity_overtime(), estimate_specialty_response_savings(), format_3_lines() (+11 more)

### Community 4 - "Community 4"
Cohesion: 0.10
Nodes (33): Census Batch Geocoding, merge_census_results(), Merge CAD data with Census batch geocoding results.      This function now use, DataFrame, Pandera schemas for DataFrame validation.  These schemas enforce data integrit, Validate raw CAD DataFrame after parsing.      Args:         df: DataFrame to, Validate CAD DataFrame with coordinate columns.      Args:         df: DataFr, Validate Census batch geocoding results.      Args:         df: DataFrame to (+25 more)

### Community 5 - "Community 5"
Cohesion: 0.16
Nodes (33): DataFrame, build_census_chunk_payload(), build_census_staging(), build_corrected_export(), _build_street_series(), _clean_state(), _clean_text(), _clean_zip() (+25 more)

### Community 6 - "Community 6"
Cohesion: 0.11
Nodes (24): _allocate_demo_counts(), _coord_column_matches(), _estimate_demo_preview_points(), _extract_station_lat_lon(), _find_station_coord_column(), infer_simulation_targets_from_station_file(), _looks_like_station_upload_content(), _normalize_station_state_abbr() (+16 more)

### Community 7 - "Community 7"
Cohesion: 0.05
Nodes (56): _add_boundary_geometry_traces(), add_cell_towers_layer_to_plotly(), add_no_fly_zones_layer_to_plotly(), _apply_admin_fast_jump(), _boundary_palette(), _build_carrier_mini_map(), calculate_max_flights_per_day(), _dashed_line_coords() (+48 more)

### Community 8 - "Community 8"
Cohesion: 0.12
Nodes (17): _log_qr_scan_to_sheets(), _log_to_sheets(), _notify_email(), _render_public_report_route(), _build_sheets_row(), _log_login_to_sheets(), _log_qr_scan_to_sheets(), _log_to_sheets() (+9 more)

### Community 9 - "Community 9"
Cohesion: 0.06
Nodes (48): BaseException, build_corrected_export_from_merged(), Build the corrected Census export from an already merged dataframe.      This, get_jurisdiction_message(), log_crash(), Log a crash to stdout and configured external sinks., find_jurisdictions_by_coordinates(), Purely coordinate-driven jurisdiction lookup.      Spatially joins call points (+40 more)

### Community 10 - "Community 10"
Cohesion: 0.24
Nodes (11): forward_geocode(), forward_geocode_with_context(), _forward_geocode_with_context_cached(), _get_geocoder_provider_signature(), _get_google_maps_api_key(), _get_mapbox_api_key(), lookup_county_for_city(), _lookup_streamlit_secret() (+3 more)

### Community 11 - "Community 11"
Cohesion: 0.09
Nodes (20): _build_public_report_url(), _df_latlon_signature(), fetch_county_by_centroid(), _fetch_hifld_stations_cached(), _fetch_osm_stations_cached(), find_relevant_jurisdictions(), generate_clustered_calls(), generate_random_points_in_polygon() (+12 more)

### Community 12 - "Community 12"
Cohesion: 0.15
Nodes (19): _count_points_within_boundary(), Count calls (points) that fall within a boundary polygon., _build_context_station_rows(), _build_public_facility_rows(), _count_points_within_boundary(), _derive_jurisdiction_lookup_contexts(), _fetch_hifld_stations_cached(), _fetch_osm_stations_cached() (+11 more)

### Community 13 - "Community 13"
Cohesion: 0.27
Nodes (8): Save boundary to a type-specific shapefile base so place/county do not overwrite, save_boundary_gdf(), generate_clustered_calls(), generate_random_points_in_polygon(), load_fast_demo_payload(), _prepare_sampling_polygon(), Geospatial utilities - random point generation, clustering, circle coordinates., Build and cache the smallest useful payload for Path 03.

### Community 14 - "Community 14"
Cohesion: 0.12
Nodes (18): get_address_from_latlon(), Generate a self-contained HTML block for the PDF/HTML export.      Includes th, Safely serialize a DataFrame to a JSON-safe list of records.      Returns an e, Estimate additional annual savings from thermal-enabled search efficiency and av, Return a best-effort parsed datetime series from common CAD field patterns., Return an HTML block for the High-Activity Staffing Pressure section., Generates the full Command Center visual suite with interactive Javascript filte, Estimate high-activity monthly staffing pressure and officer overtime replacemen (+10 more)

### Community 15 - "Community 15"
Cohesion: 0.08
Nodes (31): _apply_admin_fast_jump(), _get_admin_dashboard_emails(), _get_query_params_dict(), _is_admin_dashboard_user(), _live_admin_dashboard_fragment(), _presence_heartbeat_fragment(), _prune_active_sessions(), Admin dashboard and session management functions. (+23 more)

### Community 16 - "Community 16"
Cohesion: 0.12
Nodes (21): _git_commit_timestamp(), _git_short_hash(), _compute_build_info(), _count_app_lines(), get_build_info(), _git_revision(), Build version management for BRINC app., Read stored build timestamp and revision from .build_meta. (+13 more)

### Community 17 - "Community 17"
Cohesion: 0.19
Nodes (17): _boundary_shp_base(), fetch_census_population(), fetch_census_state_population(), fetch_county_by_centroid(), _get_census_api_key(), load_saved_boundary(), lookup_county_for_city(), _lookup_known_population() (+9 more)

### Community 18 - "Community 18"
Cohesion: 0.13
Nodes (19): Count app.py lines for build metadata logging., Compute the version string and related build metadata., Return a copy of the current build metadata., Render version badge in top-right or bottom-right corner., Persist the latest app.py timestamp and revision., Read the revision stored when versioning was introduced., Return a stable revision derived from git history when available., Advance the revision when app.py has been saved since the last recorded build. (+11 more)

### Community 19 - "Community 19"
Cohesion: 0.15
Nodes (11): build_demo_boundaries(), clear_stale_boundary_shapefiles(), _extract_single_column_station_addresses(), load_simulation_custom_stations(), load_station_file(), _normalize_display_text(), _normalize_station_columns(), Helpers for onboarding and saved deployment restore. (+3 more)

### Community 20 - "Community 20"
Cohesion: 0.11
Nodes (19): add_cell_towers_layer_to_plotly(), add_no_fly_zones_layer_to_plotly(), _build_carrier_mini_map(), calculate_max_flights_per_day(), estimate_grants(), generate_stations_from_calls(), get_circle_coords(), _get_document_jurisdiction_name() (+11 more)

### Community 21 - "Community 21"
Cohesion: 0.18
Nodes (19): forward_geocode(), geocode_intersection_fallback_rows(), _get_geocoder_provider_signature(), _get_google_maps_api_key(), _get_mapbox_api_key(), _lookup_streamlit_secret(), _normalize_public_facility_type(), _public_facility_candidate_is_plausible() (+11 more)

### Community 22 - "Community 22"
Cohesion: 0.06
Nodes (32): 1. `modules/data_models.py` (258 lines), 1. `requirements.txt`, 2. `modules/census_batch.py`, 2. `modules/data_validation.py` (284 lines), 3. `modules/efficient_merge.py` (428 lines), 4. `INTEGRATION_GUIDE.md` (500+ lines), 5. `SKILLS_USAGE.md` (200+ lines), Automatic (No Code Changes Required) (+24 more)

### Community 23 - "Community 23"
Cohesion: 0.18
Nodes (15): download_airfields_us_with_retry(), generate_mock_airfields_us(), generate_mock_cell_towers_for_state(), generate_mock_faa_airspace_for_state(), generate_mock_faa_obstacles(), generate_mock_no_fly_zones(), load_cell_towers_from_local_gz(), main() (+7 more)

### Community 24 - "Community 24"
Cohesion: 0.17
Nodes (14): add_coverage_traces(), _build_carrier_mini_map(), _carrier_coverage_analysis(), _coverage_geom_cache_key(), _get_coverage_analysis_cache(), _load_coverage(), _load_dissolved_coverage(), Coverage analysis and carrier analysis functions. (+6 more)

### Community 25 - "Community 25"
Cohesion: 0.12
Nodes (23): _boundary_shp_base(), fetch_county_boundary_local(), fetch_place_boundary_local(), fetch_tiger_city_shapefile(), fetch_tiger_county_subdivision_shapefile(), fetch_tiger_state_shapefile(), generate_clustered_calls(), generate_random_points_in_polygon() (+15 more)

### Community 26 - "Community 26"
Cohesion: 0.16
Nodes (16): GeoDataFrame, _boundary_overlay_status(), build_display_calls(), Geospatial utilities - boundaries, geocoding, station generation., bounded_station_avg_distance_miles(), compute_all_elbow_curves(), mean_covered_distance_miles(), precompute_spatial_data() (+8 more)

### Community 27 - "Community 27"
Cohesion: 0.25
Nodes (5): Deployment Map UI, Dashboard Helpers, HTML Report Generator, init_session_state(), Session-state helpers for the Streamlit app.

### Community 28 - "Community 28"
Cohesion: 0.23
Nodes (5): get_circle_coords(), _plot_rf_coverage_map(), FAA airspace, regulatory layers, and RF coverage analysis., _rf_surface_for_layer(), _summarize_rf_grid()

### Community 29 - "Community 29"
Cohesion: 0.21
Nodes (11): _estimate_clutter_loss_db(), _estimate_elevation_simple(), _estimate_terrain_blockage_db(), _get_terrain_cache(), _path_loss_advanced(), RF propagation models - path loss, elevation, clutter, and terrain blockage., Estimate clutter/foliage/building loss based on land-use class.     Returns dB, Global cache dict for DEM tiles to avoid re-downloading. (+3 more)

### Community 30 - "Community 30"
Cohesion: 0.18
Nodes (11): add_coverage_traces(), _carrier_coverage_analysis(), _coverage_geom_cache_key(), _get_coverage_analysis_cache(), _load_coverage(), _load_dissolved_coverage(), Returns the shared analysis-result dict for this worker process., Load raw cell_coverage/{STATE}.parquet rows; returns GeoDataFrame or None. (+3 more)

### Community 31 - "Community 31"
Cohesion: 0.07
Nodes (30): 1. In `modules/census_batch.py`, 1. `modules/data_models.py`, 2. `modules/data_validation.py`, 2. Optional: Use Pydantic Models for Clarity, 3. `modules/efficient_merge.py`, 3. Optional: Validate at Key Checkpoints, Data Processing Library Integration Guide, `deduplicate_coordinates(df, keep='best')` (+22 more)

### Community 32 - "Community 32"
Cohesion: 0.18
Nodes (11): add_cell_towers_layer_to_plotly(), add_faa_obstacles_layer_to_plotly(), add_no_fly_zones_layer_to_plotly(), generate_mock_faa_grid(), load_cached_regulatory_layers(), load_faa_parquet(), Add OpenCelliD cell tower markers to map., Add FAA Digital Obstacle File (obstacles > 200 ft) to map. (+3 more)

### Community 33 - "Community 33"
Cohesion: 0.20
Nodes (10): build_corridor_demo(), build_corridor_polygon(), estimate_corridor_calls(), fetch_highway_geometry(), _generate_corridor_calls(), Fetch highway geometry from Overpass API, clipped to the given state.      Arg, Buffer a highway LineString to create a corridor polygon.      Returns:, Estimate annual calls for service along a highway corridor.      Formula: corr (+2 more)

### Community 34 - "Community 34"
Cohesion: 0.20
Nodes (10): Buffer a highway LineString to create a corridor polygon.      Returns:, Estimate annual calls for service along a highway corridor.      Formula: corr, Place call points along the highway corridor.      75% distributed near the ro, Build a simulated calls DataFrame for a highway corridor.      Returns:, build_corridor_demo(), build_corridor_polygon(), estimate_corridor_calls(), fetch_highway_geometry() (+2 more)

### Community 35 - "Community 35"
Cohesion: 0.18
Nodes (11): add_coverage_traces(), _carrier_coverage_analysis(), _coverage_geom_cache_key(), _get_coverage_analysis_cache(), _load_coverage(), _load_dissolved_coverage(), Returns the shared analysis-result dict for this worker process., Load raw cell_coverage/{STATE}.parquet rows; returns GeoDataFrame or None. (+3 more)

### Community 36 - "Community 36"
Cohesion: 0.20
Nodes (10): _estimate_clutter_loss_db(), _estimate_elevation_simple(), _estimate_terrain_blockage_db(), _get_terrain_cache(), _path_loss_advanced(), Global cache dict for DEM tiles to avoid re-downloading., Fetch elevation for a point (cached) — fallback to 100 ft if unavailable., Estimate clutter/foliage/building loss based on land-use class.     Returns dB (+2 more)

### Community 37 - "Community 37"
Cohesion: 0.19
Nodes (17): reverse_geocode_state(), fetch_census_population(), fetch_census_state_population(), _get_census_api_key(), _lookup_known_population(), _lookup_population_for_boundary(), _normalize_population_lookup_name(), _population_lookup_aliases() (+9 more)

### Community 38 - "Community 38"
Cohesion: 0.22
Nodes (10): _compute_rf_grid_coverage(), _estimate_clutter_loss_db(), _estimate_elevation_simple(), _estimate_terrain_blockage_db(), _path_loss_advanced(), Fetch elevation for a point (cached) â€” fallback to 100 ft if unavailable., Estimate clutter/foliage/building loss based on land-use class.     Returns dB, Estimate terrain blockage loss using simple Fresnel zone calculation.     If mi (+2 more)

### Community 39 - "Community 39"
Cohesion: 0.07
Nodes (27): 10. Confidentiality, 11. Security, 12. Retention and Deletion, 13. Compliance and Export Controls, 14. Availability and Changes, 15. Disclaimers, 16. Limitation of Liability, 17. Indemnity (+19 more)

### Community 40 - "Community 40"
Cohesion: 0.22
Nodes (9): add_coverage_traces(), _carrier_coverage_analysis(), _coverage_geom_cache_key(), _load_coverage(), _load_dissolved_coverage(), Load raw cell_coverage/{STATE}.parquet rows; returns GeoDataFrame or None., Load carrier-dissolved statewide coverage, used only for the full-map overlay., Add AT&T / T-Mobile / Verizon 4G LTE polygon traces. (+1 more)

### Community 41 - "Community 41"
Cohesion: 0.36
Nodes (8): fetch_metra_geometry(), _geometry_from_overpass_elements(), metra_code_from_label(), metra_label_from_code(), _query_overpass(), Helpers for loading Metra route geometry., Fetch Metra route geometry from OpenStreetMap route relations., _route_ref_pattern()

### Community 42 - "Community 42"
Cohesion: 0.31
Nodes (9): forward_geocode(), _get_geocoder_provider_signature(), _get_google_maps_api_key(), _get_mapbox_api_key(), lookup_county_for_city(), _lookup_streamlit_secret(), Use Nominatim reverse-geocode to find the county name for a city that     doesn, search_address_candidates() (+1 more)

### Community 43 - "Community 43"
Cohesion: 0.20
Nodes (10): _get_annualized_calls(), Return raw_count scaled to a full year using the uploaded file's date span., _build_apprehension_table(), _build_cad_charts(), Compute and render the Drone Apprehension Impact Value table.        Derived, Compute and render the Drone Apprehension Impact Value table.        Derived, Render apprehension impact table + top call types chart., Render apprehension impact table + top call types chart. (+2 more)

### Community 44 - "Community 44"
Cohesion: 0.29
Nodes (7): get_export_disclaimer_text(), init_compliance_state(), _is_sensitive_classification(), Lightweight compliance guardrails for internal and customer-facing exports., Install defaults for the sidebar compliance checklist., Render a compact sidebar checklist and return the current completion state., render_compliance_sidebar()

### Community 45 - "Community 45"
Cohesion: 0.36
Nodes (5): _df_latlon_signature(), find_relevant_jurisdictions(), get_relevant_jurisdictions_cached(), _jurisdiction_scan_signature(), Utility functions for caching, hashing, and display calculations.

### Community 46 - "Community 46"
Cohesion: 0.31
Nodes (9): _normalize_public_facility_type(), _public_facility_candidate_is_plausible(), _public_facility_candidate_score(), _public_facility_label_is_plausible(), _public_facility_query_variants(), _public_facility_type_is_plausible(), _reverse_geocode_public_facility_meta(), search_public_facility_candidates() (+1 more)

### Community 47 - "Community 47"
Cohesion: 0.25
Nodes (8): _estimate_clutter_loss_db(), _estimate_elevation_simple(), _estimate_terrain_blockage_db(), _path_loss_advanced(), Fetch elevation for a point (cached) — fallback to 100 ft if unavailable., Estimate clutter/foliage/building loss based on land-use class.     Returns dB, Estimate terrain blockage loss using simple Fresnel zone calculation.     If mi, Advanced path loss model combining multiple effects:       PL_total = FSPL + cl

### Community 48 - "Community 48"
Cohesion: 0.29
Nodes (6): git, python, ruff, git, pytest, ruff

### Community 49 - "Community 49"
Cohesion: 0.38
Nodes (7): fetch_census_population(), fetch_census_state_population(), _lookup_known_population(), _lookup_population_for_boundary(), _normalize_population_lookup_name(), _population_lookup_aliases(), _refresh_reference_population()

### Community 50 - "Community 50"
Cohesion: 0.33
Nodes (7): fetch_county_boundary_local(), fetch_place_boundary_local(), fetch_tiger_city_shapefile(), normalize_jurisdiction_name(), Look up a city/town/CDP boundary from the local places_lite.parquet.     Return, Try place and county boundaries and keep the candidate containing the most uploa, _select_best_boundary_for_calls()

### Community 51 - "Community 51"
Cohesion: 0.11
Nodes (17): 10. Can it be used without internet access?, 11. What should I do if the map layers are missing?, 12. What should I do if my incident upload does not produce useful results?, 13. What is the main benefit of using this software?, 1. What does this software do?, 2. Who is this software built for?, 3. What kind of inputs does it use?, 4. How does it know which jurisdiction to analyze? (+9 more)

### Community 52 - "Community 52"
Cohesion: 0.22
Nodes (10): _build_corrected_export_from_merged_fallback(), _build_historical_response_time_summary(), _fetch_osm_stations_cached(), _find_response_metric_column(), _make_random_stations(), DataFrame, Fallback station generator based on call-density hotspots.      If a city boun, Cache-friendly OSM query keyed on rounded centroid (2 dp ≈ 1 km grid).     Retu (+2 more)

### Community 53 - "Community 53"
Cohesion: 0.11
Nodes (17): 1. POLARS - Fast DataFrame Operations, 2. PANDERA - DataFrame Validation, 3. PYDANTIC - Type-Safe Data Models, 4. DASK - Distributed Computing, Common Patterns, Dask, Integration Status, New Skills Usage Guide (+9 more)

### Community 54 - "Community 54"
Cohesion: 0.40
Nodes (4): main(), process_file(), Path, Recompress cell_coverage/*.parquet files:   1. geometry_wkb hex string  ->  bina

### Community 55 - "Community 55"
Cohesion: 0.33
Nodes (5): add_cell_towers_layer_to_plotly(), add_no_fly_zones_layer_to_plotly(), Plotly map layer functions for cell towers, no-fly zones, and coverage., Add no-fly zones (parks, water, restricted areas) to map., Add OpenCelliD cell tower markers to map.

### Community 56 - "Community 56"
Cohesion: 0.33
Nodes (6): _boundary_shp_base(), load_saved_boundary(), Save boundary to a type-specific shapefile base so place/county do not overwrite, Load a previously saved boundary, preferring the exact typed name., _sanitize_boundary_token(), save_boundary_gdf()

### Community 58 - "Community 58"
Cohesion: 0.50
Nodes (4): add_faa_laanc_layer_to_plotly(), _normalize_display_text(), Returns list of (label, hex_color, radius_miles) for 3 SNR tiers at 3390 MHz., _rf_range_rings_3390()

### Community 59 - "Community 59"
Cohesion: 0.50
Nodes (4): fetch_airfields(), load_cached_airfields(), Uses the pre-cached US dataset only.     Runtime network lookups are intentiona, Load all US airfields from pre-cached parquet.

### Community 60 - "Community 60"
Cohesion: 0.50
Nodes (3): Render components for the main application., Render in-app FAQ/Help panel with version and changelog.      Args:         _, render_in_app_faq()

### Community 61 - "Community 61"
Cohesion: 0.11
Nodes (17): Are FAA and regulatory overlays included?, Do I need internet access to run it?, Does the app choose stations automatically?, Frankenstein FAQ, How do I start the software locally?, How does it determine the jurisdiction?, Is this a real-time dispatch system?, What are Responder and Guardian drones in the app? (+9 more)

### Community 66 - "Community 66"
Cohesion: 0.19
Nodes (13): Any, Logger, LogRecord, _as_bool(), _as_float(), BetterStackHandler, configure_crash_logging(), _normalize_better_stack_host() (+5 more)

### Community 67 - "Community 67"
Cohesion: 0.13
Nodes (14): 1. Create Google Cloud Project, 2. Enable Google Drive API, 3. Create Service Account, 4. Create and Download JSON Key, 5. Share Google Drive Folder with Service Account, Configure Streamlit Secrets, Google Drive Setup for Site Survey App, Local Development (+6 more)

### Community 68 - "Community 68"
Cohesion: 0.17
Nodes (16): fetch_county_boundary_local(), fetch_place_boundary_local(), fetch_tiger_city_shapefile(), fetch_tiger_county_subdivision_shapefile(), fetch_tiger_state_shapefile(), lookup_zip_code(), _match_local_boundary_rows(), normalize_jurisdiction_name() (+8 more)

### Community 69 - "Community 69"
Cohesion: 0.13
Nodes (15): 1. Create and activate a virtual environment, 2. Install dependencies, 3. Configure Streamlit secrets, 4. Cache regulatory layers, 5. Run the app, Architecture Notes, Current Repo State, Data Expectations (+7 more)

### Community 70 - "Community 70"
Cohesion: 0.18
Nodes (10): CAD Upload Skill, Census Batch Geocoding Skill, Coordinate Recovery Skill, Core App, Current UX Skill, Files To Inspect First For Upload/Geocoding Work, Important Merge Behavior, Known Data Characteristics (+2 more)

### Community 71 - "Community 71"
Cohesion: 0.20
Nodes (9): 📚 Documentation, 📞 Help, 💡 Key Features, Load Times, ⏱️ Performance Expectations, ✅ Quick Verification, Regulatory Layers — Quick Start Guide, 🚀 TL;DR (+1 more)

### Community 72 - "Community 72"
Cohesion: 0.25
Nodes (7): Core App, Current UX, Files To Inspect First, Geospatial Data Safety, Project Skills, Streamlit Monolith Surgery, Validation

### Community 74 - "Community 74"
Cohesion: 0.40
Nodes (4): Agent rules, Codex behavior request, Prompting preference, Recommended workflow

### Community 75 - "Community 75"
Cohesion: 0.40
Nodes (5): "Cell towers or no-fly zones missing", "Download is slow/timing out", "FAA layer is still slow", "Layers aren't showing", 🛠️ Troubleshooting

### Community 76 - "Community 76"
Cohesion: 0.50
Nodes (4): Data Added, File Sizes, Performance, 📊 What Changed

### Community 77 - "Community 77"
Cohesion: 0.50
Nodes (4): Immediate (Done!), 🎯 Next Steps, Optional — Future Enhancement, Optional — Monthly

### Community 78 - "Community 78"
Cohesion: 0.50
Nodes (4): In Coverage Map section, look for:, Toggle Behavior, 🗺️ Using New Layers, What to Look For

### Community 79 - "Community 79"
Cohesion: 0.50
Nodes (4): 📥 Installation (First-Time Only), Step 1: Install requests library, Step 2: Download & cache regulatory data, Step 3: Launch app

### Community 81 - "Community 81"
Cohesion: 0.67
Nodes (3): Automated refresh (optional), 🔄 Keeping Data Fresh, Monthly refresh (optional but recommended)

## Knowledge Gaps
- **200 isolated node(s):** `python`, `ruff`, `git`, `Path`, `LogRecord` (+195 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `_render_public_report_route()` connect `Community 8` to `Community 9`, `Community 15`, `Community 7`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Why does `_public_report_metadata_path()` connect `Community 15` to `Community 8`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Why does `main()` connect `Community 7` to `Community 0`, `Community 2`, `Community 6`, `Community 8`, `Community 9`, `Community 41`, `Community 43`, `Community 44`, `Community 52`, `Community 25`, `Community 30`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `main()` (e.g. with `aggressive_parse_calls()` and `_get_annualized_calls()`) actually correct?**
  _`main()` has 9 INFERRED edges - model-reasoned connections that need verification._
- **What connects `python`, `ruff`, `git` to the rest of the system?**
  _507 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.07055630936227951 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.0647307924984876 - nodes in this community are weakly interconnected._