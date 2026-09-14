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
