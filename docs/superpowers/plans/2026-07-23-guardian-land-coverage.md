# Automatic Guardian Land-Coverage Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an uploaded-stations workflow that automatically selects Guardian stations by maximum measurable marginal land coverage and keeps cards, map, counts, and deployments synchronized.

**Architecture:** Add a pure, deterministic greedy selector that operates on `clipped_guard` geometries and returns selected station indices plus marginal gains. Expose it through the existing dashboard helper layer, then apply its result through the established `suggestion_modes` / manual-deployment reconciliation path so station identity remains index-based and manual card choices remain authoritative after the optimizer run.

**Tech Stack:** Python, Streamlit, GeoPandas/Shapely geometry, NumPy, pytest, existing station suggestion state helpers.

## Global Constraints

- Apply only to the uploaded-stations-file workflow.
- Use `clipped_guard` for Guardian land selection; never use Responder `clipped_2m` for this objective.
- Stop when the best remaining station adds no measurable new area after geometry tolerance.
- Preserve stable station identity and card order; do not infer identity from display rank.
- Preserve manual card selections and prevent any station from being both Guardian and Responder.
- Preserve all unrelated dirty files and do not change generated `graphify-out` or `jurisdiction_data` artifacts.
- Run focused tests with `$env:PYTHONPATH='.'` from the repository root.

---

### Task 1: Add the pure Guardian marginal-area selector

**Files:**
- Modify: `modules/optimization.py` near the existing area-coverage helpers
- Test: `tests/test_guardian_land_optimization.py`

**Interfaces:**
- Produces:
  `select_guardian_land_stations(guard_geometries, city_area, min_gain_area=1e-9) -> tuple[list[int], list[float], float]`
- The returned tuple is `(selected_indices, marginal_gains, selected_area)`.
- `guard_geometries` is an ordered list whose positions are stable station indices.
- `marginal_gains` has one value per selected index and is expressed in the same projected-area units as the geometries.

- [ ] **Step 1: Write failing geometry tests**

```python
from shapely.geometry import box

from modules.optimization import select_guardian_land_stations


def test_selects_stations_by_new_guardian_land_not_responder_land():
    geometries = [
        box(0, 0, 10, 10),
        box(9, 0, 19, 10),
        box(30, 0, 31, 10),
    ]

    selected, gains, area = select_guardian_land_stations(
        geometries, city_area=1000, min_gain_area=1e-6
    )

    assert selected == [0, 1, 2]
    assert gains == [100.0, 90.0, 10.0]
    assert area == 200.0


def test_stops_when_remaining_station_adds_only_negligible_area():
    geometries = [box(0, 0, 10, 10), box(0, 0, 10, 10.0000000001)]

    selected, gains, area = select_guardian_land_stations(
        geometries, city_area=1000, min_gain_area=1e-6
    )

    assert selected == [0]
    assert gains == [100.0]
    assert area == 100.0


def test_empty_geometries_are_skipped_and_ties_use_station_index():
    geometries = [None, box(0, 0, 1, 1), box(2, 0, 3, 1)]

    selected, gains, area = select_guardian_land_stations(
        geometries, city_area=1000, min_gain_area=1e-6
    )

    assert selected == [1, 2]
    assert gains == [1.0, 1.0]
    assert area == 2.0
```

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run:

```powershell
$env:PYTHONPATH='.'
python -m pytest tests/test_guardian_land_optimization.py -q
```

Expected: collection or test failure because `select_guardian_land_stations` does not yet exist.

- [ ] **Step 3: Implement the minimal deterministic selector**

Add a helper that maintains `current_union`, evaluates every unselected geometry's union-area gain, chooses the candidate with the greatest gain, breaks equal gains by the lower station index, appends the gain, and stops when `best_gain <= min_gain_area`. Treat `None`, empty, invalid, and union/intersection exceptions as zero-gain candidates. Return the final union area, or `0.0` when no valid geometry is selected.

