# Page Extraction Implementation Guide

## ⚠️ Important: Large Refactoring Ahead

Extracting the onboarding and simulation pages is a **high-risk, high-complexity refactoring** because:
- Involves moving 7,000+ lines of code
- Multiple interdependencies across functions
- Streamlit state management must be preserved
- Session state handling is critical

## Recommended Approach: Incremental Extraction

Instead of one large extraction, break it into smaller, testable steps:

### Step 1: Identify Dependencies

Before extracting, identify what the onboarding and simulation pages need:

```python
# Functions used by onboarding page
Functions from app.py:
- get_themed_logo_base64()
- get_transparent_product_base64()
- aggressive_parse_calls()
- _slugify()
- _build_corrected_export_from_merged
- ... (and many more)

Modules imported by pages:
- streamlit (st)
- pandas as pd
- geopandas as gpd
- plotly, folium, simplekml
- modules/* (constants, geospatial, etc.)
```

### Step 2: Safe Extraction Pattern

**Option A: Function-Based Extraction** (RECOMMENDED)
```python
# pages/onboarding.py
def render_onboarding_page(
    app_context: dict,  # Pass all needed functions via context
    session_state: dict  # Explicit session state management
) -> bool:
    """Render upload/onboarding page.
    
    Args:
        app_context: Dict with required functions from app.py
        session_state: Reference to st.session_state
        
    Returns:
        bool: Whether to continue to next page
    """
    # Code from lines 2427-4398 goes here
    # Use app_context['function_name'] for dependencies
    # Use session_state instead of st.session_state
```

**Option B: Import Everything** (SIMPLER but riskier)
```python
# pages/onboarding.py
from app import (
    get_themed_logo_base64,
    get_transparent_product_base64,
    aggressive_parse_calls,
    # ... all other dependencies
)

def render_onboarding_page() -> None:
    """Render upload/onboarding page."""
    # Code from lines 2427-4398 goes here
    # Direct function calls as normal
```

## Implementation Strategy

### Phase 2-A: Onboarding Page (1,972 lines)

#### Safest Approach:
1. **Create pages/onboarding.py** stub with function signature
2. **Copy lines 2427-4398** from app.py into the function
3. **Fix indentation** (remove 4 spaces - was inside main())
4. **Add imports** for any globals/functions used
5. **Test incrementally**:
   - Test file upload works
   - Test jurisdiction detection
   - Test data filtering
   - Test transition to simulation page
6. **Update app.py** to call `render_onboarding_page()`
7. **Remove extracted code** from app.py main()

### Phase 2-B: Simulation Page (5,300 lines)

This is more complex due to interdependencies. Options:

#### Option 1: Whole Function (RISKY)
- Move all 5,300 lines at once
- Risk: Multiple breaking changes
- Benefit: Clean separation

#### Option 2: Sub-functions (SAFER)
Break simulation into sub-functions:
```python
def render_simulation_page():
    _render_sidebar_controls()
    _render_map_and_summary()
    _render_station_suggestions()
    _render_results_panels()
    _render_export_section()
```

Then extract each sub-function individually with testing between each.

#### Option 3: Staged Migration (SAFEST)
1. Keep simulation code in app.py for now
2. Create pages/simulation.py as thin wrapper
3. Gradually move sub-functions over weeks/months
4. Test everything between each move

## Risk Mitigation Checklist

### Before Starting:
- [ ] Backup current working app.py
- [ ] Create a git branch for this refactoring
- [ ] Review all dependencies to extract
- [ ] Document current behavior with tests

### During Extraction:
- [ ] Extract small sections (< 500 lines each)
- [ ] Test after each extraction
- [ ] Verify session state still works
- [ ] Check that imports resolve correctly
- [ ] Run full test suite after each step

### After Extraction:
- [ ] Run all 117 tests
- [ ] Test full app flow (upload → analysis → export)
- [ ] Check for any import errors
- [ ] Verify no performance regression
- [ ] Code review with team

## Critical Functions to Preserve

These MUST remain accessible and working:

```python
# Session/State Management
init_session_state()
st.session_state access

# Data Handling
aggressive_parse_calls()
_build_corrected_export_from_merged()
df manipulation

# UI Components
get_themed_logo_base64()
get_transparent_product_base64()
render_sidebar_*()

# Streamlit Integration
st.file_uploader()
st.session_state
st.write() / st.markdown()
@st.cache_data decorators
```

## Testing Strategy

### Unit Tests
```bash
# After extracting onboarding:
pytest tests/test_onboarding.py -v

# After extracting simulation:
pytest tests/test_simulation.py -v
```

### Integration Tests
```bash
# Full app flow
pytest tests/test_integration.py -v
```

### Manual Testing
1. Start app
2. Upload CSV file
3. Select jurisdiction
4. Filter data
5. Generate stations
6. View coverage analysis
7. Export results
8. Verify QR report still works

## Estimated Timeline

- **Onboarding extraction**: 2-4 hours (more straightforward)
- **Simulation extraction**: 6-12 hours (complex dependencies)
- **Testing & fixes**: 3-5 hours
- **Code review**: 1-2 hours
- **Total**: 12-23 hours

## Success Criteria

✓ All 117 existing tests pass
✓ File upload → simulation flow works
✓ All export formats work (CSV, KML, HTML)
✓ QR public reports still work
✓ No functionality lost
✓ No performance regression
✓ Code is more maintainable

## If Things Break

1. **Don't panic** - revert to git branch
2. **Identify the breaking change** - which line caused it?
3. **Isolate the issue** - test just that part
4. **Fix the issue** - usually import or dependency related
5. **Add a test** - prevent future regressions
6. **Try again** - smaller chunks this time

## Next Steps

1. **Choose an approach**: Option A, B, or C above
2. **Start with onboarding**: It's simpler to extract
3. **Follow testing checklist** before and after
4. **Commit frequently** - every working state
5. **Don't try both pages at once** - do one, test, then next

## Resources

- ROUTING_REFACTORING_PLAN.md - Overall strategy
- REFACTORING_SUMMARY.md - Context of refactoring
- tests/ directory - Test examples to follow
- modules/ directory - Extracted module patterns

---

**Ready to proceed?** Start with the "Safest Approach" checklist and take it one step at a time.
