import json
import urllib.request

from modules.boundaries_ca import (
    is_ca_region,
    detect_country_from_postal,
    lookup_postal_code_ca,
)


def test_is_ca_region_true_for_province_false_for_state():
    assert is_ca_region("on") is True
    assert is_ca_region("NY") is False
    assert is_ca_region("") is False


def test_detect_country_from_postal_classifies_us_zip_and_ca_postal():
    assert detect_country_from_postal("60614") == "US"
    assert detect_country_from_postal("60614-1234") == "US"
    assert detect_country_from_postal("M5V 2T6") == "CA"
    assert detect_country_from_postal("M5V") == "CA"
    assert detect_country_from_postal("not-a-code") is None


def test_lookup_postal_code_ca_parses_zippopotam_response(monkeypatch):
    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return json.dumps({
                "places": [{
                    "place name": "Toronto",
                    "state abbreviation": "ON",
                    "state": "Ontario",
                }]
            }).encode("utf-8")

    def _fake_urlopen(req, timeout=5):
        assert "api.zippopotam.us/ca/M5V" in req.full_url
        return _FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
    assert lookup_postal_code_ca("M5V 2T6") == ("Toronto", "ON", "Ontario")


def test_lookup_postal_code_ca_rejects_us_zip():
    assert lookup_postal_code_ca("60614") == (None, None, None)
