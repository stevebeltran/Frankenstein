import json

import pandas as pd
from shapely.geometry import box

import modules.stations as stations


class _Response:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self._payload


def test_usgs_lookup_normalizes_fire_and_police_features(monkeypatch):
    requested_urls = []

    def fake_urlopen(request, timeout):
        requested_urls.append((request.full_url, timeout))
        if "/51/query" in request.full_url:
            return _Response({
                "features": [{
                    "attributes": {
                        "fcode": 74026,
                        "name": "Raleigh Fire Station 1",
                        "address": "220 S Dawson St",
                        "city": "Raleigh",
                        "state": "NC",
                        "zipcode": "27601",
                    },
                    "geometry": {"x": -78.6431, "y": 35.7766},
                }]
            })
        return _Response({
            "features": [{
                "attributes": {
                    "fcode": 74034,
                    "name": "Raleigh Police Department",
                    "address": "6716 Six Forks Rd",
                    "city": "Raleigh",
                    "state": "NC",
                    "zipcode": "27615",
                },
                "geometry": {"x": -78.6389, "y": 35.8702},
            }]
        })

    monkeypatch.setattr(stations.urllib.request, "urlopen", fake_urlopen)

    rows, note = stations._fetch_usgs_nsd_stations(
        35.69, -78.87, 35.98, -78.50
    )

    assert note == "Found 2 stations from USGS National Structures Dataset."
    assert rows == [
        {
            "name": "Raleigh Fire Station 1",
            "address": "220 S Dawson St, Raleigh, NC 27601",
            "lat": 35.7766,
            "lon": -78.6431,
            "type": "Fire",
            "source": "USGS_NSD",
        },
        {
            "name": "Raleigh Police Department",
            "address": "6716 Six Forks Rd, Raleigh, NC 27615",
            "lat": 35.8702,
            "lon": -78.6389,
            "type": "Police",
            "source": "USGS_NSD",
        },
    ]
    assert len(requested_urls) == 2
    assert all(timeout == 8 for _, timeout in requested_urls)
    assert all("geometry=-78.87%2C35.69%2C-78.5%2C35.98" in url for url, _ in requested_urls)
    assert any("%2F51%2Fquery" not in url and "/51/query" in url for url, _ in requested_urls)


def test_usgs_lookup_rejects_wrong_fcodes_and_bad_coordinates(monkeypatch):
    def fake_urlopen(request, timeout):
        del timeout
        expected = 74026 if "/51/query" in request.full_url else 74034
        return _Response({
            "features": [
                {
                    "attributes": {"fcode": expected, "name": "Valid"},
                    "geometry": {"x": -78.64, "y": 35.78},
                },
                {
                    "attributes": {"fcode": 74036, "name": "Prison"},
                    "geometry": {"x": -78.65, "y": 35.79},
                },
                {
                    "attributes": {"fcode": expected, "name": "Bad coordinate"},
                    "geometry": {"x": None, "y": 35.80},
                },
            ]
        })

    monkeypatch.setattr(stations.urllib.request, "urlopen", fake_urlopen)

    rows, _note = stations._fetch_usgs_nsd_stations(35.69, -78.87, 35.98, -78.50)

    assert [row["name"] for row in rows] == ["Valid", "Valid"]
    assert [row["type"] for row in rows] == ["Fire", "Police"]


def test_usgs_lookup_fails_open_when_service_is_unavailable(monkeypatch):
    def fail(*_args, **_kwargs):
        raise TimeoutError("USGS unavailable")

    monkeypatch.setattr(stations.urllib.request, "urlopen", fail)

    rows, note = stations._fetch_usgs_nsd_stations(35.69, -78.87, 35.98, -78.50)

    assert rows is None
    assert note == "USGS unavailable"


def test_station_merge_prefers_usgs_for_colocated_same_type():
    usgs = [{
        "name": "Raleigh Fire Station 1",
        "lat": 35.77661,
        "lon": -78.64311,
        "type": "Fire",
        "source": "USGS_NSD",
        "address": "220 S Dawson St",
    }]
    osm = [{
        "name": "Fire Station 1",
        "lat": 35.77659,
        "lon": -78.64309,
        "type": "Fire",
        "source": "OSM",
    }]
    police_same_site = [{
        "name": "Public Safety Office",
        "lat": 35.77660,
        "lon": -78.64310,
        "type": "Police",
        "source": "HIFLD",
    }]

    merged = stations._merge_station_candidate_rows(usgs, osm, police_same_site)

    assert merged[["name", "type", "source"]].to_dict("records") == [
        {"name": "Raleigh Fire Station 1", "type": "Fire", "source": "USGS_NSD"},
        {"name": "Public Safety Office", "type": "Police", "source": "HIFLD"},
    ]


def test_call_density_fallback_does_not_claim_real_facility_identity():
    calls = pd.DataFrame({
        "lat": [35.77, 35.78, 35.79, 35.80],
        "lon": [-78.64, -78.63, -78.62, -78.61],
    })

    generated = stations._make_random_stations(calls, n=2)

    assert generated["source"].tolist() == ["CALL_DENSITY", "CALL_DENSITY"]
    assert all(name.startswith("Proposed Call-Density Site") for name in generated["name"])
    assert set(generated["type"]) == {"Proposed"}


def test_generated_candidates_are_strictly_clipped_to_selected_boundary():
    candidates = pd.DataFrame({
        "name": ["Inside", "Outside"],
        "lat": [35.78, 36.20],
        "lon": [-78.64, -78.64],
        "type": ["Fire", "Fire"],
        "source": ["USGS_NSD", "USGS_NSD"],
    })

    filtered = stations._filter_station_candidates_to_boundary(
        candidates,
        box(-78.70, 35.70, -78.60, 35.90),
        32617,
    )

    assert filtered["name"].tolist() == ["Inside"]
