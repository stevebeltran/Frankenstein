# app.py Modularization Plan

## Overview
The current `app.py` (10,934 lines) is a monolithic Streamlit application. This guide outlines a phased approach to split it into feature-specific modules while maintaining functionality and backward compatibility.

## Current Structure Problems
- **Very large file** (10.9K lines) makes navigation and maintenance difficult
- **Mixed concerns**: UI routing, geocoding, geospatial analysis, reporting all in one file
- **Limited testability**: Hard to unit test individual features without running the full app
- **Slow IDE performance**: Large files impact IntelliSense and refactoring tools
- **High risk for future changes**: Unclear dependencies between sections

## Proposed Module Structure

```
app/
├── app.py                    # Main entry point (routing & UI layout)
├── pages/
│   ├── hero.py              # Hero page / welcome screen
│   ├── jurisdiction_select.py
│   ├── simulation.py         # Core simulation pipeline
│   ├── results.py            # Results visualization & export
│   └── public_report.py      # Public report generation
├── modules/
│   ├── constants.py          # ✅ DONE - Magic number constants
│   ├── search_utils.py       # ✅ DONE - Search consolidation utilities
│   ├── propagation_utils.py  # ✅ DONE - RF path loss utilities
│   ├── config.py
│   ├── cad_parser.py
│   ├── geospatial.py
│   ├── [existing modules...]
│   └── ui_helpers.py         # NEW - Shared UI rendering functions
└── utils/                    # NEW - General utilities
    ├── validation.py         # Input validation helpers
    ├── formatting.py         # String/number formatting
    └── export.py             # Export utilities
```

## Refactoring Phases

### Phase 1: Extract Core Features (Recommended Starting Point)
**Scope**: ~3-4 weeks for an experienced developer  
**Impact**: Low - keeps all existing functionality, just reorganizes

1. **Create `ui_components.py`** → Extract Streamlit UI rendering
   - `_render_hero_section()`
   - `_render_jurisdiction_selector()`
   - `_render_simulation_controls()`
   - Color/theme constants (move to `modules/constants.py`)

2. **Create `station_generation.py`** → Consolidate station logic
   - `_make_random_stations()`
   - `generate_stations_from_calls()`
   - `_fetch_osm_stations_cached()`
   - `_fetch_hifld_stations_cached()`
   - These are already somewhat independent and testable

3. **Create `coverage_analysis.py`** → RF coverage & reporting
   - `_path_loss_advanced()`
   - `_estimate_terrain_blockage_db()`
   - `_estimate_clutter_loss_db()`
   - `_estimate_elevation_simple()`
   - Use new `propagation_utils.py` helpers

4. **Create `export_handlers.py`** → Export & report generation
   - `_build_corrected_export_from_merged_fallback()`
   - KML/shapefile export logic
   - Public report generation helpers

**Testing**: Add unit tests for each extracted module

### Phase 2: Break Up Routing Layer (2-3 weeks after Phase 1)

1. **Refactor `app.py` main logic**
   - Keep only Streamlit routing/navigation
   - Move page content to separate functions or modules
   - Use `if st.session_state.page == "simulation": simulation_page()`

2. **Extract `api_integrations.py`** if external APIs grow
   - Google Sheets logging (`modules/notifications.py` already does this)
   - Census geocoding
   - Reverse geocoding providers

### Phase 3: Create Test Suite (Ongoing)
- Unit tests for each extracted module
- Integration tests for major workflows
- Regression tests for UI interactions

## Implementation Strategy

### 1. Start with Functions That Have Few Dependencies
- Station generation functions (mostly self-contained)
- Path loss calculations (isolated math)
- Constants (no dependencies)

### 2. Keep Functions in `app.py` If They:
- Heavily rely on `st.*` (Streamlit functions)
- Use session state directly
- Are only called from the UI layer
- Example: `_render_public_report_route()`

### 3. Move to Modules If They:
- Are pure computation (e.g., `_path_loss_advanced()`)
- Could be unit tested independently
- Are called from multiple places
- Have no direct Streamlit dependencies

