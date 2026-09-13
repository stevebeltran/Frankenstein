# Dual-Currency (USD/CAD) Display — Design

Date: 2026-09-13
Status: Approved, pending implementation plan

## Context

The Canada mapping expansion (merged 2026-09-12, commit `0818382`) added
province/census-division/census-subdivision jurisdiction lookup, auto-detected
by province abbreviation via `is_ca_region()` in `modules/boundaries_ca.py`.
Every financial figure in the app (annual savings, CapEx, per-officer cost
comparisons, ROI, etc.) is still USD-only, regardless of jurisdiction. This
is a follow-up: when the active jurisdiction is Canadian, show a live-rate
CAD equivalent alongside every USD figure.

This is the first of two independent follow-ups scoped out of the Canada
mapping handoff (the second, km/km² unit display, is a separate spec).

## Scope

`app.py` has 87 real currency-literal call sites (grep for `$[0-9{]` /
`USD`, minus one false positive — a JS template literal
(`` `Day ${day} · ${h}:${m}` ``) at app.py:9766, which is JavaScript
interpolation syntax, not a dollar amount). All 87 get retrofitted to the
shared formatter in this pass — no deferred subset.

**Explicitly out of scope:** `estimate_grants()` (app.py:3184) returns a
static population-tier bucket string like `"$1.5M - $3.0M+"` modeling US
federal/state grant programs (DOJ/BJA-style). It is not a precise computed
dollar amount, and the underlying concept (US grant programs) may not even
transfer to a Canadian jurisdiction. It stays USD-only, unconverted.

The km/km² unit-display work is a separate, independent feature (different
call sites, no external dependency) — out of scope for this spec.

## Trigger condition

CAD display only appears when the active jurisdiction is Canadian:
`is_ca_region(session_state.get('active_state', ''))` — the same check
`modules/onboarding.py` already uses to dispatch boundary/population lookups
to the CA path. A US-only session is unaffected; every formatter call is a
no-op passthrough to today's plain `"$X"` output.

## Architecture

New module `modules/currency.py`:

### FX rate fetch + cache

- `fetch_live_usd_cad_rate() -> float` — GET
  `https://open.er-api.com/v6/latest/USD` (free, no API key — matches the
  existing no-key pattern used for Zippopotam.us and StatCan calls
  elsewhere in this codebase), 5s timeout, extract `rates['CAD']`. Raises on
  any failure (network, timeout, missing key, non-200).
- Disk cache at `jurisdiction_data/fx_usd_cad.json` (`{"rate": float,
  "fetched_at": ISO8601 string}`) — `jurisdiction_data/` is the same
  directory the app already writes runtime-fetched boundary shapefiles to.
- `get_usd_cad_context(session_state) -> dict` with keys `rate` (float or
  `None`), `timestamp` (ISO8601 string or `None`), `source` (one of
  `'live'`, `'cached'`, `'unavailable'`). Behavior:
  1. If `session_state['fx_usd_cad_ctx']` is already set this session,
     return it unchanged (fetch happens at most once per browser session,
     not on every rerun, and not shared process-wide across other users'
     sessions).
  2. Otherwise try `fetch_live_usd_cad_rate()`. On success: write the disk
     cache, build `{rate, timestamp: now, source: 'live'}`, stash in
     `session_state`, return it.
  3. On failure, read the disk cache file. If present: build `{rate,
     timestamp: <cached fetched_at>, source: 'cached'}`, stash, return it.
  4. If no disk cache exists either (cold start, first run, no network):
     build `{rate: None, timestamp: None, source: 'unavailable'}`, stash,
     return it.

### Formatters

- `format_usd(amount, session_state, decimals=0) -> str` — single-value
  formatter. Non-CA session or `rate is None`: `f"${amount:,.{decimals}f}"`
  unchanged. CA session with a rate: `f"${amount:,.{decimals}f} (C${amount
  * rate:,.{decimals}f})"`.
- `format_usd_range(low, high, session_state, decimals=0) -> str` — same
  gating, dual-formats both bounds: `"$940,000 – $1,200,000 (C$1,269,000 –
  C$1,620,000)"`.

### Rate badge

One badge rendered once, near the existing jurisdiction-name line
(app.py:8654, where the active city/province name already renders) — only
for CA sessions:
- `source == 'live'`: `"1 USD = 1.35 CAD as of 2026-09-13 08:00"`
- `source == 'cached'`: same text + a `(cached)` tag, using the cached
  fetch's original timestamp (not "now") so staleness is visible.
- `source == 'unavailable'`: `"CAD rate unavailable"` — no rate is guessed.

## Rejected approach

A regex pass over the fully-rendered HTML string (at each `st.markdown`
call, or once globally) to auto-detect `$`-prefixed amounts and append a
CAD parenthetical, instead of touching each of the 87 call sites
individually. Rejected: this is a financial-figures tool, and the JS
template-literal false positive already found during scoping
(`` `Day ${day}` ``) demonstrates that plain-text `$` detection is fragile
across ~90 disparate hand-written HTML blocks with varying decimal
precision, ranges, and embedded JS. A wrong or duplicated dollar figure is
worse than the larger, but explicit and reviewable, diff of 87 call-site
edits.

## Error handling

- FX fetch failure (network/timeout/malformed response): caught inside
  `fetch_live_usd_cad_rate()`'s caller (`get_usd_cad_context`), never
  raises out to the Streamlit render path — falls through to disk cache,
  then to `'unavailable'`.
- Disk cache read/write failures (missing dir, permissions, corrupt JSON):
  caught and treated as "no cache", same as a cold start.
- `format_usd`/`format_usd_range` never raise on a missing rate — they
  degrade to USD-only output.

## Testing

- `format_usd` / `format_usd_range`: non-CA passthrough, CA with a rate,
  CA with `rate=None` (both `'cached'`-with-no-rate — shouldn't occur but
  defensively tested — and `'unavailable'`).
- `get_usd_cad_context`: live fetch succeeds; live fetch fails + disk cache
  exists (returns cached, correct stale timestamp); live fetch fails + no
  disk cache (returns unavailable); second call within the same
  `session_state` does not re-fetch (mock the network call, assert it's
  called at most once).
- Manual verification against the running app: a Canadian jurisdiction
  (e.g. Toronto ON) shows the badge + dual-currency figures; a US
  jurisdiction (e.g. Buffalo NY) is pixel-identical to pre-change output.
