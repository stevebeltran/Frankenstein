"""
Email and Google Sheets notification system for BRINC app.
"""

import datetime
import json
import smtplib
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import gspread
from google.oauth2.service_account import Credentials

from modules.versioning import (
    __version__,
    __build_revision__,
    __build_datetime__,
    __build_line_count__,
)


def _build_details_html(details):
    """Shared HTML block for deployment details used in email notifications."""
    if not details:
        return ""
    drone_list = "".join([
        f"<li><b>{d['name']}</b> ({d['type']}) @ {d['lat']:.4f}, {d['lon']:.4f}</li>"
        for d in details.get('active_drones', [])
    ])
    pop   = details.get('population', 0)
    calls = details.get('total_calls', 0)
    daily = details.get('daily_calls', 0)
    area  = details.get('area_sq_mi', 0)
    be    = details.get('break_even', 'N/A')
    src   = details.get('data_source', '—')
    sid   = details.get('session_id', '—')
    stime = details.get('session_start', '—')
    dur   = details.get('session_duration_min', '—')
    avg_t = details.get('avg_response_min', 0)
    time_saved = details.get('avg_time_saved_min', 0)
    area_cov = details.get('area_covered_pct', 0)
    return f"""
    <div style="margin-top:20px; padding-top:20px; border-top:1px solid #f0f0f0;">
        <h4 style="color:#555; margin-bottom:10px;">Session Info</h4>
        <table style="width:100%; border-collapse:collapse; font-size:12px; margin-bottom:15px;">
            <tr><td style="padding:4px; color:#888; width:50%;">Session ID</td><td style="padding:4px;">{sid}</td></tr>
            <tr><td style="padding:4px; color:#888;">Session Start</td><td style="padding:4px;">{stime}</td></tr>
            <tr><td style="padding:4px; color:#888;">Session Duration</td><td style="padding:4px;">{dur} min</td></tr>
            <tr><td style="padding:4px; color:#888;">Data Source</td><td style="padding:4px;">{src}</td></tr>
        </table>
        <h4 style="color:#555; margin-bottom:10px;">Jurisdiction</h4>
        <table style="width:100%; border-collapse:collapse; font-size:12px; margin-bottom:15px;">
            <tr><td style="padding:4px; color:#888; width:50%;">Population</td><td style="padding:4px;">{pop:,}</td></tr>
            <tr><td style="padding:4px; color:#888;">Total Annual Calls</td><td style="padding:4px;">{calls:,}</td></tr>
            <tr><td style="padding:4px; color:#888;">Daily Calls</td><td style="padding:4px;">{daily:,}</td></tr>
            <tr><td style="padding:4px; color:#888;">Coverage Area</td><td style="padding:4px;">{area:,} sq mi</td></tr>
        </table>
        <h4 style="color:#555; margin-bottom:10px;">Deployment Settings</h4>
        <table style="width:100%; border-collapse:collapse; font-size:12px; margin-bottom:15px;">
            <tr><td style="padding:4px; color:#888; width:50%;">Strategy</td><td style="padding:4px;">{details.get('opt_strategy', '')}</td></tr>
            <tr><td style="padding:4px; color:#888;">Incremental Build</td><td style="padding:4px;">{details.get('incremental_build', False)}</td></tr>
            <tr><td style="padding:4px; color:#888;">Allow Overlap</td><td style="padding:4px;">{details.get('allow_redundancy', False)}</td></tr>
            <tr><td style="padding:4px; color:#888;">DFR Dispatch Rate</td><td style="padding:4px;">{details.get('dfr_rate', 0)}%</td></tr>
            <tr><td style="padding:4px; color:#888;">Deflection Rate</td><td style="padding:4px;">{details.get('deflect_rate', 0)}%</td></tr>
            <tr><td style="padding:4px; color:#888;">Total CapEx</td><td style="padding:4px;">${details.get('fleet_capex', 0):,.0f}</td></tr>
            <tr><td style="padding:4px; color:#888;">Annual Savings</td><td style="padding:4px;">${details.get('annual_savings', 0):,.0f}</td></tr>
            <tr><td style="padding:4px; color:#888;">Thermal Upside</td><td style="padding:4px;">${details.get('thermal_savings', 0):,.0f}</td></tr>
            <tr><td style="padding:4px; color:#888;">K-9 Upside</td><td style="padding:4px;">${details.get('k9_savings', 0):,.0f}</td></tr>
            <tr><td style="padding:4px; color:#888;">Break-Even</td><td style="padding:4px;">{be}</td></tr>
            <tr><td style="padding:4px; color:#888;">Avg Response Time</td><td style="padding:4px;">{avg_t:.1f} min</td></tr>
            <tr><td style="padding:4px; color:#888;">Time Saved vs Patrol</td><td style="padding:4px;">{time_saved:.1f} min</td></tr>
            <tr><td style="padding:4px; color:#888;">Geographic Coverage</td><td style="padding:4px;">{area_cov:.1f}%</td></tr>
        </table>
        <h4 style="color:#555; margin-bottom:10px;">Active Drones Placed</h4>
        <ul style="font-size:12px; color:#444; padding-left:20px;">{drone_list}</ul>
    </div>
    """


