# Station Placement Card Sort Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give uploaded-station-file users a front-and-center way to sort "Suggested Station Placements" cards by Calls% or Land%, per fleet role, fixing the current bug where Guardian land% never actually drives sort order.

**Architecture:** Add a pure, testable sort function (`sort_uploaded_station_suggestions`) to `modules/dashboard_helpers.py` that orders cards descending by whichever metric (Calls/Land) matches each card's own currently-assigned role (Guardian/Responder/Off). Wire it into `render_station_suggestions_grid` behind two new front-and-center radios, shown only when a stations file is uploaded. Hide the now-redundant sidebar "Guardian Objective"/"Responder Objective" radios in that same mode — they keep writing the exact same session-state keys (`guard_strat_idx`, `resp_strat_idx`) so the optimizer call in `app.py` (`guard_strategy`, `resp_strategy`) is untouched.

**Tech Stack:** Python, Streamlit, pytest.

## Global Constraints

- Preserve existing local work; do not overwrite, remove, or revert unrelated user changes.
- Keep edits limited to the minimum file set required: `modules/dashboard_helpers.py`, `app.py`, `tests/test_station_suggestion_sync.py`.
- Small diffs, no unrelated refactors of shared code.
- No-upload flow (sliders + sidebar objective radios + top-10 marginal-gain suggestion list) must be functionally unchanged.
- List files changed at the end; state plainly if any validation step was not run.

---

### Task 1: Pure sort helper + unit tests

**Files:**
- Modify: `modules/dashboard_helpers.py` (insert new functions between line 2201 and line 2204, i.e. right after `station_suggestion_marginal_label` and before `deployed_station_indices`)
- Modify: `tests/test_station_suggestion_sync.py` (append tests, add import)

**Interfaces:**
- Produces: `sort_uploaded_station_suggestions(suggestions, modes, guard_rank_by='call', resp_rank_by='call') -> list[dict]` — used by Task 2. Returns a **new** list of shallow-copied suggestion dicts, sorted descending, each with `rank` renumbered starting at 1. Does not mutate its inputs.
- Consumes: suggestion dicts as produced by `compute_station_suggestions` (`modules/dashboard_helpers.py:2047`), which always include the keys `station_idx`, `call_pct`, `call_pct_responder`, `call_pct_guardian`, `land_pct`, `land_pct_responder`, `land_pct_guardian`, `marginal_calls`. `modes` is a `{station_idx: 'Guardian'|'Responder'|'Off'}` dict as produced by `sync_station_suggestion_modes`.

- [ ] **Step 1: Write the failing tests**

Add this import to the top of `tests/test_station_suggestion_sync.py` (alongside the existing `from modules.dashboard_helpers import (...)` block, keep it alphabetically placed with the rest):

```python
from modules.dashboard_helpers import (
    _suggestion_widget_key,
    apply_suggestion_widget_overrides,
    apply_manual_suggestion_deployments,
    deployed_station_indices,
    reconcile_suggestion_modes_from_deployments,
    reconcile_unique_deployment_indices,
    sort_uploaded_station_suggestions,
    sync_station_suggestion_modes,
)
```

Append this to the end of the file:

