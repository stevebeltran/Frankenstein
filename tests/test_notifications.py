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
        "contract_value": 4200000,
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
    assert row_map["Contract Value ($)"] == 4200000
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


def test_log_to_sheets_uses_fallback_sheet_id_when_secret_missing(monkeypatch):
    monkeypatch.setattr(notifications.st, "secrets", {"gcp_service_account": {"project_id": "demo"}}, raising=False)

    captured = {}

    class FakeSheet:
        def row_values(self, row):
            return ["Timestamp", "Email", "Name", "Event"] if row == 1 else []

        def append_row(self, row):
            captured["row"] = row

    class FakeSpreadsheet:
        def open_by_key(self, sheet_id):
            captured["sheet_id"] = sheet_id
            return self

        def worksheet(self, name):
            captured.setdefault("worksheets", []).append(name)
            return FakeSheet()

    monkeypatch.setattr(notifications, "_upsert_user", lambda *args, **kwargs: None)
    monkeypatch.setattr(notifications.Credentials, "from_service_account_info", lambda info, scopes=None: object())
    monkeypatch.setattr(notifications.gspread, "authorize", lambda creds: FakeSpreadsheet())

    details = {
        "auth_timestamp": "2026-08-25 10:00:00",
        "session_id": "sess-456",
        "session_start": "2026-08-25 11:00:00",
        "session_duration_min": 7.0,
        "source_app": "Frankenstein",
        "rep_name": "Steven Beltran",
        "rep_email": "steven.beltran@brincdrones.com",
        "data_source": "simulation",
        "population": 1000,
        "area_sq_mi": 12.0,
        "total_calls": 50,
        "total_annual_calls": 50,
        "city_calls": 50,
        "modeled_calls": 45,
        "daily_calls": 1,
        "lat": 38.6,
        "lon": -90.2,
        "active_stations": 3,
        "total_stations": 7,
        "responder_stations": 1,
        "guardian_stations": 2,
        "call_coverage_pct": 66.7,
        "land_coverage_pct": 42.1,
        "station_count": 7,
        "fleet_capex": 1000000,
        "annual_savings": 125000,
        "break_even": "8.0 MONTHS",
        "avg_response_min": 2.0,
        "avg_time_saved_min": 1.5,
        "area_covered_pct": 66.7,
        "report_id": "report-xyz",
        "active_drones": [{"type": "RESPONDER"}],
    }

    notifications._log_to_sheets(
        "Richland County",
        "SC",
        "HTML",
        1,
        0,
        66.7,
        "Steven Beltran",
        "steven.beltran@brincdrones.com",
        details,
    )

    assert captured["sheet_id"] == notifications.DEFAULT_EXPORT_SHEET_ID
    assert captured["worksheets"][0] == "Reports"
    assert captured["row"][1] == "steven.beltran@brincdrones.com"
    assert captured["row"][2] == "Steven Beltran"
    assert captured["row"][3] == "REPORT"
    assert captured["row"][4] == "Frankenstein"
    assert captured["row"][5] == "Richland County"
    assert captured["row"][9] == "2026-08-25 10:00:00"
    assert captured["row"][10] == "sess-456"
    assert captured["row"][12] == "Steven Beltran"
    assert captured["row"][13] == "steven.beltran@brincdrones.com"
    assert captured["row"][15] == 50
    assert captured["row"][19] == 3
    assert captured["row"][20] == 7
    assert captured["row"][-1] == "HTML"


def test_log_login_to_sheets_records_source_app_and_run_location(monkeypatch):
    monkeypatch.setattr(
        notifications.st,
        "secrets",
        {"SOURCE_APP": "beta-optimizer", "gcp_service_account": {"project_id": "demo"}},
        raising=False,
    )

    captured = {}

    class FakeSheet:
        def row_values(self, row):
            return ["Timestamp", "Email", "Name", "Event"] if row == 1 else []

        def update(self, cell_range, values):
            captured["header_range"] = cell_range
            captured["headers"] = values[0]

        def append_row(self, row):
            captured["row"] = row

    class FakeSpreadsheet:
        def open_by_key(self, sheet_id):
            captured["sheet_id"] = sheet_id
            return self

        def worksheet(self, name):
            captured.setdefault("worksheets", []).append(name)
            return FakeSheet()

    notifications._LOGIN_WRITE_RECENT.clear()
    monkeypatch.setattr(notifications, "_should_skip_login_write", lambda email: False)
    monkeypatch.setattr(notifications.Credentials, "from_service_account_info", lambda info, scopes=None: object())
    monkeypatch.setattr(notifications.gspread, "authorize", lambda creds: FakeSpreadsheet())

    notifications._log_login_to_sheets(
        "steven.beltran@brincdrones.com",
        "Steven Beltran",
        city="Kansas City",
        state="MO",
        lat=39.0997,
        lon=-94.5786,
        details={
            "auth_timestamp": "2026-08-25 09:59:11",
            "source_app": "beta-optimizer",
            "session_id": "sess-789",
            "session_start": "2026-08-25 09:45:00",
            "rep_name": "Steven Beltran",
            "rep_email": "steven.beltran@brincdrones.com",
            "population": 12345,
            "total_annual_calls": 678,
            "data_source": "simulation",
            "sim_or_upload": "simulation",
            "total_calls": 678,
            "active_stations": 4,
            "total_stations": 8,
            "responder_stations": 2,
            "guardian_stations": 2,
            "call_coverage_pct": 66.7,
            "land_coverage_pct": 42.0,
            "station_count": 8,
        },
    )

    assert captured["worksheets"][0] == "Logins"
    assert "Users" in captured["worksheets"]
    assert captured["header_range"] == "A1:Z1"
    assert captured["headers"] == notifications.LOGIN_HEADERS
    assert captured["row"][1] == "steven.beltran@brincdrones.com"
    assert captured["row"][2] == "Steven Beltran"
    assert captured["row"][3] == "LOGIN"
    assert captured["row"][4] == "beta-optimizer"
    assert captured["row"][5] == "Kansas City"
    assert captured["row"][6] == "MO"
    assert captured["row"][7] == 39.0997
    assert captured["row"][8] == -94.5786
    assert captured["row"][9] == "2026-08-25 09:59:11"
    assert captured["row"][10] == "sess-789"
    assert captured["row"][12] == "Steven Beltran"
    assert captured["row"][13] == "steven.beltran@brincdrones.com"
    assert captured["row"][15] == 678
    assert captured["row"][19] == 4
    assert captured["row"][20] == 8
