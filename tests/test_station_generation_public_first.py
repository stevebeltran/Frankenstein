import pandas as pd

from modules import stations


def test_make_random_stations_prefers_public_facilities(monkeypatch):
    calls = pd.DataFrame(
        {
            "lat": [35.10, 35.20, 35.30],
            "lon": [-78.10, -78.20, -78.30],
        }
    )

    monkeypatch.setattr(
        stations,
        "_derive_jurisdiction_lookup_contexts",
        lambda work, min_call_share=0.10: [{"city": "Raleigh", "state": "NC", "share": 0.62}],
    )
    monkeypatch.setattr(
        stations,
        "_build_context_station_rows",
        lambda *args, **kwargs: pd.DataFrame(
            [
                {
                    "name": "Police HQ",
                    "lat": 35.11,
                    "lon": -78.11,
                    "type": "Police",
                    "source": "PUBLIC_FACILITY",
                    "call_share": 0.62,
                },
                {
                    "name": "OSM Station",
                    "lat": 35.12,
                    "lon": -78.12,
                    "type": "Fire",
                    "source": "OSM",
                    "call_share": 0.62,
                },
                {
                    "name": "HIFLD Station",
                    "lat": 35.13,
                    "lon": -78.13,
                    "type": "Government",
                    "source": "HIFLD",
                    "call_share": 0.62,
                },
            ]
        ),
    )

    result = stations._make_random_stations(calls, n=3)

    assert list(result["source"]) == ["PUBLIC_FACILITY", "OSM", "HIFLD"]
    assert result.iloc[0]["name"] == "Police HQ"