```python
def select_guardian_land_stations(
    guard_geometries,
    city_area,
    min_gain_area=1e-9,
):
    selected = []
    marginal_gains = []
    current_union = None
    remaining = set(range(len(guard_geometries or [])))
    tolerance = max(float(min_gain_area or 0.0), 0.0)

    while remaining:
        best_idx = None
        best_gain = -1.0
        for idx in sorted(remaining):
            geometry = guard_geometries[idx]
            if geometry is None or getattr(geometry, "is_empty", True):
                gain = 0.0
            else:
                try:
                    candidate_union = (
                        geometry if current_union is None
                        else current_union.union(geometry)
                    )
                    current_area = current_union.area if current_union is not None else 0.0
                    gain = max(float(candidate_union.area - current_area), 0.0)
                except Exception:
                    gain = 0.0
            if gain > best_gain:
                best_idx, best_gain = idx, gain

        if best_idx is None or best_gain <= tolerance:
            break
        geometry = guard_geometries[best_idx]
        current_union = geometry if current_union is None else current_union.union(geometry)
        selected.append(best_idx)
        marginal_gains.append(float(best_gain))
        remaining.remove(best_idx)

    selected_area = float(current_union.area) if current_union is not None else 0.0
    return selected, marginal_gains, selected_area
```

`city_area` is accepted for interface clarity and future percentage reporting; the selector must not use it to change the selection order. Remove the unused argument only if the existing project conventions reject unused interface parameters and update all plan references consistently.

- [ ] **Step 4: Run the focused tests and confirm they pass**

Run the same pytest command. Expected: all three tests pass.

- [ ] **Step 5: Commit the pure selector**

```powershell
git add modules/optimization.py tests/test_guardian_land_optimization.py
git commit -m "feat: add Guardian marginal land selector"
```

### Task 2: Add dashboard-layer state application and metrics

**Files:**
- Modify: `modules/dashboard_helpers.py` near `compute_station_suggestions`, `sync_station_suggestion_modes`, and `apply_manual_suggestion_deployments`
- Test: `tests/test_guardian_land_optimization.py`
- Test: `tests/test_station_suggestion_sync.py` only if an existing invariant test needs extension

**Interfaces:**
- Produces:
  `compute_guardian_land_optimization(station_metadata, city_area, min_gain_area=1e-9) -> dict`
- Return shape:
  `{'selected_indices': list[int], 'marginal_gains': dict[int, float], 'selected_area': float, 'land_pct': float}`.
- Consumes `station_metadata[i]['clipped_guard']` and preserves the metadata list index as the station identity.

- [ ] **Step 1: Write failing helper tests**

```python
from modules.dashboard_helpers import compute_guardian_land_optimization


def test_dashboard_result_uses_guardian_geometry_and_reports_percentage():
    metadata = [
        {'clipped_guard': box(0, 0, 10, 10), 'clipped_2m': box(0, 0, 1, 1)},
        {'clipped_guard': box(20, 0, 30, 10), 'clipped_2m': box(0, 0, 1, 1)},
    ]

    result = compute_guardian_land_optimization(metadata, city_area=1000)

    assert result['selected_indices'] == [0, 1]
    assert result['marginal_gains'] == {0: 100.0, 1: 100.0}
    assert result['selected_area'] == 200.0
    assert result['land_pct'] == 20.0
```

- [ ] **Step 2: Run the helper test and confirm it fails**

```powershell
$env:PYTHONPATH='.'
python -m pytest tests/test_guardian_land_optimization.py::test_dashboard_result_uses_guardian_geometry_and_reports_percentage -q
```

Expected: failure because the dashboard helper does not yet exist.

- [ ] **Step 3: Implement the dashboard helper**

Build the ordered `clipped_guard` list, call `select_guardian_land_stations`, convert the parallel result into an index-to-gain dictionary, and calculate `selected_area / city_area * 100` only when `city_area > 0`. Store no Streamlit widget state inside this pure helper.

- [ ] **Step 4: Add state-application tests before wiring the button**

Extend the synchronization tests with a case asserting that applying an automatic result sets selected indices to `Guardian`, all other currently unassigned suggestions to `Off`, and then passes through `apply_manual_suggestion_deployments` without duplicate role indices. Keep a manually assigned station in `_suggestion_manual_modes` and assert it remains the exact station identity after application.

- [ ] **Step 5: Implement state application through existing helpers**

Add a small state adapter in `dashboard_helpers.py` that:

1. Takes the optimizer result and the current suggestions.
2. Sets `session_state['suggestion_modes'][idx]` to `Guardian` for selected indices and `Off` for unselected indices that are not manual overrides.
3. Records the automatic result for display metrics.
4. Calls the existing manual deployment reconciliation after the automatic result, so manual modes remain authoritative.
5. Derives Guardian/Responder counts from the final complete mode set.

Do not add automatic selections to optimizer lock inputs, do not rename stations, and do not change widget identity keys.

- [ ] **Step 6: Run focused synchronization tests**

```powershell
$env:PYTHONPATH='.'
python -m pytest tests/test_guardian_land_optimization.py tests/test_station_suggestion_sync.py -q
```

