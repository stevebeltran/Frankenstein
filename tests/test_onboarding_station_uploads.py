import io

import pandas as pd

from modules.onboarding import (
    infer_simulation_targets_from_station_file,
    load_simulation_custom_stations,
    resolve_demo_stations,
    restore_brinc_session,
)


class UploadedFile(io.BytesIO):
    def __init__(self, name, text):
        super().__init__(text.encode("utf-8"))
        self.name = name


STATIONS_CSV = """NAME,TYPE,ADDRESS,CAPACITY,NOTES,LAT,LON
"45 Patton Mountain Rd, Asheville, NC 28804",Police,,1,Imported from CalTopo marker,35.62361583,-82.53180946
"""


def test_path01_station_target_inference_uses_existing_coordinates():
    def forward_geocode(*_args):
        raise AssertionError("forward geocode should not be needed when lat/lon are present")

    def reverse_geocode_state(lat, lon):
        assert round(lat, 6) == 35.623616
        assert round(lon, 6) == -82.531809
        return "North Carolina", "Asheville"

    targets, notice = infer_simulation_targets_from_station_file(
        UploadedFile("stations.csv", STATIONS_CSV),
        forward_geocode,
        reverse_geocode_state,
        {"North Carolina": "NC"},
    )

    assert targets == [{"city": "Asheville", "state": "NC"}]
    assert notice == "Derived jurisdiction targets from the uploaded stations file."


def test_path01_custom_station_loader_accepts_address_in_name_with_blank_address():
    def forward_geocode(*_args):
        raise AssertionError("forward geocode should not be needed when lat/lon are present")

    stations_df, ungeocoded = load_simulation_custom_stations(
        UploadedFile("stations.csv", STATIONS_CSV),
        [{"city": "Asheville", "state": "NC"}],
        forward_geocode,
    )

    assert ungeocoded == []
    assert stations_df.to_dict("records") == [
        {
            "name": "45 Patton Mountain Rd, Asheville, NC 28804",
            "lat": 35.62361583,
            "lon": -82.53180946,
            "type": "Police",
            "address": "",
        }
    ]


def test_resolve_demo_stations_reports_uploaded_station_count():
    def forward_geocode(*_args):
        raise AssertionError("forward geocode should not be needed when lat/lon are present")

    stations_df, uploaded, notices, warnings = resolve_demo_stations(
        pd.DataFrame({"lat": [35.6], "lon": [-82.5]}),
        city_poly=None,
        sim_uploader=UploadedFile("stations.csv", STATIONS_CSV),
        active_targets=[{"city": "Asheville", "state": "NC"}],
        forward_geocode=forward_geocode,
        search_public_facility_candidates=None,
        generate_stations_from_calls=lambda *_args: (None, ""),
        generate_random_points_in_polygon=lambda *_args: [],
    )

    assert uploaded is True
    assert warnings == []
    assert notices == ["Loaded 1 station row from uploaded stations file."]
    assert len(stations_df) == 1


def test_restore_brinc_session_missing_responder_count_defaults_to_zero():
    session_state = {}

    restore_brinc_session(
        session_state,
        {
            "city": "Test City",
            "state": "TX",
            "calls_data": [{"lat": 1.0, "lon": 2.0}],
        },
    )

    assert session_state["k_resp"] == 0
