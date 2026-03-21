"""
app_patch.py
============
This file shows the EXACT replacement for the `with path_upload_col:` block
in your app.py.  Everything else in app.py stays identical.

Step 1: Put smart_ingest.py in the same folder as app.py
Step 2: Add this import near the top of app.py (after other imports):

    from smart_ingest import render_smart_uploader

Step 3: Replace the entire  `with path_upload_col:` block (roughly lines
        that start with `with path_upload_col:` through the `elif call_file
        or station_file:` warning) with the single call below.
"""

# ─── PASTE THIS into app.py (replaces the old `with path_upload_col:` block) ───

# with path_upload_col:
#     render_smart_uploader(
#         accent_color=accent_color,
#         text_muted=text_muted,
#         card_bg=card_bg,
#         card_border=card_border,
#     )

# ────────────────────────────────────────────────────────────────────────────────
# WHAT CHANGES vs. the old uploader
# ────────────────────────────────────────────────────────────────────────────────
#
# OLD behaviour
# ─────────────
#   • Only accepted files literally named "calls.csv" and "stations.csv"
#   • Required lat / lon columns with standard names
#   • Crashed on any other format
#   • Mandatory station file
#
# NEW behaviour (smart_ingest.py)
# ────────────────────────────────
#   • Accepts ANY filename  (cad_export.xlsx, incidents_2024.csv, CAD_Q1.txt …)
#   • Accepts ANY delimiter  (comma, tab, pipe, semicolon — auto-detected)
#   • Accepts ANY column names  — two-stage classifier:
#       Stage 1: regex heuristics  (lat, latitude, y_coord, geoy, YLAT …)
#       Stage 2: TF-IDF + Logistic Regression trained on 150-name corpus
#   • Coordinate formats supported:
#       ✓ Decimal lat/lon            (38.123, -95.456)
#       ✓ Projected X/Y – UTM       (517000, 4200000)
#       ✓ Projected X/Y – State Plane feet
#       ✓ Web Mercator              (EPSG:3857)
#       ✓ Full address strings      ("123 Main St, Orlando FL")
#       ✓ Intersections             ("Main St & Oak Ave, Orlando")
#       ✓ Block-level               ("100 Block of Main St")
#         (address → geocoded via Nominatim, ≤1 req/s, capped 5 000 rows)
#   • User can review & override the inferred mapping before processing
#   • Station file OPTIONAL:
#       – If provided: same smart detection applied
#       – If absent:  real police / fire / EMS stations fetched from OSM
#         Overpass API within the bounding box of the call data
#         (falls back to 100 synthetic random stations if OSM unavailable)
#   • Writes to session_state identically to the old block:
#       st.session_state['df_calls']            ← standard lat/lon/priority/nature/date df
#       st.session_state['df_stations']         ← standard lat/lon/name/type df
#       st.session_state['total_original_calls']
#       st.session_state['csvs_ready'] = True
#       st.session_state['active_city'] / ['active_state']  (auto-detected)
#
# ────────────────────────────────────────────────────────────────────────────────
# EXAMPLE INPUT FILES THAT NOW WORK
# ────────────────────────────────────────────────────────────────────────────────
#
# Format A — standard lat/lon (already worked):
#   lat,lon,priority
#   28.538,-81.379,High
#
# Format B — verbose column names:
#   LATITUDE,LONGITUDE,CALL_TYPE,INCIDENT_DATE
#   28.538,-81.379,BURGLARY,2024-03-15
#
# Format C — address only:
#   address,city,state,zip,priority
#   123 Main St,Orlando,FL,32801,High
#
# Format D — intersection:
#   location,priority
#   "Main St & Oak Ave, Orlando FL",Medium
#
# Format E — CAD export with state-plane feet (FL East, EPSG:2236):
#   X_SP,Y_SP,NATURE,PRIORITY
#   762345,604210,THEFT,3
#
# Format F — UTM Zone 17N:
#   UTM_E,UTM_N,Type,Date
#   517000,4200000,ROBBERY,2024-01-10
#
# Format G — Excel file with mixed columns:
#   (same detection logic applies — .xlsx supported)
#
# Format H — no station file provided:
#   (real OSM police/fire/EMS auto-fetched for the bounding box)
