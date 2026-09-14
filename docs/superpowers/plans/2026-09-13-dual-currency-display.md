# Dual-Currency (USD/CAD) Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show a live-rate CAD equivalent alongside every app-computed USD figure when the active jurisdiction is Canadian, with no visible change for US jurisdictions.

**Architecture:** A new `modules/currency.py` fetches the USD→CAD rate once per session (disk-cached fallback, `urllib.request` matching the codebase's existing no-key-API pattern), and exposes two formatters (`format_usd`, `format_usd_range`) that every currency call site in `app.py` routes through. A rate badge renders once near the jurisdiction name. Non-CA sessions never touch the network and render byte-identical `"$X"` output.

**Tech Stack:** Python, Streamlit, `urllib.request` (stdlib — matches `modules/boundaries_ca.py`'s Zippopotam pattern), `pytest` + `monkeypatch`.

**Spec:** `docs/superpowers/specs/2026-09-13-dual-currency-display-design.md`

## Global Constraints

- FX source: `https://open.er-api.com/v6/latest/USD`, no API key, 5s timeout.
- Disk cache at `jurisdiction_data/fx_usd_cad.json`, format `{"rate": float, "fetched_at": ISO8601 string}`.
- Rate fetched at most once per `session_state` (memoized in `session_state['fx_usd_cad_ctx']`).
- `format_usd`/`format_usd_range` never raise — always degrade to USD-only on any failure.
- Non-CA session (`is_ca_region(session_state.get('active_state', '')) is False`): formatter output is byte-identical to the current `"$X"` string — no network call, no cache read.
- Only real computed currency call sites are retrofitted. Excluded (left USD-only, unconverted), per the spec's Scope section:
  - `estimate_grants()` bucket strings, app.py:3185-3189.
  - 23 static third-party benchmark/citation lines (full list in spec).
  - app.py:13078 ("Net Program ROI" row) — abbreviated `$NNK` compact format, doesn't fit the full-dollar-string formatter design.
  - False positives (not dollar amounts at all): app.py:9766 (JS template literal), app.py:13173 and 13198 (`USD` substring inside `USDA`).
- 56 real call sites get retrofitted, no deferred subset among them (Tasks 4-8 below cover all 56).

---

## Task 1: `modules/currency.py` — FX fetch + disk cache + session context

**Files:**
- Create: `modules/currency.py`
- Create: `tests/test_currency.py`

**Interfaces:**
- Produces: `fetch_live_usd_cad_rate() -> float` (raises on any failure), `get_usd_cad_context(session_state) -> dict` with keys `rate` (float|None), `timestamp` (str|None), `source` ('live'|'cached'|'unavailable'). Consumed by Task 2's formatters and Task 3's badge.
- Consumes: `is_ca_region` from `modules.boundaries_ca` (already exists).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_currency.py
import json
import urllib.request

import pytest

import modules.currency as currency


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def test_fetch_live_usd_cad_rate_parses_response(monkeypatch):
    def _fake_urlopen(req, timeout=5):
        assert "open.er-api.com/v6/latest/USD" in req.full_url
        return _FakeResponse({"rates": {"CAD": 1.35}})

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
    assert currency.fetch_live_usd_cad_rate() == 1.35


def test_fetch_live_usd_cad_rate_raises_on_network_failure(monkeypatch):
    def _fake_urlopen(req, timeout=5):
        raise OSError("network down")

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
    with pytest.raises(OSError):
        currency.fetch_live_usd_cad_rate()


def test_get_usd_cad_context_live_success_writes_cache(tmp_path, monkeypatch):
    cache_path = tmp_path / "fx_usd_cad.json"
    monkeypatch.setattr(currency, "FX_CACHE_PATH", str(cache_path))
    monkeypatch.setattr(currency, "fetch_live_usd_cad_rate", lambda: 1.35)

    session_state = {}
    ctx = currency.get_usd_cad_context(session_state)

    assert ctx["rate"] == 1.35
    assert ctx["source"] == "live"
    assert ctx["timestamp"]
    assert session_state["fx_usd_cad_ctx"] == ctx
    cached = json.loads(cache_path.read_text())
    assert cached["rate"] == 1.35


def test_get_usd_cad_context_fetch_fails_falls_back_to_disk_cache(tmp_path, monkeypatch):
    cache_path = tmp_path / "fx_usd_cad.json"
    cache_path.write_text(json.dumps({"rate": 1.30, "fetched_at": "2026-09-01T00:00:00+00:00"}))
    monkeypatch.setattr(currency, "FX_CACHE_PATH", str(cache_path))

    def _fail():
        raise OSError("down")

    monkeypatch.setattr(currency, "fetch_live_usd_cad_rate", _fail)

    session_state = {}
    ctx = currency.get_usd_cad_context(session_state)

    assert ctx == {"rate": 1.30, "timestamp": "2026-09-01T00:00:00+00:00", "source": "cached"}


def test_get_usd_cad_context_fetch_fails_no_cache_returns_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(currency, "FX_CACHE_PATH", str(tmp_path / "missing.json"))

    def _fail():
        raise OSError("down")

    monkeypatch.setattr(currency, "fetch_live_usd_cad_rate", _fail)

    session_state = {}
    ctx = currency.get_usd_cad_context(session_state)

    assert ctx == {"rate": None, "timestamp": None, "source": "unavailable"}


def test_get_usd_cad_context_only_fetches_once_per_session(tmp_path, monkeypatch):
    monkeypatch.setattr(currency, "FX_CACHE_PATH", str(tmp_path / "fx.json"))
    call_count = {"n": 0}

    def _fetch():
        call_count["n"] += 1
        return 1.35

    monkeypatch.setattr(currency, "fetch_live_usd_cad_rate", _fetch)

    session_state = {}
    currency.get_usd_cad_context(session_state)
    currency.get_usd_cad_context(session_state)

    assert call_count["n"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_currency.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'modules.currency'`

- [ ] **Step 3: Write the implementation**

```python
# modules/currency.py
"""USD/CAD dual-currency fetch, cache, and session context.

Formatters that consume this context live in this same module — see
format_usd / format_usd_range added in the next task.
"""
import datetime
import json
import os
import urllib.request

FX_API_URL = "https://open.er-api.com/v6/latest/USD"
FX_CACHE_PATH = os.path.join("jurisdiction_data", "fx_usd_cad.json")


def fetch_live_usd_cad_rate():
    """Fetch the current USD->CAD rate. Raises on any failure."""
    req = urllib.request.Request(
        FX_API_URL, headers={"User-Agent": "BRINC-Frankenstein/1.0"}
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return float(data["rates"]["CAD"])


def _read_fx_cache():
    try:
        with open(FX_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return float(data["rate"]), str(data["fetched_at"])
    except Exception:
        return None, None


def _write_fx_cache(rate, timestamp):
    try:
        cache_dir = os.path.dirname(FX_CACHE_PATH)
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
        with open(FX_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"rate": rate, "fetched_at": timestamp}, f)
    except Exception:
        pass


def get_usd_cad_context(session_state):
    """Session-memoized USD->CAD context: {rate, timestamp, source}.

    Fetches at most once per session_state — repeat calls in the same
    session return the stashed result without hitting the network again.
    """
    existing = session_state.get("fx_usd_cad_ctx")
    if existing is not None:
        return existing

    try:
        rate = fetch_live_usd_cad_rate()
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        _write_fx_cache(rate, timestamp)
        ctx = {"rate": rate, "timestamp": timestamp, "source": "live"}
    except Exception:
        cached_rate, cached_timestamp = _read_fx_cache()
        if cached_rate is not None:
            ctx = {"rate": cached_rate, "timestamp": cached_timestamp, "source": "cached"}
        else:
            ctx = {"rate": None, "timestamp": None, "source": "unavailable"}

    session_state["fx_usd_cad_ctx"] = ctx
    return ctx
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_currency.py -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add modules/currency.py tests/test_currency.py
git commit -m "feat(currency): add USD/CAD FX fetch, disk cache, session context"
```

---

## Task 2: `format_usd` / `format_usd_range` formatters

**Files:**
- Modify: `modules/currency.py` (append to file from Task 1)
- Test: `tests/test_currency.py` (append)

**Interfaces:**
- Consumes: `get_usd_cad_context(session_state) -> dict` (Task 1), `is_ca_region(abbr) -> bool` from `modules.boundaries_ca`.
- Produces: `format_usd(amount, session_state, decimals=0) -> str`, `format_usd_range(low, high, session_state, decimals=0) -> str`. Consumed by Task 3 (badge doesn't call these, but shares the module) and Tasks 4-8 (all 56 app.py call sites).

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_currency.py

def test_format_usd_non_ca_passthrough():
    session_state = {"active_state": "IL"}
    assert currency.format_usd(1234567, session_state) == "$1,234,567"


def test_format_usd_ca_with_rate_shows_dual_currency():
    session_state = {
        "active_state": "ON",
        "fx_usd_cad_ctx": {"rate": 1.35, "timestamp": "t", "source": "live"},
    }
    assert currency.format_usd(1000, session_state) == "$1,000 (C$1,350)"


def test_format_usd_ca_rate_none_falls_back_to_usd_only():
    session_state = {
        "active_state": "ON",
        "fx_usd_cad_ctx": {"rate": None, "timestamp": None, "source": "unavailable"},
    }
    assert currency.format_usd(1000, session_state) == "$1,000"


def test_format_usd_range_non_ca_passthrough():
    session_state = {"active_state": "IL"}
    assert currency.format_usd_range(940_000, 1_200_000, session_state) == "$940,000 – $1,200,000"


def test_format_usd_range_ca_with_rate_shows_dual_currency():
    session_state = {
        "active_state": "ON",
        "fx_usd_cad_ctx": {"rate": 1.35, "timestamp": "t", "source": "live"},
    }
    assert currency.format_usd_range(1000, 2000, session_state) == (
        "$1,000 – $2,000 (C$1,350 – C$2,700)"
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_currency.py -v -k format_usd`
Expected: FAIL with `AttributeError: module 'modules.currency' has no attribute 'format_usd'`

- [ ] **Step 3: Write the implementation**

```python
# append to modules/currency.py
from modules.boundaries_ca import is_ca_region


def format_usd(amount, session_state, decimals=0):
    if not is_ca_region(session_state.get("active_state", "")):
        return f"${amount:,.{decimals}f}"
    ctx = get_usd_cad_context(session_state)
    if ctx["rate"] is None:
        return f"${amount:,.{decimals}f}"
    cad_amount = amount * ctx["rate"]
    return f"${amount:,.{decimals}f} (C${cad_amount:,.{decimals}f})"


def format_usd_range(low, high, session_state, decimals=0):
    base = f"${low:,.{decimals}f} – ${high:,.{decimals}f}"
    if not is_ca_region(session_state.get("active_state", "")):
        return base
    ctx = get_usd_cad_context(session_state)
    if ctx["rate"] is None:
        return base
    cad_low = low * ctx["rate"]
    cad_high = high * ctx["rate"]
    return f"{base} (C${cad_low:,.{decimals}f} – C${cad_high:,.{decimals}f})"
```

Move the `from modules.boundaries_ca import is_ca_region` line to the top of `modules/currency.py` with the other imports rather than mid-file — Python allows either, but the file should read top-down like the rest of the codebase's modules.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_currency.py -v`
Expected: 11 PASS

- [ ] **Step 5: Commit**

```bash
git add modules/currency.py tests/test_currency.py
git commit -m "feat(currency): add format_usd/format_usd_range dual-currency formatters"
```

---

## Task 3: Rate badge in `app.py`

**Files:**
- Modify: `app.py:111-117` (import block), `app.py:8666` (insert badge render after existing header)

**Interfaces:**
- Consumes: `get_usd_cad_context`, `format_usd`, `format_usd_range` from `modules.currency` (Tasks 1-2); `is_ca_region` (already imported in app.py at line 112).

- [ ] **Step 1: Add the import**

In `app.py`, immediately after the `modules.boundaries_ca` import block:

```python
from modules.boundaries_ca import (
    is_ca_region,
    fetch_cd_boundary_local,
    fetch_csd_boundary_local,
    fetch_cd_by_centroid,
    fetch_ca_population,
)
from modules.currency import format_usd, format_usd_range, get_usd_cad_context
```

- [ ] **Step 2: Render the badge**

In `app.py`, right after the existing header render (currently ending at line 8666 with `st.markdown(header_html, unsafe_allow_html=True)`), insert:

```python
        st.markdown(header_html, unsafe_allow_html=True)

        if is_ca_region(st.session_state.get('active_state', '')):
            _fx_ctx = get_usd_cad_context(st.session_state)
            if _fx_ctx['source'] == 'unavailable':
                _fx_badge_text = "CAD rate unavailable"
            else:
                _fx_ts = datetime.datetime.fromisoformat(_fx_ctx['timestamp']).strftime('%Y-%m-%d %H:%M')
                _fx_badge_text = f"1 USD = {_fx_ctx['rate']:.2f} CAD as of {_fx_ts}"
                if _fx_ctx['source'] == 'cached':
                    _fx_badge_text += " (cached)"
            st.markdown(
                f'<div style="font-size:0.75rem;color:{text_muted};margin-bottom:8px;">{html.escape(_fx_badge_text)}</div>',
                unsafe_allow_html=True,
            )
```

`datetime` and `html` are already imported at the top of `app.py` (line 23's combined stdlib import). `text_muted` is already in scope at this point in the function (used two lines above at 8657).

- [ ] **Step 3: Syntax-check app.py**

Run: `python -m py_compile app.py`
Expected: no output, exit code 0 (app.py can't be imported/pytest-run directly — it executes Streamlit calls at module scope — so a compile check is the available automated signal here).

- [ ] **Step 4: Run the existing test suite**

Run: `pytest -q`
Expected: same pass count as before this change (no regressions) — full manual browser verification of the badge itself happens in Task 9.

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "feat(currency): render USD/CAD rate badge for Canadian jurisdictions"
```

---

## Task 4: Retrofit — Budget box & Unit Economics header (6 sites)

**Files:**
- Modify: `app.py:8502, 8504, 8507, 8511, 8515, 8533`

**Interfaces:**
- Consumes: `format_usd` (Task 2), already imported (Task 3).

- [ ] **Step 1: Apply the 6 edits**

`app.py:8502`
```python
# before
                <div style="font-size:1.8rem; font-weight:900; color:{budget_box_border}; font-family:monospace;">${annual_savings:,.0f}</div>
# after
                <div style="font-size:1.8rem; font-weight:900; color:{budget_box_border}; font-family:monospace;">{format_usd(annual_savings, st.session_state)}</div>
```

`app.py:8504`
```python
# before
                <div style="font-size:1.05rem; font-weight:800; color:#39FF14; font-family:monospace; margin-top:2px;">${_s_specialty_total:,.0f}</div>
# after
                <div style="font-size:1.05rem; font-weight:800; color:#39FF14; font-family:monospace; margin-top:2px;">{format_usd(_s_specialty_total, st.session_state)}</div>
```

`app.py:8507`
```python
# before
                    <span style="color:#fbbf24; font-weight:700;">${_s_thermal_total:,.0f}/yr</span>
# after
                    <span style="color:#fbbf24; font-weight:700;">{format_usd(_s_thermal_total, st.session_state)}/yr</span>
```

`app.py:8511`
```python
# before
                    <span style="color:#39FF14; font-weight:700;">${_s_k9_total:,.0f}/yr</span>
# after
                    <span style="color:#39FF14; font-weight:700;">{format_usd(_s_k9_total, st.session_state)}/yr</span>
```

`app.py:8515`
```python
# before
                    <span style="color:#fb7121; font-weight:700;">${_s_fire_total:,.0f}/yr</span>
# after
                    <span style="color:#fb7121; font-weight:700;">{format_usd(_s_fire_total, st.session_state)}/yr</span>
```

`app.py:8533`
```python
# before
                    <span style="color:{text_main}; font-weight:700;">${fleet_capex:,.0f}</span>
# after
                    <span style="color:{text_main}; font-weight:700;">{format_usd(fleet_capex, st.session_state)}</span>
```

- [ ] **Step 2: Syntax-check and run test suite**

Run: `python -m py_compile app.py && pytest -q`
Expected: compiles clean; same pass count as before.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat(currency): retrofit budget box + unit economics header to dual-currency"
```

---

## Task 5: Retrofit — SRO section (6 sites)

**Files:**
- Modify: `app.py:10034, 10051, 10225, 10240, 10288, 10612`

**Interfaces:**
- Consumes: `format_usd`, `format_usd_range` (Task 2).

- [ ] **Step 1: Apply the 6 edits**

`app.py:10034`
```python
# before
            _dfr_amort_str  = f"${_dfr_amortized:,}/yr" if _dfr_amortized > 0 else "~$11K–22K/yr"
# after
            _dfr_amort_str  = f"{format_usd(_dfr_amortized, st.session_state)}/yr" if _dfr_amortized > 0 else "~$11K–22K/yr"
```
The `"~$11K–22K/yr"` fallback (shown only when `_dfr_amortized <= 0`) is a static placeholder string, not a computed amount — left as-is.

`app.py:10051`
```python
# before
                        f"${_sro_cost_low:,}–${_sro_cost_high:,} per officer",
# after
                        f"{format_usd_range(_sro_cost_low, _sro_cost_high, st.session_state)} per officer",
```

`app.py:10225`
```python
# before
                  <div style="font-size:1.6rem;font-weight:900;color:#f59e0b;font-family:'IBM Plex Mono',monospace;">${940_000:,} – ${1_200_000:,}</div>
# after
                  <div style="font-size:1.6rem;font-weight:900;color:#f59e0b;font-family:'IBM Plex Mono',monospace;">{format_usd_range(940_000, 1_200_000, st.session_state)}</div>
```

`app.py:10240`
```python
# before
                  <div style="font-size:1.6rem;font-weight:900;color:{accent_color};font-family:'IBM Plex Mono',monospace;">${fleet_capex:,.0f} CapEx</div>
# after
                  <div style="font-size:1.6rem;font-weight:900;color:{accent_color};font-family:'IBM Plex Mono',monospace;">{format_usd(fleet_capex, st.session_state)} CapEx</div>
```

`app.py:10288`
```python
# before
                _fr_dfr_amort_str = f"${_fr_dfr_amortized:,}/yr" if _fr_dfr_amortized > 0 else "~$11K–22K/yr"
# after
                _fr_dfr_amort_str = f"{format_usd(_fr_dfr_amortized, st.session_state)}/yr" if _fr_dfr_amortized > 0 else "~$11K–22K/yr"
```

`app.py:10612`
```python
# before
                  <div style="font-size:1.6rem;font-weight:900;color:{accent_color};font-family:'IBM Plex Mono',monospace;">${fleet_capex:,.0f} CapEx</div>
# after
                  <div style="font-size:1.6rem;font-weight:900;color:{accent_color};font-family:'IBM Plex Mono',monospace;">{format_usd(fleet_capex, st.session_state)} CapEx</div>
```

Note: `app.py:10225` and `app.py:10240`/`10612` are near-duplicate blocks (verify with the line number, not just the text, before editing — `10240` and `10612` are identical text but different call sites and must both be edited).

- [ ] **Step 2: Syntax-check and run test suite**

Run: `python -m py_compile app.py && pytest -q`
Expected: compiles clean; same pass count as before.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat(currency): retrofit SRO section to dual-currency"
```

---

## Task 6: Retrofit — Executive Summary / Cover ROI metrics (14 sites)

**Files:**
- Modify: `app.py:11053, 11958, 12083, 12885, 12886, 12887, 12907, 12909, 12910, 12911, 12928, 12939, 12960, 12971`

**Interfaces:**
- Consumes: `format_usd` (Task 2).

- [ ] **Step 1: Apply the 14 edits**

`app.py:11053`
```python
# before
    <div class="metric m-roi"><div class="k">Annual Savings</div><div class="v">${float(annual_savings or 0):,.0f}</div></div>
# after
    <div class="metric m-roi"><div class="k">Annual Savings</div><div class="v">{format_usd(float(annual_savings or 0), st.session_state)}</div></div>
```

`app.py:11958`
```python
# before
                    f"<tr><td>{d['name']}</td><td>{d['type']}</td><td>{d['avg_time_min']:.1f} min</td><td>{d['faa_ceiling']}</td><td>${d['cost']:,}</td></tr>"
# after
                    f"<tr><td>{d['name']}</td><td>{d['type']}</td><td>{d['avg_time_min']:.1f} min</td><td>{d['faa_ceiling']}</td><td>{format_usd(d['cost'], st.session_state)}</td></tr>"
```

`app.py:12083`
```python
# before
                _dfr_amort_str     = f"${_exp_dfr_amortized:,}/yr" if _exp_dfr_amortized > 0 else "~$11K–22K/yr"
# after
                _dfr_amort_str     = f"{format_usd(_exp_dfr_amortized, st.session_state)}/yr" if _exp_dfr_amortized > 0 else "~$11K–22K/yr"
```

`app.py:12885`
```python
# before
                <div class="cover-meta-cell"><div class="label">Fleet CapEx</div><div class="value accent">${fleet_capex:,.0f}</div></div>
# after
                <div class="cover-meta-cell"><div class="label">Fleet CapEx</div><div class="value accent">{format_usd(fleet_capex, st.session_state)}</div></div>
```

`app.py:12886`
```python
# before
                <div class="cover-meta-cell"><div class="label">Annual Savings</div><div class="value gold">${annual_savings:,.0f}</div></div>
# after
                <div class="cover-meta-cell"><div class="label">Annual Savings</div><div class="value gold">{format_usd(annual_savings, st.session_state)}</div></div>
```

`app.py:12887`
```python
# before
                <div class="cover-meta-cell"><div class="label">Add'l Thermal + K-9</div><div class="value accent">${possible_additional_savings:,.0f}</div></div>
# after
                <div class="cover-meta-cell"><div class="label">Add'l Thermal + K-9</div><div class="value accent">{format_usd(possible_additional_savings, st.session_state)}</div></div>
```

`app.py:12907` — **mixed line**: wrap only the two computed `CONFIG[...]` amounts; leave the static `"$76–$120/call (IACP/DOJ)"` benchmark citation untouched.
```python
# before
          <div class="section-eyebrow"><span class="pg-num">01</span><span class="pg-title">Executive Summary</span><span class="src" data-src="Sources: Incident coverage &amp; response time computed from uploaded CAD data via BRINC geospatial optimizer. Hardware pricing: BRINC Responder ${CONFIG['RESPONDER_COST']:,} · Guardian ${CONFIG['GUARDIAN_COST']:,} per unit{'' if st.session_state.get('pricing_tier', 'Safe Guard') == 'Custom Quote' else ' (' + st.session_state.get('pricing_tier', 'Safe Guard') + ')'}. Officer dispatch cost benchmark: $76–$120/call (IACP/DOJ). Population: US Census Bureau ACS.">ⓘ</span></div>
# after
          <div class="section-eyebrow"><span class="pg-num">01</span><span class="pg-title">Executive Summary</span><span class="src" data-src="Sources: Incident coverage &amp; response time computed from uploaded CAD data via BRINC geospatial optimizer. Hardware pricing: BRINC Responder {format_usd(CONFIG['RESPONDER_COST'], st.session_state)} · Guardian {format_usd(CONFIG['GUARDIAN_COST'], st.session_state)} per unit{'' if st.session_state.get('pricing_tier', 'Safe Guard') == 'Custom Quote' else ' (' + st.session_state.get('pricing_tier', 'Safe Guard') + ')'}. Officer dispatch cost benchmark: $76–$120/call (IACP/DOJ). Population: US Census Bureau ACS.">ⓘ</span></div>
```

`app.py:12909`
```python
# before
            <div class="metric-cell"><div class="m-label">Fleet Capital Expenditure</div><div class="m-value cyan">${fleet_capex:,.0f}</div><div class="m-sub">{actual_k_responder} Responder · {actual_k_guardian} Guardian</div></div>
# after
            <div class="metric-cell"><div class="m-label">Fleet Capital Expenditure</div><div class="m-value cyan">{format_usd(fleet_capex, st.session_state)}</div><div class="m-sub">{actual_k_responder} Responder · {actual_k_guardian} Guardian</div></div>
```

`app.py:12910`
```python
# before
            <div class="metric-cell"><div class="m-label">Annual Savings Capacity</div><div class="m-value gold">${annual_savings:,.0f}</div><div class="m-sub">At {int(dfr_dispatch_rate*100)}% dispatch · {int(deflection_rate*100)}% resolution</div></div>
# after
            <div class="metric-cell"><div class="m-label">Annual Savings Capacity</div><div class="m-value gold">{format_usd(annual_savings, st.session_state)}</div><div class="m-sub">At {int(dfr_dispatch_rate*100)}% dispatch · {int(deflection_rate*100)}% resolution</div></div>
```

`app.py:12911`
```python
# before
            <div class="metric-cell"><div class="m-label">Specialty Response Value</div><div class="m-value green">${possible_additional_savings:,.0f}</div><div class="m-sub">Thermal ${thermal_savings:,.0f} · K-9 ${k9_savings:,.0f} · Fire ${fire_savings:,.0f}</div></div>
# after
            <div class="metric-cell"><div class="m-label">Specialty Response Value</div><div class="m-value green">{format_usd(possible_additional_savings, st.session_state)}</div><div class="m-sub">Thermal {format_usd(thermal_savings, st.session_state)} · K-9 {format_usd(k9_savings, st.session_state)} · Fire {format_usd(fire_savings, st.session_state)}</div></div>
```

`app.py:12928`
```python
# before
                <div style="font-size:12px;color:#aabbdd;">Responder: <strong>${CONFIG['RESPONDER_COST']:,}</strong> · Guardian: <strong>${CONFIG['GUARDIAN_COST']:,}</strong></div>
# after
                <div style="font-size:12px;color:#aabbdd;">Responder: <strong>{format_usd(CONFIG['RESPONDER_COST'], st.session_state)}</strong> · Guardian: <strong>{format_usd(CONFIG['GUARDIAN_COST'], st.session_state)}</strong></div>
```

`app.py:12939`
```python
# before
            <strong>${annual_savings:,.0f} in annual operational savings</strong> with a break-even horizon of {break_even_text.lower()}.
# after
            <strong>{format_usd(annual_savings, st.session_state)} in annual operational savings</strong> with a break-even horizon of {break_even_text.lower()}.
```

`app.py:12960`
```python
# before
                <div class="fc-row"><span class="k">Unit CapEx</span><span class="v">${CONFIG['GUARDIAN_COST']:,}</span></div>
# after
                <div class="fc-row"><span class="k">Unit CapEx</span><span class="v">{format_usd(CONFIG['GUARDIAN_COST'], st.session_state)}</span></div>
```

`app.py:12971`
```python
# before
                <div class="fc-row"><span class="k">Unit CapEx</span><span class="v">${CONFIG['RESPONDER_COST']:,}</span></div>
# after
                <div class="fc-row"><span class="k">Unit CapEx</span><span class="v">{format_usd(CONFIG['RESPONDER_COST'], st.session_state)}</span></div>
```

- [ ] **Step 2: Syntax-check and run test suite**

Run: `python -m py_compile app.py && pytest -q`
Expected: compiles clean; same pass count as before.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat(currency): retrofit executive summary + cover ROI metrics to dual-currency"
```

---

## Task 7: Retrofit — Fiscal Impact narrative & Fire Department section (19 sites)

**Files:**
- Modify: `app.py:13066, 13074, 13075, 13078(excluded — see note), 13106, 13124, 13129, 13134, 13135, 13146, 13152, 13190, 13207, 13208, 13209, 13210, 13216, 13217, 13218, 13220`

**Interfaces:**
- Consumes: `format_usd` (Task 2).

- [ ] **Step 1: Apply the 19 edits**

`app.py:13066` — 7 computed tokens on this one line, all wrapped:
```python
# before
            <p><strong>Fiscal Impact &amp; Return on Investment:</strong> Total program capital expenditure is <strong>${fleet_capex:,.0f}</strong> ({actual_k_responder} Responder × ${CONFIG["RESPONDER_COST"]:,} + {actual_k_guardian} Guardian × ${CONFIG["GUARDIAN_COST"]:,}). At a <strong>{int(dfr_dispatch_rate*100)}% DFR dispatch rate</strong> and <strong>{int(deflection_rate*100)}% call resolution rate</strong> (no officer dispatch required), the program is projected to generate <strong>${annual_savings:,.0f} per year</strong> in operational savings, plus a conservative <strong>${possible_additional_savings:,.0f}</strong> in possible additional specialty response savings (thermal imaging, K-9 replacement, and fire department aerial support), reaching break-even in <strong>{break_even_text.lower()}</strong>. Cost per drone response is ${CONFIG["DRONE_COST_PER_CALL"]} versus ${CONFIG["OFFICER_COST_PER_CALL"]} for a ground patrol dispatch — a <strong>{int((1-CONFIG["DRONE_COST_PER_CALL"]/CONFIG["OFFICER_COST_PER_CALL"])*100)}% cost reduction</strong> per incident. The program also reduces officer exposure to unknown-risk calls, decreasing liability and improving officer retention outcomes.</p>
# after
            <p><strong>Fiscal Impact &amp; Return on Investment:</strong> Total program capital expenditure is <strong>{format_usd(fleet_capex, st.session_state)}</strong> ({actual_k_responder} Responder × {format_usd(CONFIG["RESPONDER_COST"], st.session_state)} + {actual_k_guardian} Guardian × {format_usd(CONFIG["GUARDIAN_COST"], st.session_state)}). At a <strong>{int(dfr_dispatch_rate*100)}% DFR dispatch rate</strong> and <strong>{int(deflection_rate*100)}% call resolution rate</strong> (no officer dispatch required), the program is projected to generate <strong>{format_usd(annual_savings, st.session_state)} per year</strong> in operational savings, plus a conservative <strong>{format_usd(possible_additional_savings, st.session_state)}</strong> in possible additional specialty response savings (thermal imaging, K-9 replacement, and fire department aerial support), reaching break-even in <strong>{break_even_text.lower()}</strong>. Cost per drone response is {format_usd(CONFIG["DRONE_COST_PER_CALL"], st.session_state)} versus {format_usd(CONFIG["OFFICER_COST_PER_CALL"], st.session_state)} for a ground patrol dispatch — a <strong>{int((1-CONFIG["DRONE_COST_PER_CALL"]/CONFIG["OFFICER_COST_PER_CALL"])*100)}% cost reduction</strong> per incident. The program also reduces officer exposure to unknown-risk calls, decreasing liability and improving officer retention outcomes.</p>
```

`app.py:13074`
```python
# before
                <tr><td>Annual Savings</td><td>${annual_savings:,.0f}</td><td>${annual_savings*1.05:,.0f}</td><td>${annual_savings*1.1:,.0f}</td><td>${annual_savings*1.22:,.0f}</td></tr>
# after
                <tr><td>Annual Savings</td><td>{format_usd(annual_savings, st.session_state)}</td><td>{format_usd(annual_savings*1.05, st.session_state)}</td><td>{format_usd(annual_savings*1.1, st.session_state)}</td><td>{format_usd(annual_savings*1.22, st.session_state)}</td></tr>
```

`app.py:13075`
```python
# before
                <tr><td>Cumulative Savings</td><td>${annual_savings:,.0f}</td><td>${annual_savings*3.15:,.0f}</td><td>${annual_savings*5.53:,.0f}</td><td>${annual_savings*12.58:,.0f}</td></tr>
# after
                <tr><td>Cumulative Savings</td><td>{format_usd(annual_savings, st.session_state)}</td><td>{format_usd(annual_savings*3.15, st.session_state)}</td><td>{format_usd(annual_savings*5.53, st.session_state)}</td><td>{format_usd(annual_savings*12.58, st.session_state)}</td></tr>
```

**`app.py:13078` — do not edit.** This is the "Net Program ROI" row using an abbreviated `+$NNK` / `(NNK deficit)` compact format (divides by 1000, suffixes `K`, no thousands separator on the underlying value). `format_usd` produces full comma-formatted dollar strings and would either break this cell's compact style or require a formatter variant outside this spec's scope. Left USD-only per the spec's Scope section.

`app.py:13106`
```python
# before
            <div class="grant-stat gold"><div class="gs-label">Annual Savings</div><div class="gs-val">${annual_savings:,.0f}</div><div class="gs-sub">break-even {break_even_text.lower()}</div></div>
# after
            <div class="grant-stat gold"><div class="gs-label">Annual Savings</div><div class="gs-val">{format_usd(annual_savings, st.session_state)}</div><div class="gs-sub">break-even {break_even_text.lower()}</div></div>
```

`app.py:13124`
```python
# before
              <div class="m-value" style="color:#fb7121">${fire_savings * 0.8:,.0f}/yr</div>
# after
              <div class="m-value" style="color:#fb7121">{format_usd(fire_savings * 0.8, st.session_state)}/yr</div>
```

`app.py:13129`
```python
# before
              <div class="m-value" style="color:#fb7121">${fire_savings * 0.2:,.0f}/yr</div>
# after
              <div class="m-value" style="color:#fb7121">{format_usd(fire_savings * 0.2, st.session_state)}/yr</div>
```

`app.py:13134`
```python
# before
              <div class="m-value" style="color:#fb7121">${fire_savings:,.0f}/yr</div>
# after
              <div class="m-value" style="color:#fb7121">{format_usd(fire_savings, st.session_state)}/yr</div>
```

`app.py:13135`
```python
# before
              <div class="m-sub">${CONFIG["FIRE_SAVINGS_PER_CALL"]} blended savings per fire call</div>
# after
              <div class="m-sub">{format_usd(CONFIG["FIRE_SAVINGS_PER_CALL"], st.session_state)} blended savings per fire call</div>
```

`app.py:13146`
```python
# before
                <td style="color:#fb7121;font-weight:700">${fire_savings * 0.8:,.0f}/yr</td>
# after
                <td style="color:#fb7121;font-weight:700">{format_usd(fire_savings * 0.8, st.session_state)}/yr</td>
```

`app.py:13152`
```python
# before
                <td style="color:#fb7121;font-weight:700">${fire_savings * 0.2:,.0f}/yr</td>
# after
                <td style="color:#fb7121;font-weight:700">{format_usd(fire_savings * 0.2, st.session_state)}/yr</td>
```

`app.py:13190` — **mixed line**: wrap only `fire_savings`; leave the two static citations (`$3,000–$8,000 per aerial ladder deployment (NFPA)` and `$200/hr equivalent labor cost`) untouched.
```python
# before
            <p><strong>Fiscal Impact — Fire Department:</strong> The modeled fire department value of <strong>${fire_savings:,.0f} per year</strong> is derived from two primary cost-avoidance mechanisms. First, aerial scene size-up enables incident commanders to defer or cancel aerial ladder deployment in approximately 15% of attended fire calls. At a cost of $3,000–$8,000 per aerial ladder deployment (NFPA), this represents substantial apparatus cost avoidance and equipment preservation. Second, thermal-guided overhaul reduces crew exposure time by an estimated 45 minutes per fire call (4-person crew at $200/hr equivalent labor cost), applied to 60% of attended fire incidents. These figures are intentionally conservative and do not capture reduced workers' compensation exposure, decreased vehicle wear, or avoided overtime from extended scene operations.</p>
# after
            <p><strong>Fiscal Impact — Fire Department:</strong> The modeled fire department value of <strong>{format_usd(fire_savings, st.session_state)} per year</strong> is derived from two primary cost-avoidance mechanisms. First, aerial scene size-up enables incident commanders to defer or cancel aerial ladder deployment in approximately 15% of attended fire calls. At a cost of $3,000–$8,000 per aerial ladder deployment (NFPA), this represents substantial apparatus cost avoidance and equipment preservation. Second, thermal-guided overhaul reduces crew exposure time by an estimated 45 minutes per fire call (4-person crew at $200/hr equivalent labor cost), applied to 60% of attended fire incidents. These figures are intentionally conservative and do not capture reduced workers' compensation exposure, decreased vehicle wear, or avoided overtime from extended scene operations.</p>
```

`app.py:13207`
```python
# before
                <tr><td>Annual Fire Dept Value</td><td>${fire_savings:,.0f}</td><td>${fire_savings*1.05:,.0f}</td><td>${fire_savings*1.10:,.0f}</td><td>${fire_savings*1.22:,.0f}</td></tr>
# after
                <tr><td>Annual Fire Dept Value</td><td>{format_usd(fire_savings, st.session_state)}</td><td>{format_usd(fire_savings*1.05, st.session_state)}</td><td>{format_usd(fire_savings*1.10, st.session_state)}</td><td>{format_usd(fire_savings*1.22, st.session_state)}</td></tr>
```

`app.py:13208`
```python
# before
                <tr><td>Cumulative Fire Value</td><td>${fire_savings:,.0f}</td><td>${fire_savings*3.15:,.0f}</td><td>${fire_savings*5.53:,.0f}</td><td>${fire_savings*12.58:,.0f}</td></tr>
# after
                <tr><td>Cumulative Fire Value</td><td>{format_usd(fire_savings, st.session_state)}</td><td>{format_usd(fire_savings*3.15, st.session_state)}</td><td>{format_usd(fire_savings*5.53, st.session_state)}</td><td>{format_usd(fire_savings*12.58, st.session_state)}</td></tr>
```

`app.py:13209`
```python
# before
                <tr><td>Scene Size-Up Savings</td><td>${fire_savings*0.8:,.0f}</td><td>${fire_savings*0.8*1.05:,.0f}</td><td>${fire_savings*0.8*1.10:,.0f}</td><td>${fire_savings*0.8*1.22:,.0f}</td></tr>
# after
                <tr><td>Scene Size-Up Savings</td><td>{format_usd(fire_savings*0.8, st.session_state)}</td><td>{format_usd(fire_savings*0.8*1.05, st.session_state)}</td><td>{format_usd(fire_savings*0.8*1.10, st.session_state)}</td><td>{format_usd(fire_savings*0.8*1.22, st.session_state)}</td></tr>
```

`app.py:13210`
```python
# before
                <tr><td>Overhaul Crew Savings</td><td>${fire_savings*0.2:,.0f}</td><td>${fire_savings*0.2*1.05:,.0f}</td><td>${fire_savings*0.2*1.10:,.0f}</td><td>${fire_savings*0.2*1.22:,.0f}</td></tr>
# after
                <tr><td>Overhaul Crew Savings</td><td>{format_usd(fire_savings*0.2, st.session_state)}</td><td>{format_usd(fire_savings*0.2*1.05, st.session_state)}</td><td>{format_usd(fire_savings*0.2*1.10, st.session_state)}</td><td>{format_usd(fire_savings*0.2*1.22, st.session_state)}</td></tr>
```

`app.py:13216`
```python
# before
            <div class="grant-stat" style="border-color:rgba(251,113,33,0.4)"><div class="gs-label">Scene Size-Up Value</div><div class="gs-val" style="color:#fb7121">${fire_savings*0.8:,.0f}</div><div class="gs-sub">aerial ladder cost avoidance</div></div>
# after
            <div class="grant-stat" style="border-color:rgba(251,113,33,0.4)"><div class="gs-label">Scene Size-Up Value</div><div class="gs-val" style="color:#fb7121">{format_usd(fire_savings*0.8, st.session_state)}</div><div class="gs-sub">aerial ladder cost avoidance</div></div>
```

`app.py:13217`
```python
# before
            <div class="grant-stat" style="border-color:rgba(251,113,33,0.4)"><div class="gs-label">Overhaul Value</div><div class="gs-val" style="color:#fb7121">${fire_savings*0.2:,.0f}</div><div class="gs-sub">crew time &amp; hotspot detection</div></div>
# after
            <div class="grant-stat" style="border-color:rgba(251,113,33,0.4)"><div class="gs-label">Overhaul Value</div><div class="gs-val" style="color:#fb7121">{format_usd(fire_savings*0.2, st.session_state)}</div><div class="gs-sub">crew time &amp; hotspot detection</div></div>
```

`app.py:13218`
```python
# before
            <div class="grant-stat gold"><div class="gs-label">Total Fire Value</div><div class="gs-val">${fire_savings:,.0f}/yr</div><div class="gs-sub">${CONFIG["FIRE_SAVINGS_PER_CALL"]}/call blended</div></div>
# after
            <div class="grant-stat gold"><div class="gs-label">Total Fire Value</div><div class="gs-val">{format_usd(fire_savings, st.session_state)}/yr</div><div class="gs-sub">{format_usd(CONFIG["FIRE_SAVINGS_PER_CALL"], st.session_state)}/call blended</div></div>
```

`app.py:13220`
```python
# before
            <div class="grant-stat" style="border-color:rgba(251,113,33,0.4)"><div class="gs-label">10-Year Fire Value</div><div class="gs-val" style="color:#fb7121">${fire_savings*12.58:,.0f}</div><div class="gs-sub">cumulative projected value</div></div>
# after
            <div class="grant-stat" style="border-color:rgba(251,113,33,0.4)"><div class="gs-label">10-Year Fire Value</div><div class="gs-val" style="color:#fb7121">{format_usd(fire_savings*12.58, st.session_state)}</div><div class="gs-sub">cumulative projected value</div></div>
```

- [ ] **Step 2: Syntax-check and run test suite**

Run: `python -m py_compile app.py && pytest -q`
Expected: compiles clean; same pass count as before.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat(currency): retrofit fiscal impact narrative + fire dept section to dual-currency"
```

---

## Task 8: Retrofit — Narcotics / Community Sponsor / SRO table (11 sites)

**Files:**
- Modify: `app.py:13251, 13261, 13268, 13278, 13279, 13280, 13282, 13363, 13376, 13480, 13536`

**Interfaces:**
- Consumes: `format_usd` (Task 2).

- [ ] **Step 1: Apply the 11 edits**

`app.py:13251`
```python
# before
            <strong>Estimated Annual Value:</strong> The modeled narcotics prevention, deterrence &amp; response value of <strong>${narcotics_savings:,.0f} per year</strong> is derived from an estimated <strong>{narcotics_calls_annual:,.0f} narcotics-related calls</strong> annually within the coverage area, split between hot-spot deterrence coverage (persistent overwatch of known drug markets and trafficking corridors) and officer safety/reconnaissance value (aerial intelligence ahead of ground entry). Figures are conservative and do not capture reduced use-of-force incidents, faster case clearance, or avoided overtime from extended scene operations.
# after
            <strong>Estimated Annual Value:</strong> The modeled narcotics prevention, deterrence &amp; response value of <strong>{format_usd(narcotics_savings, st.session_state)} per year</strong> is derived from an estimated <strong>{narcotics_calls_annual:,.0f} narcotics-related calls</strong> annually within the coverage area, split between hot-spot deterrence coverage (persistent overwatch of known drug markets and trafficking corridors) and officer safety/reconnaissance value (aerial intelligence ahead of ground entry). Figures are conservative and do not capture reduced use-of-force incidents, faster case clearance, or avoided overtime from extended scene operations.
```

`app.py:13261`
```python
# before
              <div style="width:90px;text-align:right;font-size:12px;font-weight:700;color:#0077aa;flex-shrink:0;">${narcotics_savings*0.6:,.0f}</div>
# after
              <div style="width:90px;text-align:right;font-size:12px;font-weight:700;color:#0077aa;flex-shrink:0;">{format_usd(narcotics_savings*0.6, st.session_state)}</div>
```

`app.py:13268`
```python
# before
              <div style="width:90px;text-align:right;font-size:12px;font-weight:700;color:#0077aa;flex-shrink:0;">${narcotics_savings*0.4:,.0f}</div>
# after
              <div style="width:90px;text-align:right;font-size:12px;font-weight:700;color:#0077aa;flex-shrink:0;">{format_usd(narcotics_savings*0.4, st.session_state)}</div>
```

`app.py:13278`
```python
# before
            <div class="grant-stat" style="border-color:rgba(0,210,255,0.4)"><div class="gs-label">Hot-Spot Deterrence Value</div><div class="gs-val">${narcotics_savings*0.6:,.0f}</div><div class="gs-sub">persistent hot-spot overwatch</div></div>
# after
            <div class="grant-stat" style="border-color:rgba(0,210,255,0.4)"><div class="gs-label">Hot-Spot Deterrence Value</div><div class="gs-val">{format_usd(narcotics_savings*0.6, st.session_state)}</div><div class="gs-sub">persistent hot-spot overwatch</div></div>
```

`app.py:13279`
```python
# before
            <div class="grant-stat" style="border-color:rgba(0,210,255,0.4)"><div class="gs-label">Officer Safety Value</div><div class="gs-val">${narcotics_savings*0.4:,.0f}</div><div class="gs-sub">recon ahead of ground entry</div></div>
# after
            <div class="grant-stat" style="border-color:rgba(0,210,255,0.4)"><div class="gs-label">Officer Safety Value</div><div class="gs-val">{format_usd(narcotics_savings*0.4, st.session_state)}</div><div class="gs-sub">recon ahead of ground entry</div></div>
```

`app.py:13280`
```python
# before
            <div class="grant-stat gold"><div class="gs-label">Total Narcotics Value</div><div class="gs-val">${narcotics_savings:,.0f}/yr</div><div class="gs-sub">${CONFIG["NARCOTICS_SAVINGS_PER_CALL"]}/call blended</div></div>
# after
            <div class="grant-stat gold"><div class="gs-label">Total Narcotics Value</div><div class="gs-val">{format_usd(narcotics_savings, st.session_state)}/yr</div><div class="gs-sub">{format_usd(CONFIG["NARCOTICS_SAVINGS_PER_CALL"], st.session_state)}/call blended</div></div>
```

`app.py:13282`
```python
# before
            <div class="grant-stat" style="border-color:rgba(0,210,255,0.4)"><div class="gs-label">10-Year Narcotics Value</div><div class="gs-val">${narcotics_savings*12.58:,.0f}</div><div class="gs-sub">cumulative projected value</div></div>
# after
            <div class="grant-stat" style="border-color:rgba(0,210,255,0.4)"><div class="gs-label">10-Year Narcotics Value</div><div class="gs-val">{format_usd(narcotics_savings*12.58, st.session_state)}</div><div class="gs-sub">cumulative projected value</div></div>
```

`app.py:13363`
```python
# before
          <p>Total program CapEx is <strong>${fleet_capex:,.0f}</strong>. The {prop_city} Police Department is seeking community partnership contributions to offset a portion of this cost and accelerate deployment. Every dollar contributed directly funds equipment that protects your street, your block, your customers.</p>
# after
          <p>Total program CapEx is <strong>{format_usd(fleet_capex, st.session_state)}</strong>. The {prop_city} Police Department is seeking community partnership contributions to offset a portion of this cost and accelerate deployment. Every dollar contributed directly funds equipment that protects your street, your block, your customers.</p>
```

`app.py:13376` — **mixed line**: wrap only the computed projection; leave the static "$10,000 contributed" example amount untouched.
```python
# before
          <p>For every <strong>$10,000</strong> contributed, the program is projected to generate approximately <strong>${int(annual_savings/max(fleet_capex,1)*10000):,}</strong> in annual operational savings and property crime cost avoidance for the {prop_city} business community — a {round(annual_savings/max(fleet_capex,1),1):.1f}x return on community investment.</p>
# after
          <p>For every <strong>$10,000</strong> contributed, the program is projected to generate approximately <strong>{format_usd(int(annual_savings/max(fleet_capex,1)*10000), st.session_state)}</strong> in annual operational savings and property crime cost avoidance for the {prop_city} business community — a {round(annual_savings/max(fleet_capex,1),1):.1f}x return on community investment.</p>
```

`app.py:13480`
```python
# before
                  <td style="text-align:center;color:#0369a1;">${int(fleet_capex/7):,}/yr amortized (7-yr) · {actual_k_responder + actual_k_guardian} units</td></tr>
# after
                  <td style="text-align:center;color:#0369a1;">{format_usd(int(fleet_capex/7), st.session_state)}/yr amortized (7-yr) · {actual_k_responder + actual_k_guardian} units</td></tr>
```

`app.py:13536`
```python
# before
              <div class="fc-val">${fleet_capex:,.0f} CapEx</div>
# after
              <div class="fc-val">{format_usd(fleet_capex, st.session_state)} CapEx</div>
```

- [ ] **Step 2: Syntax-check and run test suite**

Run: `python -m py_compile app.py && pytest -q`
Expected: compiles clean; same pass count as before.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat(currency): retrofit narcotics + community sponsor + SRO table to dual-currency"
```

---

## Task 9: Completeness check + manual verification

**Files:** none (verification only)

**Interfaces:** none — this task validates Tasks 1-8 together.

- [ ] **Step 1: Confirm no real call site was missed**

Run:
```bash
grep -n '\$[0-9{]\|USD' app.py
```
Expected: exactly 32 remaining matches — the 5 `estimate_grants()` lines (3185-3189), the 23 static-citation lines, the 1 `$NNK`-abbreviated ROI line (13078), and the 3 false positives (9766, 13173, 13198). Every other line that was in the original 88-line grep output must now read `format_usd(...)` or `format_usd_range(...)` instead of a raw `$` literal. If the count differs from 32, cross-reference against the spec's Scope section line lists and this plan's Tasks 4-8 before proceeding.

- [ ] **Step 2: Full test suite**

Run: `pytest -q`
Expected: all tests pass, count is the pre-change count (84, per the last recorded full run) plus the 11 new tests from Tasks 1-2 (95 total) — confirm no regressions.

- [ ] **Step 3: Manual verification against the running app**

Start the app (`streamlit run app.py` or the project's usual launch command). Load a Canadian jurisdiction (e.g. Toronto, ON) and confirm:
- The rate badge renders near the jurisdiction name with either a live rate, a `(cached)` rate, or "CAD rate unavailable".
- Every retrofitted figure (budget box, unit economics, SRO section, executive summary, fiscal impact narrative, fire department section, narcotics section, community sponsor section) shows `$X (C$Y)`.
- The excluded lines (grant tiers, benchmark citations, the ROI `$NNK` row) still show USD-only, unchanged.

Then load a US jurisdiction (e.g. Buffalo, NY) and confirm the report is pixel-identical to the pre-change output — no badge, no `(C$...)` parentheticals anywhere, no network calls (check the browser/console network tab or app logs if available).

- [ ] **Step 4: Record the result**

No commit for this task (verification only). If Step 1 or Step 3 surfaces a missed or incorrectly-converted site, fix it as part of whichever Task 4-8 owns that line, re-run Steps 1-3, then continue.