```python
def _upload_suggestion(idx, call_r, call_g, land_r, land_g, marginal=0):
    return {
        "station_idx": idx,
        "rank": idx + 1,
        "role": "Responder",
        "name": f"Station {idx}",
        "call_pct": call_r,
        "call_pct_responder": call_r,
        "call_pct_guardian": call_g,
        "land_pct": land_r,
        "land_pct_responder": land_r,
        "land_pct_guardian": land_g,
        "marginal_calls": marginal,
    }


def test_sort_uploaded_orders_guardian_cards_by_guardian_land_pct():
    suggestions = [
        _upload_suggestion(0, call_r=10, call_g=10, land_r=50, land_g=5),
        _upload_suggestion(1, call_r=10, call_g=10, land_r=5, land_g=40),
        _upload_suggestion(2, call_r=10, call_g=10, land_r=30, land_g=60),
    ]
    modes = {0: "Guardian", 1: "Guardian", 2: "Guardian"}

    ordered = sort_uploaded_station_suggestions(
        suggestions, modes, guard_rank_by="land", resp_rank_by="call"
    )

    assert [s["station_idx"] for s in ordered] == [2, 1, 0]
    assert [s["rank"] for s in ordered] == [1, 2, 3]


def test_sort_uploaded_orders_responder_cards_by_responder_land_pct():
    suggestions = [
        _upload_suggestion(0, call_r=10, call_g=10, land_r=50, land_g=5),
        _upload_suggestion(1, call_r=10, call_g=10, land_r=5, land_g=40),
        _upload_suggestion(2, call_r=10, call_g=10, land_r=30, land_g=60),
    ]
    modes = {0: "Responder", 1: "Responder", 2: "Responder"}

    ordered = sort_uploaded_station_suggestions(
        suggestions, modes, guard_rank_by="call", resp_rank_by="land"
    )

    assert [s["station_idx"] for s in ordered] == [0, 2, 1]


def test_sort_uploaded_uses_each_cards_own_assigned_role():
    suggestions = [
        _upload_suggestion(0, call_r=10, call_g=10, land_r=90, land_g=10),
        _upload_suggestion(1, call_r=10, call_g=10, land_r=10, land_g=90),
    ]
    modes = {0: "Responder", 1: "Guardian"}

    ordered = sort_uploaded_station_suggestions(
        suggestions, modes, guard_rank_by="land", resp_rank_by="land"
    )

    assert [s["station_idx"] for s in ordered] == [0, 1]
    assert ordered[0]["land_pct_responder"] == 90
    assert ordered[1]["land_pct_guardian"] == 90


def test_sort_uploaded_off_cards_fall_back_to_responder_metric():
    suggestions = [
        _upload_suggestion(0, call_r=10, call_g=10, land_r=20, land_g=99),
        _upload_suggestion(1, call_r=10, call_g=10, land_r=80, land_g=1),
    ]
    modes = {0: "Off", 1: "Off"}

    ordered = sort_uploaded_station_suggestions(
        suggestions, modes, guard_rank_by="land", resp_rank_by="land"
    )

    assert [s["station_idx"] for s in ordered] == [1, 0]


def test_sort_uploaded_defaults_unknown_rank_by_to_call():
    suggestions = [
        _upload_suggestion(0, call_r=5, call_g=5, land_r=99, land_g=99),
        _upload_suggestion(1, call_r=50, call_g=50, land_r=1, land_g=1),
    ]
    modes = {0: "Responder", 1: "Responder"}

    ordered = sort_uploaded_station_suggestions(
        suggestions, modes, guard_rank_by="bogus", resp_rank_by="bogus"
    )

    assert [s["station_idx"] for s in ordered] == [1, 0]


def test_sort_uploaded_does_not_mutate_input_list():
    suggestions = [_upload_suggestion(0, 10, 10, 10, 10)]
    original_rank = suggestions[0]["rank"]

    sort_uploaded_station_suggestions(suggestions, {0: "Responder"}, resp_rank_by="land")

    assert suggestions[0]["rank"] == original_rank
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_station_suggestion_sync.py -v`
Expected: `ImportError: cannot import name 'sort_uploaded_station_suggestions'` (or collection error) — the function doesn't exist yet.

- [ ] **Step 3: Implement the helper**

In `modules/dashboard_helpers.py`, find this exact block (currently lines 2194-2204):

```python
def station_suggestion_marginal_label(suggestion):
    """Return this station's added (non-overlapping) coverage vs. the picks ranked above it."""
    metric = suggestion.get('marginal_metric')
    pct = suggestion.get('marginal_pct')
    if not metric or pct is None:
        return ''
    unit = 'land' if metric == 'land' else 'calls'
    return f"+{pct}% new {unit}"


def deployed_station_indices(active_drones):
```

Replace it with (inserting the new functions between the two existing ones):