def _build_sheets_row(city, state, event_type, k_resp, k_guard, coverage, name, email, details=None):
    """Build the flat list of values for a Google Sheets row — single source of truth."""
    d = details or {}
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    session_start = d.get('session_start', now)
    dur = d.get('session_duration_min', '')
    try:
        if dur == '':
            start_dt = datetime.datetime.strptime(session_start, "%Y-%m-%d %H:%M:%S")
            dur = round((datetime.datetime.now() - start_dt).total_seconds() / 60, 1)
    except Exception:
        dur = ''
    fm = d.get('file_meta', {})
    return [
        # ── Identity ────────────────────────────────────────────────────────
        now,                                    # A: Timestamp
        d.get('session_id', ''),               # B: Session ID
        session_start,                          # C: Session Start
        dur,                                    # D: Session Duration (min)
        d.get('data_source', ''),              # E: Data Source
        # ── Who ─────────────────────────────────────────────────────────────
        name,                                   # F: BRINC Rep Name
        email,                                  # G: BRINC Rep Email
        # ── Where (user-selected) ────────────────────────────────────────────
        city,                                   # H: City (user-selected)
        state,                                  # I: State (user-selected)
        d.get('population', ''),               # N: Population
        d.get('area_sq_mi', ''),               # O: Area (sq mi)
        # ── Where (file-inferred) ────────────────────────────────────────────
        fm.get('file_inferred_city', ''),      # P: City inferred from uploaded file
        fm.get('file_inferred_state', ''),     # Q: State inferred from uploaded file
        d.get('city_confirmed_match', ''),     # R: File city matched user selection (True/False)
        d.get('multi_city_targets', ''),       # S: All target cities JSON
        d.get('num_cities_targeted', ''),      # T: Count of cities analyzed
        # ── Calls ───────────────────────────────────────────────────────────
        d.get('total_calls', ''),              # U: Total Annual Calls
        d.get('daily_calls', ''),              # V: Daily Calls
        d.get('calls_per_capita', ''),         # W: Calls per Capita
        # ── Fleet ───────────────────────────────────────────────────────────
        event_type,                             # X: Event Type
        k_resp,                                 # Y: Responders
        k_guard,                                # Z: Guardians
        round(coverage, 1) if coverage else '', # AA: Call Coverage %
        d.get('area_covered_pct', ''),         # AB: Area Coverage %
        d.get('avg_response_min', ''),         # AC: Avg Response (min)
        d.get('avg_time_saved_min', ''),       # AD: Time Saved vs Patrol (min)
        # ── Financials ──────────────────────────────────────────────────────
        d.get('fleet_capex', ''),              # AE: Fleet CapEx
        d.get('annual_savings', ''),           # AF: Annual Savings
        d.get('break_even', ''),               # AG: Break-Even
        # ── Settings ────────────────────────────────────────────────────────
        d.get('opt_strategy', ''),             # AH: Opt Strategy
        d.get('dfr_rate', ''),                 # AI: DFR Rate %
        d.get('deflect_rate', ''),             # AJ: Deflection Rate %
        d.get('incremental_build', ''),        # AK: Incremental Build
        d.get('allow_redundancy', ''),         # AL: Allow Overlap
        d.get('r_resp_radius', ''),            # AM: Responder Radius (mi)
        d.get('r_guard_radius', ''),           # AN: Guardian Radius (mi)
        d.get('estimated_pop_input', ''),      # AO: Population input by user
        # ── File Data Matrix ─────────────────────────────────────────────────
        fm.get('uploaded_filename', ''),       # AP: Uploaded filename(s)
        fm.get('file_row_count', ''),          # AQ: Raw file row count
        fm.get('file_col_count', ''),          # AR: Column count
        fm.get('file_col_names', ''),          # AS: Column names JSON
        fm.get('file_date_range_start', ''),   # AT: Earliest date in data
        fm.get('file_date_range_end', ''),     # AU: Latest date in data
        fm.get('file_date_span_days', ''),     # AV: Days of history in file
        fm.get('file_null_rate_pct', ''),      # AW: Null rate % across key fields
        fm.get('file_has_lat_lon', ''),        # AX: Lat/lon detected (True/False)
        fm.get('file_has_priority', ''),       # AY: Priority col detected (True/False)
        fm.get('call_type_breakdown', ''),     # AZ: Top call types JSON
        fm.get('priority_distribution', ''),   # BA: Priority counts JSON
        fm.get('peak_hour', ''),               # BB: Peak hour of day (0-23)
        fm.get('peak_day_of_week', ''),        # BC: Peak day of week (0=Mon)
        fm.get('peak_month', ''),              # BD: Peak month (1-12)
        # ── User Interaction Signals ─────────────────────────────────────────
        d.get('boundary_kind', ''),            # BE: Boundary type (place/county)
        d.get('boundary_source_path', ''),     # BF: Shapefile path used
        d.get('sim_or_upload', ''),            # BG: simulation vs cad_upload
        d.get('onboarding_completed', ''),     # BH: Onboarding finished (True/False)
        d.get('demo_mode_used', ''),           # BI: Demo city loaded (True/False)
        d.get('export_type_sequence', ''),     # BJ: Ordered export clicks (JSON list)
        d.get('total_exports_in_session', ''),# BK: Total export clicks
        d.get('map_viewed', ''),               # BL: Map rendered this session
        # ── Drones detail (JSON) ─────────────────────────────────────────────
        json.dumps([{"name": dr.get("name"), "type": dr.get("type"),
                     "lat": dr.get("lat"), "lon": dr.get("lon"),
                     "avg_time_min": dr.get("avg_time_min"),
                     "faa_ceiling": dr.get("faa_ceiling"),
                     "annual_savings": dr.get("annual_savings")}
                    for dr in d.get('active_drones', [])]),  # BM: Drone JSON
        d.get('app_version', __version__),          # BN: App Version
        d.get('app_revision', __build_revision__),  # BO: App Revision
        d.get('build_datetime', __build_datetime__),# BP: Build Datetime
        d.get('app_line_count', __build_line_count__), # BQ: app.py line count
    ]


