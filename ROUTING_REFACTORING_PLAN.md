# Phase 2 Part 2: Routing Layer Refactoring Plan

## Current State

**main() function**: Lines 2425-9696 (7,271 lines!)
- Monolithic routing and page rendering combined
- Two major conditional branches:
  - Upload/Onboarding page: `if not st.session_state['csvs_ready']` (lines 2427-4398)
  - Main Simulation page: `if st.session_state['csvs_ready']` (lines 4399-9696)

## Target Architecture

```
app/
├── app.py (main entry point, ~200 lines)
│   ├── Page routing logic
│   ├── Session initialization
│   └── Public report handling
├── pages/
│   ├── __init__.py
│   ├── onboarding.py (~1,800 lines)
│   │   └── render_onboarding_page()
│   └── simulation.py (~5,400 lines)
│       ├── render_simulation_page()
│       ├── render_sidebar_controls()
│       └── render_results_panels()
└── modules/ (existing)
```

## Refactoring Steps

### Phase 2-A: Onboarding Page Extraction
**Scope**: Extract upload/data import page
**Lines**: 2427-4398 (~1,972 lines)
**File**: pages/onboarding.py
**Function**: render_onboarding_page()
**Impact**: Low risk (isolated to conditional branch)
**Testing**: Verify upload flow still works

### Phase 2-B: Simulation Page Extraction  
**Scope**: Extract main analysis/results page
**Lines**: 4399-9696 (~5,300 lines)
**File**: pages/simulation.py
**Functions**:
  - render_simulation_page()
  - render_sidebar_controls()
  - render_station_suggestions()
  - render_results_export()
**Impact**: High complexity (interdependent logic)
**Testing**: Verify map display, station suggestions, export functions

### Phase 2-C: Clean Up Routing
**Scope**: Simplify main() to pure routing logic
**Result**: ~300 line main() with clean flow
**Pattern**:
```python
def main():
    _render_in_app_faq()
    
    # Route based on data state
    if not st.session_state['csvs_ready']:
        render_onboarding_page()
    else:
        render_simulation_page()
```

## Complexity Assessment

### Onboarding Page (2-A): MEDIUM
- File upload handling (CAD parsing)
- Jurisdiction selection & boundary overlay
- Sidebar controls for data filters
- Census data integration
- Single isolated section
- **Extraction risk**: LOW

### Simulation Page (2-B): HIGH  
- Map visualization with Folium
- Station optimization and placement
- Results panels (metrics, coverage, etc.)
- Export functionality (KML, CSV, reports)
- Multi-panel dashboard layout
- Many interdependent components
- **Extraction risk**: HIGH
- **Mitigation**: Extract as series of sub-functions

### Dependencies to Preserve

Functions/modules used by pages:
- `modules/station_generation.py` - Station placement
- `modules/coverage_analysis.py` - RF calculations
- `modules/geospatial.py` - Boundary operations
- `modules/dashboard_helpers.py` - UI components
- `modules/optimization.py` - Fleet optimization
- `modules/html_reports.py` - Report generation
- Various helper functions from app.py

## Implementation Strategy

### Step 1: Extract Onboarding Page
1. Create `pages/onboarding.py` with `render_onboarding_page()` function
2. Move lines 2427-4398 into the function
3. Update imports and function signatures
4. Test: File upload flow works correctly
5. Update `app.py` to call `render_onboarding_page()`

### Step 2: Extract Simulation Page (Sub-functions)
1. Create `pages/simulation.py` with structure:
   ```python
   def render_simulation_page():
       render_sidebar_controls()
       render_map_and_summary()
       render_results_panels()
       render_export_section()
   ```
2. Identify natural breakpoints in the 5,300 line section
3. Extract each sub-function separately
4. Test each sub-function before integrating

### Step 3: Cleanup app.py
1. Remove extracted page logic
2. Keep only routing, session init, auth
3. Ensure clean function signatures
4. Add type hints to new page functions

## Critical Functions to Preserve

These must be kept accessible from pages or moved carefully:

- Sidebar rendering functions
- Map building logic  
- Station optimization pipelines
- Export handlers
- Results computation
- Metrics calculation

## Testing Strategy

### Onboarding Page Tests
- [ ] File upload works
- [ ] Jurisdiction detection works
- [ ] Boundary overlay renders
- [ ] Data filtering works
- [ ] Session state updates correctly

### Simulation Page Tests
- [ ] Map displays with data
- [ ] Station suggestions generate
- [ ] Coverage metrics compute correctly
- [ ] Export formats (KML, CSV) work
- [ ] Results panels render properly

### Integration Tests
- [ ] Flow from upload to simulation works
- [ ] Page transitions smooth
- [ ] Session state persists
- [ ] No memory leaks from page switching

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Breaking dependencies | Careful extraction with import testing |
| Losing functionality | Comprehensive testing before/after |
| Session state issues | Test state transitions between pages |
| Import circular deps | pages/ modules don't import app.py |
| Large file sizes | Break simulation.py into sub-modules if >2000 lines |

## Timeline Estimate

- Phase 2-A (Onboarding): ~4-6 hours
- Phase 2-B (Simulation): ~8-12 hours (most complex)
- Phase 2-C (Cleanup): ~1-2 hours
- Testing: ~3-4 hours
- **Total**: ~16-24 hours (can be parallelized)

## Success Criteria

✓ All tests pass
✓ app.py reduced from ~9,700 to ~300 lines
✓ pages/onboarding.py extracted completely
✓ pages/simulation.py extracted with clear sub-functions
✓ No functionality lost
✓ No new bugs introduced
✓ Code is more testable and maintainable

## Next Steps

1. Start Phase 2-A: Begin onboarding page extraction
2. Create pages/ directory structure
3. Incrementally move code with testing after each step
4. Keep app.py minimal and focused on routing