```python
def station_suggestion_marginal_label(suggestion):
    """Return this station's added (non-overlapping) coverage vs. the picks ranked above it."""
    metric = suggestion.get('marginal_metric')
    pct = suggestion.get('marginal_pct')
    if not metric or pct is None:
        return ''
    unit = 'land' if metric == 'land' else 'calls'
    return f"+{pct}% new {unit}"


def _upload_suggestion_sort_key(suggestion, mode, guard_rank_by, resp_rank_by):
    """Sort key: each card ranks by whichever metric matches its OWN assigned role."""
    if mode == 'Guardian':
        primary = suggestion.get('land_pct_guardian', 0) if guard_rank_by == 'land' else suggestion.get('call_pct_guardian', 0)
    else:
        primary = suggestion.get('land_pct_responder', 0) if resp_rank_by == 'land' else suggestion.get('call_pct_responder', 0)
    return (
        float(primary or 0),
        float(suggestion.get('call_pct', 0) or 0),
        float(suggestion.get('land_pct', 0) or 0),
        float(suggestion.get('marginal_calls', 0) or 0),
        -int(suggestion.get('station_idx', 0) or 0),
    )


def sort_uploaded_station_suggestions(suggestions, modes, guard_rank_by='call', resp_rank_by='call'):
    """Sort uploaded-station suggestion cards highest-to-lowest by each card's own role metric.

    Unlike the auto-detected-pool marginal-gain ranking used by compute_station_suggestions,
    this is a plain descending sort: uploaded mode already shows every candidate station, so
    there is no overlap-aware subset to pick, just a display order.
    """
    guard_rank_by = 'land' if str(guard_rank_by).strip().lower() == 'land' else 'call'
    resp_rank_by = 'land' if str(resp_rank_by).strip().lower() == 'land' else 'call'
    modes = modes or {}
    ordered = sorted(
        suggestions,
        key=lambda s: _upload_suggestion_sort_key(
            s, modes.get(s.get('station_idx'), 'Off'), guard_rank_by, resp_rank_by
        ),
        reverse=True,
    )
    return [{**s, 'rank': i + 1} for i, s in enumerate(ordered)]


def deployed_station_indices(active_drones):
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_station_suggestion_sync.py -v`
Expected: all tests pass (16 previous + 6 new = 22 passed).

- [ ] **Step 5: Commit**

```bash
git add modules/dashboard_helpers.py tests/test_station_suggestion_sync.py
git commit -m "feat: add role-aware descending sort for uploaded station suggestions"
```

---

### Task 2: Front-and-center sort radios wired into the card grid

**Files:**
- Modify: `modules/dashboard_helpers.py` (`render_station_suggestions_grid`, currently lines 2852-3032)
- Modify: `app.py` (call site, currently lines 9101-9107)

**Interfaces:**
- Consumes: `sort_uploaded_station_suggestions` from Task 1 (exact signature above).
- Produces: `render_station_suggestions_grid(..., stations_uploaded=False)` — new keyword param. No other callers exist besides `app.py:9101`, confirmed via `grep -rn "render_station_suggestions_grid" .`.

- [ ] **Step 1: Add the `stations_uploaded` parameter**

In `modules/dashboard_helpers.py`, find:

```python
def render_station_suggestions_grid(st, session_state, suggestions, text_main, text_muted,
                                    card_bg, card_border, accent_color, source_label='public data',
                                    k_guardian=None, k_responder=None, suggestion_color_map=None):
```

Replace with:

```python
def render_station_suggestions_grid(st, session_state, suggestions, text_main, text_muted,
                                    card_bg, card_border, accent_color, source_label='public data',
                                    k_guardian=None, k_responder=None, suggestion_color_map=None,
                                    stations_uploaded=False):
```

- [ ] **Step 2: Insert the sort radios and re-sort call**

In the same function, find this exact block (currently lines 2906-2908):

```python
    st.caption('Click a card to compare role assignment. These suggestions are advisory only and do not force the deployment objective or lock the optimizer.')

    st.markdown(
```

Replace with:

```python
    st.caption('Click a card to compare role assignment. These suggestions are advisory only and do not force the deployment objective or lock the optimizer.')

    if stations_uploaded:
        _sort_cols = st.columns(2)
        with _sort_cols[0]:
            _guard_sort_raw = st.radio(
                'Guardian Sort',
                ('Calls', 'Land'),
                index=0 if session_state.get('guard_strat_idx', 1) == 0 else 1,
                horizontal=True,
                key='_guard_sort_radio',
                help='Sort Guardian-assigned cards by Call Coverage or Land Coverage.',
            )
        with _sort_cols[1]:
            _resp_sort_raw = st.radio(
                'Responder Sort',
                ('Calls', 'Land'),
                index=0 if session_state.get('resp_strat_idx', 1) == 0 else 1,
                horizontal=True,
                key='_resp_sort_radio',
                help='Sort Responder-assigned cards by Call Coverage or Land Coverage.',
            )
        session_state['guard_strat_idx'] = 0 if _guard_sort_raw == 'Calls' else 1
        session_state['resp_strat_idx'] = 0 if _resp_sort_raw == 'Calls' else 1
        suggestions = sort_uploaded_station_suggestions(
            suggestions,
            modes,
            guard_rank_by='land' if _guard_sort_raw == 'Land' else 'call',
            resp_rank_by='land' if _resp_sort_raw == 'Land' else 'call',
        )

    st.markdown(
```