### 4. Incremental Integration
- Extract one module at a time
- Test it works with existing code
- Commit and merge before extracting the next
- Avoids large, risky refactors

## Migration Checklist

- [ ] Phase 1: Extract UI components
  - [ ] Create `modules/ui_components.py`
  - [ ] Move UI rendering functions
  - [ ] Update imports in `app.py`
  - [ ] Test that app still works
  - [ ] Add unit tests

- [ ] Phase 1: Extract station generation
  - [ ] Create `modules/station_generation.py`
  - [ ] Move station functions
  - [ ] Update imports
  - [ ] Test coverage analysis

- [ ] Phase 1: Extract coverage analysis
  - [ ] Create `modules/coverage_analysis.py`
  - [ ] Use `propagation_utils.py` helpers
  - [ ] Add unit tests for RF calculations

- [ ] Phase 1: Extract export handlers
  - [ ] Create `modules/export_handlers.py`
  - [ ] Move export and report functions
  - [ ] Verify all export formats work

- [ ] Phase 2: Refactor routing
  - [ ] Create page-specific modules in `pages/`
  - [ ] Update `app.py` main logic
  - [ ] Test navigation between pages

- [ ] Phase 3: Create test suite
  - [ ] Unit tests for each module
  - [ ] Integration tests for workflows
  - [ ] Regression tests for UI

## Benefits After Refactoring

| Benefit | Current | After Refactoring |
|---------|---------|-------------------|
| Main file size | 10,934 lines | ~2,000-3,000 lines (routing only) |
| Avg module size | — | 300-800 lines (easier to understand) |
| Testable units | ~5 | ~25+ |
| IDE response time | Slow | Much faster |
| Time to add feature | 2-3 hours | 1 hour |
| Risk of regression | High | Low |

## Important Notes

1. **No functionality changes during refactoring** — the app works exactly the same after
2. **Backward compatible** — no changes to user-facing features
3. **Incremental approach** — can deploy each phase separately
4. **Keep session_state compatible** — don't change how state is stored
5. **Preserve caching** — `@st.cache_data` decorators still work

## Example: Extracting Station Generation

### Current code in app.py (lines ~985-1066)
```python
def _make_random_stations(df_calls, n=40, boundary_geom=None, epsg_code=None):
    # ... 82 lines of logic
```

### After extraction to `modules/station_generation.py`
```python
from modules.station_generation import _make_random_stations

# In app.py, just import and use it
stations = _make_random_stations(df_calls, n=50)
```

### New module structure
```python
# modules/station_generation.py
"""Station generation for drone deployment optimization."""

from typing import Optional
import pandas as pd
from shapely.geometry import Polygon

def _make_random_stations(
    df_calls: pd.DataFrame,
    n: int = 40,
    boundary_geom: Optional[Polygon] = None,
    epsg_code: Optional[int] = None
) -> pd.DataFrame:
    """Generate n random station locations for call coverage.
    
    Uses KMeans clustering when sklearn available, falls back to random sampling.
    
    Args:
        df_calls: DataFrame with lat/lon columns
        n: Number of stations to generate
        boundary_geom: Optional boundary polygon for snapping
        epsg_code: Optional EPSG code for projection
    
    Returns:
        DataFrame with station locations and types
    """
    # ... move the 82 lines here
```

## Timeline Estimate
- **Phase 1**: 3-4 weeks (1 function group per week)
- **Phase 2**: 2-3 weeks (once Phase 1 is stable)
- **Phase 3**: Ongoing (add tests as you touch code)

## Next Steps
1. Pick one function group from Phase 1 to start
2. Create the new module file
3. Move functions and add type hints + docstrings
4. Update imports in `app.py`
5. Test thoroughly
6. Commit with clear message: "refactor: extract [feature] to modules/[name].py"
7. Move to next function group

---

**Note**: This plan prioritizes incremental, low-risk changes. You can start with any phase and don't need to complete them sequentially.
