import math

import pandas as pd

from modules.arrival_advantage import (
    available_baselines,
    build_arrival_summary,
    compute_arrival_advantage,
    normalize_arrival_fields,
)
from modules.cad_parser import aggressive_parse_calls


class _UploadedCsv:
    def __init__(self, name, text):
        self.name = name
        self._data = text.encode("utf-8")

    def getvalue(self):
        return self._data


def _calls_frame():
    return pd.DataFrame(
        {
            "CFS Date": ["2025-09-10", "2025-09-10", "2025-09-10"],
            "Day of Week": ["Wednesday", "Wednesday", "Wednesday"],
            "CFS Time": ["23:58:00", "10:00:00", "11:00:00"],
            "First Assigned Time": ["23:59:00", "10:01:00", "11:01:00"],
            "First Enroute Time": ["00:01:00", "10:02:00", "11:02:00"],
            "First Arrived Time": ["00:08:00", "10:10:00", ""],
            "Beat": ["4B", "2C", "FTML"],
            "lat": [35.0, 35.01, 36.0],
            "lon": [-81.0, -81.01, -82.0],
        }
    )


def test_normalize_arrival_fields_derives_districts_and_handles_midnight():
    result = normalize_arrival_fields(_calls_frame())

    assert result["District"].tolist() == ["4", "2", ""]
    assert result["response_from_cfs_min"].iloc[0] == 10.0
    assert result["response_from_assigned_min"].iloc[0] == 9.0
    assert result["response_from_enroute_min"].iloc[0] == 7.0
    assert pd.isna(result["response_from_cfs_min"].iloc[2])
    assert available_baselines(result) == [
        "CFS Time",
        "First Assigned Time",
        "First Enroute Time",
    ]


def test_compute_arrival_advantage_uses_fastest_in_range_drone():
    drones = [
        {
            "idx": 0,
            "type": "GUARDIAN",
            "name": "Fort Mill Test Site",
            "lat": 35.0,
            "lon": -81.0,
            "speed_mph": 60.0,
            "radius_m": 8 * 1609.344,
            "arrival_station_key": "GUARDIAN:0",
        }
    ]

    result = compute_arrival_advantage(_calls_frame(), drones, baseline="CFS Time")

    assert result["arrival_category"].iloc[0] == "Drone first"
    assert result["arrival_drone_wins"].iloc[0]
    assert result["arrival_station"].iloc[0] == "Fort Mill Test Site"
    assert result["arrival_drone_response_min"].iloc[0] == 0.0
    assert result["arrival_eyes_on_min"].iloc[0] == 10.0
    assert result["arrival_category"].iloc[2] == "Missing arrival"

    summary = build_arrival_summary(result)
    assert summary["total_calls"] == 3
    assert summary["calls_with_arrival"] == 2
    assert summary["calls_analyzed"] == 2
    assert summary["drone_wins"] == 2
    assert math.isclose(summary["arrival_completeness_pct"], 200 / 3)


def test_compute_arrival_advantage_marks_calls_outside_coverage():
    drones = [
        {
            "idx": 0,
            "type": "RESPONDER",
            "name": "Remote Site",
            "lat": 33.0,
            "lon": -79.0,
            "speed_mph": 30.0,
            "radius_m": 2 * 1609.344,
        }
    ]

    result = compute_arrival_advantage(_calls_frame().iloc[:1], drones)

    assert result["arrival_category"].iloc[0] == "Outside coverage"
    assert pd.isna(result["arrival_drone_response_min"].iloc[0])
    assert build_arrival_summary(result)["calls_analyzed"] == 0


def test_cad_parser_preserves_york_timing_and_beat_fields():
    source = _UploadedCsv(
        "york_calls.csv",
        "Beat,CFS Date,Day of Week,CFS Time,Call Type,First Assigned Time,First Enroute Time,First Arrived Time,Latitude,Longitude\n"
        "4B,2025-09-10,Wednesday,23:58:00,Domestic,23:59:00,00:01:00,00:08:00,35.0,-81.0\n"
        "2C,2025-09-10,Wednesday,10:00:00,Alarm,10:01:00,10:02:00,,35.1,-81.1\n",
    )

    result = aggressive_parse_calls([source])

    assert result["District"].tolist() == ["4", "2"]
    assert result["Beat"].tolist() == ["4B", "2C"]
    assert result["response_from_cfs_min"].iloc[0] == 10.0
    assert pd.isna(result["response_from_cfs_min"].iloc[1])