Note: `modes` is already computed above this point in the function (via `sync_station_suggestion_modes`, existing line ~2888) — this reuses it, no new computation needed. The `for row_start in range(0, len(suggestions), 5):` loop further down already reads the local `suggestions` variable, so reassigning it here reorders what the loop renders.

- [ ] **Step 3: Pass `stations_uploaded` from the call site**

In `app.py`, find:

```python
            _sug_changed = render_station_suggestions_grid(
                st, st.session_state, _suggestions,
                text_main, text_muted, card_bg, card_border, accent_color,
                k_guardian=k_guardian,
                k_responder=k_responder,
                suggestion_color_map=_suggestion_color_map,
            )
```

Replace with:

```python
            _sug_changed = render_station_suggestions_grid(
                st, st.session_state, _suggestions,
                text_main, text_muted, card_bg, card_border, accent_color,
                k_guardian=k_guardian,
                k_responder=k_responder,
                suggestion_color_map=_suggestion_color_map,
                stations_uploaded=st.session_state.get('stations_user_uploaded', False),
            )
```

- [ ] **Step 4: Manual verification (no automated UI test harness exists in this repo)**

Run: `streamlit run app.py`

1. Without uploading a stations file: confirm the suggestion card grid renders exactly as before (no new radios visible), top-10 advisory cards, unchanged.
2. Upload a stations file with at least 6-8 stations covering a range of call/land percentages.
3. Confirm two new radios, "Guardian Sort" and "Responder Sort" (each Calls/Land), appear directly under the caption, above the card grid.
4. Assign several cards to Guardian via the per-card radio, several to Responder.
5. Toggle "Guardian Sort" to Land. Confirm Guardian-assigned cards' `G%` land value (in the "Land R x% / G y%" line) descends from top-left to bottom-right among Guardian cards.
6. Toggle "Responder Sort" to Land independently. Confirm Responder-assigned cards' `R%` land value descends, and this did not change the Guardian cards' relative order.
7. Flip one card's role from Responder to Guardian. Confirm it re-sorts into position under the current Guardian Sort setting on the next rerun.

- [ ] **Step 5: Commit**

```bash
git add modules/dashboard_helpers.py app.py
git commit -m "feat: add front-and-center Guardian/Responder sort radios for uploaded station cards"
```

---

### Task 3: Hide sidebar Objective radios when a stations file is uploaded

**Files:**
- Modify: `modules/dashboard_helpers.py` (`render_deployment_strategy`, currently lines 699-727)

**Interfaces:**
- Consumes: nothing new — `session_state` is already a parameter of `render_deployment_strategy` (`modules/dashboard_helpers.py:607`).
- Produces: no interface change — `guard_strategy_raw`, `resp_strategy_raw`, `guard_strategy`, `resp_strategy` are still set and still returned in the function's dict (`modules/dashboard_helpers.py:742-758`), unchanged in shape and meaning.

- [ ] **Step 1: Wrap both radios**

In `modules/dashboard_helpers.py`, find this exact block (currently lines 699-727):

```python
        st.markdown(
            f"<div style='font-size:0.7rem; color:{text_muted}; margin:10px 0 4px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;'>Guardian Objective</div>",
            unsafe_allow_html=True,
        )
        guard_strategy_raw = st.radio(
            'Guardian Objective',
            ('Call Coverage', 'Land Coverage'),
            index=session_state.get('guard_strat_idx', 1),
            horizontal=True,
            label_visibility='collapsed',
            help='What the Guardian optimizer maximises. Land Coverage = wide area patrol. Call Coverage = respond to highest-volume locations.',
        )
        session_state['guard_strat_idx'] = 0 if guard_strategy_raw == 'Call Coverage' else 1
        guard_strategy = 'Maximize Call Coverage' if guard_strategy_raw == 'Call Coverage' else 'Maximize Land Coverage'

        st.markdown(
            f"<div style='font-size:0.7rem; color:{text_muted}; margin:10px 0 4px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;'>Responder Objective</div>",
            unsafe_allow_html=True,
        )
        resp_strategy_raw = st.radio(
            'Responder Objective',
            ('Call Coverage', 'Land Coverage'),
            index=session_state.get('resp_strat_idx', 1),
            horizontal=True,
            label_visibility='collapsed',
            help='What the Responder optimizer maximises. Call Coverage = densest incident areas. Land Coverage = broadest geographic reach.',
        )
        session_state['resp_strat_idx'] = 0 if resp_strategy_raw == 'Call Coverage' else 1
        resp_strategy = 'Maximize Call Coverage' if resp_strategy_raw == 'Call Coverage' else 'Maximize Land Coverage'
```