def _notify_email(city, state, file_type, k_resp, k_guard, coverage, name, email, details=None):
    """Send email notification via Gmail."""
    try:
        gmail_address  = st.secrets.get("GMAIL_ADDRESS", "")
        app_password   = st.secrets.get("GMAIL_APP_PASSWORD", "")
        notify_address = st.secrets.get("NOTIFY_EMAIL", gmail_address)
        if not gmail_address or not app_password:
            return
        emoji = {"HTML": "📄", "KML": "🌏", "BRINC": "💾", "MAP_BUILD": "🗺️"}.get(file_type, "📥")
        subject = f"{emoji} BRINC {file_type.replace('_',' ').title()} — {city}, {state}"
        details_html = _build_details_html(details)
        d = details or {}
        pop  = d.get('population', 0)
        body = f"""
        <html><body style="font-family:Arial,sans-serif;color:#333;padding:20px;">
        <div style="max-width:560px;margin:0 auto;border:1px solid #ddd;border-radius:8px;overflow:hidden;">
            <div style="background:#000;padding:16px 20px;border-bottom:3px solid #00D2FF;">
                <span style="color:#00D2FF;font-size:18px;font-weight:900;letter-spacing:2px;">BRINC</span>
                <span style="color:#888;font-size:12px;margin-left:8px;">{file_type.replace('_',' ').title()} Notification</span>
            </div>
            <div style="padding:20px;">
                <table style="width:100%;border-collapse:collapse;font-size:14px;">
                    <tr style="border-bottom:1px solid #f0f0f0;"><td style="padding:8px 4px;color:#888;width:40%;">Event</td><td style="padding:8px 4px;font-weight:bold;">{emoji} {file_type.replace('_',' ').title()}</td></tr>
                    <tr style="border-bottom:1px solid #f0f0f0;"><td style="padding:8px 4px;color:#888;">Jurisdiction</td><td style="padding:8px 4px;font-weight:bold;">{city}, {state}</td></tr>
                    <tr style="border-bottom:1px solid #f0f0f0;"><td style="padding:8px 4px;color:#888;">Population</td><td style="padding:8px 4px;">{pop:,}</td></tr>
                    <tr style="border-bottom:1px solid #f0f0f0;"><td style="padding:8px 4px;color:#888;">Fleet</td><td style="padding:8px 4px;">{k_resp} Responder · {k_guard} Guardian</td></tr>
                    <tr style="border-bottom:1px solid #f0f0f0;"><td style="padding:8px 4px;color:#888;">Call Coverage</td><td style="padding:8px 4px;">{coverage:.1f}%</td></tr>
                    <tr style="border-bottom:1px solid #f0f0f0;"><td style="padding:8px 4px;color:#888;">BRINC Rep</td><td style="padding:8px 4px;">{name if name else '—'}</td></tr>
                    <tr><td style="padding:8px 4px;color:#888;">Rep Email</td><td style="padding:8px 4px;">{f'<a href="mailto:{email}">{email}</a>' if email else '—'}</td></tr>
                </table>
                {details_html}
                <div style="margin-top:16px;font-size:11px;color:#bbb;">{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} UTC</div>
            </div>
        </div>
        <div class="doc-version">v {__version__}</div>
</body></html>
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"], msg["From"], msg["To"] = subject, gmail_address, notify_address
        msg.attach(MIMEText(body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=8) as server:
            server.login(gmail_address, app_password)
            server.sendmail(gmail_address, notify_address, msg.as_string())
    except:
        pass


def _ensure_sheet_headers(sheet):
    """Best-effort header sync for the main export log worksheet."""
    _headers = [
        "Timestamp", "Session ID", "Session Start", "Session Duration (min)", "Data Source",
        "BRINC Rep Name", "BRINC Rep Email", "City", "State", "Population", "Area (sq mi)",
        "File Inferred City", "File Inferred State", "City Confirmed Match", "Multi City Targets",
        "Num Cities Targeted", "Total Annual Calls", "Daily Calls", "Calls per Capita",
        "Event Type", "Responders", "Guardians", "Call Coverage %", "Area Coverage %",
        "Avg Response (min)", "Time Saved vs Patrol (min)", "Fleet CapEx", "Annual Savings",
        "Break-Even", "Opt Strategy", "DFR Rate %", "Deflection Rate %", "Incremental Build",
        "Allow Overlap", "Responder Radius (mi)", "Guardian Radius (mi)", "Population Input",
        "Uploaded Filename", "File Row Count", "File Col Count", "File Col Names",
        "File Date Range Start", "File Date Range End", "File Date Span Days", "File Null Rate %",
        "File Has Lat Lon", "File Has Priority", "Call Type Breakdown", "Priority Distribution",
        "Peak Hour", "Peak Day Of Week", "Peak Month", "Boundary Kind", "Boundary Source Path",
        "Simulation Or Upload", "Onboarding Completed", "Demo Mode Used", "Export Type Sequence",
        "Total Exports In Session", "Map Viewed", "Active Drones JSON",
        "App Version", "App Revision", "Build Datetime", "App Line Count",
    ]
    try:
        _first_row = sheet.row_values(1)
        if not _first_row:
            sheet.update("A1:BQ1", [_headers])
            return
        if _first_row[0] == "Timestamp" and len(_first_row) < len(_headers):
            sheet.update("A1:BQ1", [_headers])
    except Exception:
        pass


def _log_to_sheets(city, state, file_type, k_resp, k_guard, coverage, name, email, details=None):
    """Log deployment to Google Sheets."""
    try:
        sheet_id = st.secrets.get("GOOGLE_SHEET_ID", "")
        creds_dict = st.secrets.get("gcp_service_account", {})
        if not sheet_id or not creds_dict:
            return
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(dict(creds_dict), scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(sheet_id).sheet1
        _ensure_sheet_headers(sheet)
        row = _build_sheets_row(city, state, file_type, k_resp, k_guard, coverage, name, email, details)
        sheet.append_row(row)
    except:
        pass


def _log_login_to_sheets(email, name):
    """Log user login to Google Sheets (separate LOGIN sheet)."""
    try:
        sheet_id = st.secrets.get("GOOGLE_SHEET_ID", "")
        creds_dict = st.secrets.get("gcp_service_account", {})
        if not sheet_id or not creds_dict:
            return
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(dict(creds_dict), scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(sheet_id)

        # Try to get or create a "Logins" sheet
        try:
            sheet = spreadsheet.worksheet("Logins")
        except gspread.exceptions.WorksheetNotFound:
            sheet = spreadsheet.add_worksheet(title="Logins", rows=1000, cols=10)
            # Add headers if new sheet
            sheet.append_row(["Timestamp", "Email", "Name", "Event"])

        # Append login row
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, email, name, "LOGIN"])
    except:
        pass