Expected: all existing synchronization tests plus the new land-optimization tests pass.

- [ ] **Step 7: Commit the dashboard helper changes**

```powershell
git add modules/dashboard_helpers.py tests/test_guardian_land_optimization.py tests/test_station_suggestion_sync.py
git commit -m "feat: synchronize Guardian land optimization with cards"
```

### Task 3: Wire the uploaded-stations UI action

**Files:**
- Modify: `app.py` in the uploaded-station suggestion/optimization flow around `_suggestions`, `_station_suggestion_rank_by`, and the existing station deployment reconciliation
- Modify: `modules/dashboard_helpers.py` only if the render function needs a narrowly scoped action/metric parameter
- Test: `tests/test_guardian_land_optimization.py`

**Interfaces:**
- Consumes the Task 2 result shape and the existing `suggestions`, `suggestion_modes`, and deployment state.
- Produces a visible uploaded-flow action labeled `Optimize Guardian Land Coverage` and visible result metrics.

- [ ] **Step 1: Write the UI-state test for the action flag**

Add a helper-level test for a boolean/session action flag such as `_run_guardian_land_optimization`: when true, the adapter runs once, records the result, and clears the flag; when false, no automatic selection occurs. The test must assert repeated reruns do not rerun the action unless the user activates it again.

- [ ] **Step 2: Run the new test and confirm it fails**

```powershell
$env:PYTHONPATH='.'
python -m pytest tests/test_guardian_land_optimization.py -q
```

Expected: failure because the action adapter is not yet wired.

- [ ] **Step 3: Add the uploaded-flow button and result display**

Render the button only when `stations_user_uploaded` is true and station metadata is available. On click, set the session action flag and trigger the existing Streamlit rerun pattern used by the card controls. On the following run, execute the helper using `station_metadata` and the active jurisdiction area, apply the result through the state adapter, and display selected count, total land percentage, and per-station marginal gain.

Do not restore the old Guardian/Responder count sliders in this workflow. Do not sort cards by optimizer rank. Keep station card order stable and let existing card rendering show the final mode for each station.

- [ ] **Step 4: Preserve manual overrides explicitly**

Ensure the action applies automatic selections before the existing final manual reconciliation, and verify the visible copy makes clear that pressing the optimizer action replaces the automatic plan while later card changes are manual overrides.

- [ ] **Step 5: Run focused tests**

```powershell
$env:PYTHONPATH='.'
python -m pytest tests/test_guardian_land_optimization.py tests/test_station_suggestion_sync.py -q
```

Expected: all focused tests pass.

- [ ] **Step 6: Commit the UI wiring**

```powershell
git add app.py modules/dashboard_helpers.py tests/test_guardian_land_optimization.py
git commit -m "feat: add automatic Guardian land coverage action"
```

### Task 4: Validate with York County data and final regression checks

**Files:**
- Modify: none unless a test exposes a scoped defect
- Test: `tests/test_guardian_land_optimization.py`

- [ ] **Step 1: Run the complete focused regression set**

```powershell
$env:PYTHONPATH='.'
python -m pytest tests/test_guardian_land_optimization.py tests/test_station_suggestion_sync.py tests/test_onboarding_station_uploads.py -q
```

Expected: all tests pass with no collection errors.

- [ ] **Step 2: Start an isolated local Streamlit smoke server**

Use a temporary port such as 8502 and local auth bypass only for the smoke test. Do not reuse or terminate an unrelated existing Streamlit process. Use the existing project startup convention and avoid `$PID` as a PowerShell variable name.

- [ ] **Step 3: Exercise the uploaded York County workflow**

Load:

```text
G:\My Drive\PRIVATE NO ACCESS\Python\York County NC\calls2.csv
G:\My Drive\PRIVATE NO ACCESS\Python\York County NC\stations.csv
```

Click `Optimize Guardian Land Coverage` and verify:

- the selected Guardian count is automatically determined;
- every selected card shows `Guardian`;
- unselected cards remain `Off` unless manually changed;
- the displayed land coverage equals the union of selected Guardian rings;
- map rings and markers correspond to the same station names/indices;
- no station appears as both Guardian and Responder;
- a rerun preserves selected identities and card order;
- manually toggling one additional station deploys that exact station.

- [ ] **Step 4: Capture final repository state**

```powershell
git status --short
git diff --check
git log -5 --oneline
```

Confirm that unrelated pre-existing dirty files remain untouched and report the exact implementation files changed.

- [ ] **Step 5: Run verification before completion**

Run the focused tests again after the smoke test. Do not claim completion unless the tests and live state checks pass.