Replace with:

```python
        _stations_uploaded_for_objective = bool(session_state.get('stations_user_uploaded', False))

        if not _stations_uploaded_for_objective:
            st.markdown(
                f"<div style='font-size:0.7rem; color:{text_muted}; margin:10px 0 4px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;'>Guardian Objective</div>",
                unsafe_allow_html=True,
            )
            guard_strategy_raw = st.radio(
                'Guardian Objective',
                ('Call Coverage', 'Land Coverage'),
                index=session_state.get('guard_strat_idx', 1),
                horizontal=True,
                label_visibility='collapsed',
                help='What the Guardian optimizer maximises. Land Coverage = wide area patrol. Call Coverage = respond to highest-volume locations.',
            )
            session_state['guard_strat_idx'] = 0 if guard_strategy_raw == 'Call Coverage' else 1
        else:
            guard_strategy_raw = 'Call Coverage' if session_state.get('guard_strat_idx', 1) == 0 else 'Land Coverage'
        guard_strategy = 'Maximize Call Coverage' if guard_strategy_raw == 'Call Coverage' else 'Maximize Land Coverage'

        if not _stations_uploaded_for_objective:
            st.markdown(
                f"<div style='font-size:0.7rem; color:{text_muted}; margin:10px 0 4px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;'>Responder Objective</div>",
                unsafe_allow_html=True,
            )
            resp_strategy_raw = st.radio(
                'Responder Objective',
                ('Call Coverage', 'Land Coverage'),
                index=session_state.get('resp_strat_idx', 1),
                horizontal=True,
                label_visibility='collapsed',
                help='What the Responder optimizer maximises. Call Coverage = densest incident areas. Land Coverage = broadest geographic reach.',
            )
            session_state['resp_strat_idx'] = 0 if resp_strategy_raw == 'Call Coverage' else 1
        else:
            resp_strategy_raw = 'Call Coverage' if session_state.get('resp_strat_idx', 1) == 0 else 'Land Coverage'
        resp_strategy = 'Maximize Call Coverage' if resp_strategy_raw == 'Call Coverage' else 'Maximize Land Coverage'
```

- [ ] **Step 2: Manual verification**

Run: `streamlit run app.py`

1. Without a stations file uploaded: confirm "Guardian Objective" and "Responder Objective" radios still appear in the sidebar, behave exactly as before.
2. Upload a stations file: confirm both sidebar radios disappear. Confirm the Responder/Guardian Count sliders remain disabled (pre-existing behavior, `modules/dashboard_helpers.py:1071-1072`, not touched by this task).
3. With a file uploaded, set Guardian Sort=Land and Responder Sort=Calls via the new front-and-center radios (Task 2), then remove the uploaded file (reset). Confirm the sidebar Objective radios reappear and read back a sane default (they read `guard_strat_idx`/`resp_strat_idx`, shared with the front-end radios, so whatever was last set carries over — this is expected, not a bug).

- [ ] **Step 3: Commit**

```bash
git add modules/dashboard_helpers.py
git commit -m "fix: hide sidebar objective radios when a stations file is uploaded"
```

---

### Task 4: Full regression pass

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest tests/ -v`
Expected: all tests pass, including the 6 new tests from Task 1.

- [ ] **Step 2: Manual end-to-end pass**

Run: `streamlit run app.py`

1. No-upload flow: pick a city, adjust Responder/Guardian Count sliders, toggle sidebar Call/Land objective radios, confirm the auto-optimizer still places drones and the top-10 advisory card grid behaves as before.
2. Upload flow: upload a stations file, confirm all uploaded stations appear as cards, assign roles per-card, use the new Guardian Sort / Responder Sort radios, confirm cards order correctly per role and metric as verified in Task 2 Step 4.

- [ ] **Step 3: List files changed**

```bash
git diff --stat main
```

Confirm only: `modules/dashboard_helpers.py`, `app.py`, `tests/test_station_suggestion_sync.py`, plus the two docs files already committed during brainstorming (spec + this plan).
