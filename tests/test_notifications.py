import json

from modules import notifications


def test_build_sheets_row_includes_html_export_metrics(monkeypatch):
    monkeypatch.setattr(notifications.st, "secrets", {"SOURCE_APP": "Frankenstein"}, raising=False)

    details = {
        "session_id": "sess-123",
        "session_start": "2026-08-25 10:00:00",
        "session_duration_min": 12.5,
        "data_source": "simulation",
        "population": 12345,
        "area_sq_mi": 42.0,
        "total_calls": 678,
        "city_calls": 678,
        "modeled_calls": 621,
        "daily_calls": 2,
        "fleet_capex": 2500000,
        "annual_savings": 350000,
        "break_even": "7.1 MONTHS",
        "avg_response_min": 1.9,
        "avg_time_saved_min": 2.7,
        "area_covered_pct": 74.2,
        "report_id": "report-abc",
        "active_drones": [
            {"type": "RESPONDER"},
            {"type": "RESPONDER"},
            {"type": "GUARDIAN"},
        ],
    }

    row = notifications._build_sheets_row(
        "Lincoln",
        "NE",
        "HTML",
        2,
        1,
        88.5,
        "Steven Beltran",
        "steven.beltran@brincdrones.com",
        details,
    )
    row_map = dict(zip(notifications.EXPORT_HEADERS, row))

    assert row_map["Export Type"] == "HTML"
    assert row_map["Responder Stations"] == 2
    assert row_map["Guardian Stations"] == 1
    assert row_map["Total Fleet Units"] == 3
    assert row_map["Fleet CapEx ($)"] == 2500000
    assert row_map["Annual Savings ($)"] == 350000
    assert row_map["Break Even"] == "7.1 MONTHS"
    assert row_map["Call Coverage (%)"] == 88.5
    assert row_map["Average Response (min)"] == 1.9
    assert row_map["Average Time Saved (min)"] == 2.7
    assert row_map["Area Covered (%)"] == 74.2
    assert row_map["City Calls"] == 678
    assert row_map["Modeled Calls"] == 621
    assert row_map["Daily Calls"] == 2
    assert row_map["Report ID"] == "report-abc"

    payload = json.loads(row_map["Export Details JSON"])
    assert payload["session_id"] == "sess-123"
    assert len(payload["active_drones"]) == 3
