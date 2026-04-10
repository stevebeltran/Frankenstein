# Modularization Checklist

## ✅ Completed

- [x] Phase 0: Delete dead code (lines 1229-1421)
- [x] Phase 1: Create `modules/config.py` 
- [x] Phase 2: Create `modules/versioning.py` + `modules/image_utils.py`
- [x] Phase 3: Create `modules/notifications.py`

## ⏳ Pending

- [ ] Phase 4: Create `modules/cad_parser.py`
  - Lines: 719-795 (_extract_file_meta), 2159-2996 (aggressive_parse_calls + nested helpers), 2986-2996 (_get_annualized_calls)
  - Imports: st, pandas, numpy, os, re, io, json, datetime, math, Path, STATE_FIPS, US_STATES_ABBR, KNOWN_POPULATIONS
  - Remove from app.py: lines starting ~719 through ~3000

- [ ] Phase 5: Create `modules/geospatial.py`
  - Lines: 78-142 (boundary overlay), 985-1103 (jurisdiction + count), 1150-1500+ (boundary select + geocoding)
  - Plus: 3230+, 3500+, 3700+, 4000+, 5300+ (many geo functions)
  - Imports: st, pandas, geopandas, numpy, shapely, pathlib, os, glob, json, re, zipfile, io, math, urllib, ThreadPoolExecutor, STATE_FIPS

- [ ] Phase 6: Create `modules/faa_rf.py`
  - Lines: 4000-4893 (FAA grid, parquet, LAANC, airfields, RF engine)
  - Imports: st, pandas, geopandas, numpy, plotly, shapely, pathlib, os, json, math, urllib, scipy

- [ ] Phase 7: Create `modules/optimization.py`
  - Lines: 5484-5698 (precompute_spatial_data, solve_mclp, compute_all_elbow_curves)
  - Imports: numpy, pandas, geopandas, shapely, heapq, ThreadPoolExecutor, pulp, st, CONFIG, build_display_calls

- [ ] Phase 8: Create `modules/html_reports.py`
  - Lines: 1253+, 1684+, 2833+, 2999+, 3166+, 4894+, 5309+, 6832+ (all HTML generation)
  - Imports: st, pandas, numpy, json, re, io, math, datetime, base64, simplekml, shapely, CONFIG, SIMULATOR_DISCLAIMER_SHORT

- [ ] Phase 9: Wrap main UI in `def main():`
  - Wrap upload page (~1100 lines) + main map interface (~4800 lines) in `def main():`
  - Call `main()` at end of app.py (unconditional for Streamlit)

## Verification

### After each phase:
```bash
cd "G:/My Drive/PRIVATE NO ACCESS/Pyton/app/Beta/Frankenstein"
streamlit run app.py
```

### Before Phase 4:
- [x] app.py imports successfully
- [ ] Run app, verify no import errors
- [ ] Try uploading a demo city to verify CAD parser still works

## Git Commands

```bash
# View commits
git log --oneline | head -10

# Check current line count
wc -l app.py modules/*.py

# Verify modules exist
ls -la modules/
```

## Notes

- No circular dependencies exist in dependency tree
- Each phase is independently testable
- Phases 4-9 can be done in any order (they don't depend on each other)
- After Phase 9, app.py should be ~600-900 lines of orchestration
