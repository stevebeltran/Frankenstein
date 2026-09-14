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
