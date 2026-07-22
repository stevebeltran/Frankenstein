# Station Placement Card Sort — Design

## Problem

When a stations file is uploaded, "Suggested Station Placements" shows every
uploaded station as a card. Each card can be individually assigned Guardian /
Responder / Off via a per-card radio. Users need to sort these cards by
Calls% or Land% to find their best candidates, and today:

1. The only sort control is the "Responder Objective" radio, buried in the
   sidebar, and mislabeled — it doesn't obviously apply to card sorting.
2. It only reads `resp_strategy_raw`. There is a separate, independent
   "Guardian Objective" radio that is never consulted for card order at all.
3. Card order comes from a greedy marginal-gain (overlap-aware) selection
   algorithm designed for auto-picking a top-10 subset from an unbounded
   candidate pool (the no-upload flow). In the upload flow, ALL stations are
   already shown — there is no subset to pick — so this algorithm produces a
   non-monotonic order instead of a plain highest→lowest list, and it never
   used Guardian-specific geometry (`guard_matrix` / `clipped_guard`) even
   though it's passed in. Guardian land% on screen is a different geometry
   than whatever drove the order, so it looks unsorted.

Root cause confirmed in `modules/dashboard_helpers.py` `compute_station_suggestions`
(dead `guard_matrix` param) and `app.py:7380` (`_station_rank_by` sourced only
from `resp_strategy_raw`).

## Scope

Applies only to the **uploaded-stations-file flow** (`stations_user_uploaded`
== True). The no-upload flow (slider + sidebar Call/Land objective driving
the auto-optimizer, top-10 advisory cards) is unchanged.

## Design

### 1. Front-and-center sort controls (upload mode only)

Two independent horizontal radios, rendered in `render_station_suggestions_grid`
(main panel), directly above the "Suggested Station Placements" header:

```
Suggested Station Placements
Guardian Sort: (•)Calls ( )Land    Responder Sort: ( )Calls (•)Land
[card][card][card][card][card]
[card][card][card][card][card]
```

Only rendered when `stations_user_uploaded` is True.

### 2. Sidebar radios hidden in upload mode

Existing "Guardian Objective" / "Responder Objective" radios
(`dashboard_helpers.py:703-727`) are wrapped in `if not stations_uploaded:`.
They remain exactly as-is for the no-upload flow.

### 3. Shared state — no solver changes

The new front-and-center radios write to the same session keys the sidebar
radios use today (`guard_strat_idx`/`guard_strategy_raw`,
`resp_strat_idx`/`resp_strategy_raw`). `guard_strategy` / `resp_strategy`
passed into the optimizer (`app.py:7256-7257`, `7510-7511`) are computed from
these exactly as today — the solver's actual placement-selection logic and
pin behavior are untouched. Only the widget that sets these values changes
per mode.

### 4. Card sort logic (upload mode only)

`compute_station_suggestions` is unchanged for the no-upload path (still
marginal-gain, still capped at 10, still driven only by `resp_strategy_raw`
— matches current behavior, no regression).

For the upload path, after `sync_station_suggestion_modes` resolves each
card's current mode, `render_station_suggestions_grid` re-sorts the
`suggestions` list in place, descending, using a per-card key:

- mode == 'Guardian' → `land_pct_guardian` or `call_pct_guardian`, per the
  Guardian Sort toggle
- mode == 'Responder' → `land_pct_responder` or `call_pct_responder`, per
  the Responder Sort toggle
- mode == 'Off' → falls back to the Responder metric (stable, deterministic
  position; these aren't deployed so ordering among them is low-stakes)

Ties fall back to the existing tiebreak tuple (`call_pct`, `marginal_calls`,
`-station_idx`) for determinism.

This is a plain descending sort, not overlap-aware — appropriate because
upload mode shows every candidate already; there is no subset selection
happening at display time.

### 5. Rerun behavior

Changing either sort radio relies on Streamlit's automatic rerun-on-widget-change
— no explicit `st.rerun()` call is needed, since the new radio value is read
inline and the re-sort applies within that same run. This differs from the
per-card mode radio, which does call `st.rerun()` explicitly
(`dashboard_helpers.py:2834`, `3016`) because it also needs to update derived
slider-count state before the next render. Flipping a card's own
Guardian/Responder/Off mode continues to trigger that rerun as today, and the
new sort is applied on that rerun using the card's new mode.

## Edge Cases

- No stations file uploaded: no visible or behavioral change.
- Card's role flipped: next render sorts it by its new role's metric.
- All cards Off: falls back to Responder metric for all, per above.

## Files Touched

- `app.py` — wrap sidebar Guardian/Responder Objective radios in
  `if not stations_uploaded:`.
- `modules/dashboard_helpers.py` — add front-and-center Guardian Sort /
  Responder Sort radios (upload mode only); add post-mode-resolution
  descending re-sort in `render_station_suggestions_grid`.

## Out of Scope

- No-upload flow's marginal-gain algorithm, top-10 cap, and sidebar
  Objective radios — unchanged.
- `compute_station_suggestions`'s greedy loop — unchanged (still used
  as-is for no-upload path).
