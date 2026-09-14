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
