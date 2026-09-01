# USGS Stations and Jurisdiction Call Share Design

## Goal

Add official USGS National Structures Dataset fire/EMS and police facilities to the automatically generated station candidate pool, restrict those candidates to the selected jurisdiction boundary, and replace the misleading normalized jurisdiction percentages with each boundary's actual share of sampled valid calls.

## Station source design

Query the official USGS National Map Structures ArcGIS service by the cleaned call-coordinate bounding box:

- Fire Stations/EMS Stations: feature layer 51, FCode 74026.
- Police Stations: feature layer 53, FCode 74034.

Normalize each result to the existing station schema: `name`, `address`, `lat`, `lon`, `type`, and `source="USGS_NSD"`. Reject malformed coordinates and unexpected FCodes. Cache successful and empty responses using the existing Streamlit caching pattern and apply bounded network timeouts.

USGS candidates join the existing HIFLD, OpenStreetMap, and public-facility candidate pool. Deduplicate facilities using normalized type plus geographic proximity, preferring USGS records when multiple sources identify the same facility. The optimizer receives only candidates that fall within the selected jurisdiction boundary; this preserves the approved boundary-only rule.

If USGS is unavailable, existing sources continue normally. If every real-facility source fails, retain the deterministic call-density fallback but label its rows as proposed call-density sites rather than police or fire stations.

## Jurisdiction percentage design

`find_jurisdictions_by_coordinates()` already calculates `call_share` independently for every matching place and county. Preserve that value through upload onboarding and use it in sidebar labels. For nested boundaries, Raleigh and Wake County can both contain the same call, so their percentages are independent containment values and are not expected to sum to 100%.

The sidebar label will use `DISPLAY_NAME (N.N% of calls)`. When `call_share` is unavailable in an older session or fallback boundary, derive the percentage from that row's `data_count` divided by the known sampled-call denominator when available. Do not normalize overlapping boundary counts against their sum. Retain a compatibility fallback for boundary data that has neither `call_share` nor a denominator.

## Source attribution

Add USGS National Structures Dataset to station-source text in the live coverage view and generated HTML report. Keep existing OSM and HIFLD attribution.

## Error handling

- A USGS timeout, HTTP error, malformed response, or empty result must not stop station generation.
- Query only the cleaned call bounding box and enforce the selected boundary again before optimization.
- Never invent coordinates for a USGS record.
- Do not treat prisons/correctional facilities as police stations.
- Preserve all existing user-uploaded and manually pinned station behavior.

## Verification

- Unit-test USGS request parameters and response normalization for both supported FCodes.
- Unit-test graceful failure and empty-result behavior.
- Unit-test source-priority deduplication.
- Unit-test strict selected-boundary filtering.
- Unit-test nested Raleigh/Wake labels using independent `call_share` values.
- Run the focused tests, full pytest suite, Python compilation, `git diff --check`, and a read-only Raleigh CSV smoke analysis.

## Scope

No Guardian optimization objective changes, UI redesign, deployment, push, or unrelated refactoring are included.
