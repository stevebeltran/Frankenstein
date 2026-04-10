# Completing Phases 5-9

You are at **Phase 4 completion**. This document provides exact instructions for Phases 5-9.

## Current Status
- ✅ Phases 0-4 complete
- ⏳ Phases 5-9 remaining
- app.py: 11,395 lines → target: 600-900 lines after Phase 9
- Modules created: 6 (config, versioning, image_utils, notifications, cad_parser, __init__)

---

## Phase 5: modules/geospatial.py

Extract boundary, geocoding, and station location functions.

### Functions to extract (from app.py):
- Lines 759-779: `_count_points_within_boundary`
- Lines 781-1102: `find_jurisdictions_by_coordinates`
- Lines 78-142: `_load_uploaded_boundary_overlay` + `_boundary_overlay_status`
- Lines 1150-1500+: boundary select, geocoding, jurisdiction helpers
- Plus geospatial/station functions scattered throughout

**Easier approach:** Create stub module, then move functions

```bash
cat > modules/geospatial.py << 'EOFILE'
"""Geospatial utilities - boundaries, geocoding, station generation."""
import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from pathlib import Path
import os, glob, json, re, zipfile, io, math, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

from modules.config import STATE_FIPS, US_STATES_ABBR, KNOWN_POPULATIONS

# [PASTE extracted functions here]
EOFILE
```

Then in app.py, add the import and remove the functions.

---

## Phase 6: modules/faa_rf.py

Extract FAA, airspace, and RF coverage functions.

```bash
# Extract lines 4000-4893 for FAA/RF functions
sed -n '4000,4893p' app.py
```

Create `modules/faa_rf.py` with imports:
```python
import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
import plotly.graph_objects as go
from shapely.geometry import box
import os, json, math, urllib.request
from modules.config import FAA_CEILING_COLORS, FAA_DEFAULT_COLOR, STATION_COLORS
```

---

## Phase 7: modules/optimization.py

Extract optimization solver and elbow curve functions.

```bash
sed -n '5484,5698p' app.py  # Find exact range in current app.py
```

Create `modules/optimization.py`:
```python
import numpy as np
import pandas as pd
import geopandas as gpd
import heapq
from concurrent.futures import ThreadPoolExecutor
import pulp
import streamlit as st
from modules.config import CONFIG
from modules.geospatial import build_display_calls
```

---

## Phase 8: modules/html_reports.py

Extract all HTML generation and report functions (~1400 lines).

Functions to extract:
- `_detect_datetime_series_for_labels`
- `estimate_high_activity_overtime`
- `estimate_specialty_response_savings`
- `build_high_activity_staffing_html`
- `generate_command_center_html`
- `_build_cad_charts_html`, `_build_apprehension_table`, `_build_cad_charts`
- `format_3_lines`, `_build_unit_cards_html`
- `to_kml_color`, `generate_kml`
- `generate_community_impact_dashboard_html`

Create `modules/html_reports.py` with all imports.

---

## Phase 9: Wrap Main UI in `def main()`

**After extracting Phases 5-8**, the remaining code in app.py is:
1. Top-level imports
2. Module imports
3. Mobile route (lines ~158-341)
4. Page config (line ~344)
5. OAuth gate (lines ~347-523)
6. CSS injection
7. Session state init
8. Upload page (if not csvs_ready block)
9. Main map interface (if csvs_ready block)

**Wrap items 8-9 in a function:**

```python
def main():
    if not st.session_state['csvs_ready']:
        # [Upload page code ~1100 lines]
        ...
    else:
        # [Main map interface code ~4800 lines]
        ...

# Call at end of file (unconditional for Streamlit)
main()
```

---

## Quick Verification

After each phase:
```bash
python3 -m py_compile app.py  # Check syntax
streamlit run app.py           # Try loading
```

---

## Git Workflow

After each phase:
```bash
git add modules/[name].py app.py
git commit -m "Phase [N]: Extract [name]"
```

---

## Expected Final State

After Phase 9:
- app.py: ~700 lines (orchestration only)
- 9 module files in `modules/`
- All functions extracted
- Zero circular dependencies
- Full functionality preserved

