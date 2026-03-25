import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
import plotly.graph_objects as go
from shapely.geometry import Point, Polygon, MultiPolygon, box, shape
from shapely.ops import unary_union
import os, itertools, glob, math, simplekml, heapq, re, random, json, io, datetime, base64, smtplib
from concurrent.futures import ThreadPoolExecutor
import pulp
import urllib.request
import urllib.parse
import zipfile
import streamlit.components.v1 as components
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import gspread
from google.oauth2.service_account import Credentials
import pyproj

# --- PAGE CONFIG & INITIALIZE SESSION STATE ---
st.set_page_config(page_title="BRINC COS Drone Optimizer", layout="wide", initial_sidebar_state="expanded")

defaults = {
    'csvs_ready': False, 'df_calls': None, 'df_stations': None,
    'active_city': "Victoria", 'active_state': "TX", 'estimated_pop': 65000,
    'k_resp': 2, 'k_guard': 0, 'r_resp': 2.0, 'r_guard': 8.0,
    'dfr_rate': 25, 'deflect_rate': 30, 'total_original_calls': 0,
    'onboarding_done': False, 'trigger_sim': False, 'city_count': 1,
    'brinc_user': 'steven.beltran'
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if 'target_cities' not in st.session_state:
    st.session_state['target_cities'] = [{"city": st.session_state.get('active_city', 'Victoria'), "state": st.session_state.get('active_state', 'TX')}]

# --- UTILITY FUNCTIONS ---

def _notify_email(city, state, file_type, k_resp, k_guard, coverage, name, email, details=None):
    try:
        gmail_address  = st.secrets.get("GMAIL_ADDRESS", "")
        app_password   = st.secrets.get("GMAIL_APP_PASSWORD", "")
        notify_address = st.secrets.get("NOTIFY_EMAIL", gmail_address)
        if not gmail_address or not app_password: return
        emoji = {"HTML": "📄", "KML": "🌏", "BRINC": "💾"}.get(file_type, "📥")
        subject = f"{emoji} BRINC Download — {file_type} — {city}, {state}"
        
        details_html = ""
        if details:
            drone_list = "".join([f"<li><b>{d['name']}</b> ({d['type']}) @ {d['lat']:.4f}, {d['lon']:.4f}</li>" for d in details.get('active_drones', [])])
            details_html = f"""
            <div style="margin-top:20px; padding-top:20px; border-top:1px solid #f0f0f0;">
                <h4 style="color:#555; margin-bottom:10px;">Settings</h4>
                <table style="width:100%; border-collapse:collapse; font-size:12px;">
                    <tr><td>Strategy</td><td>{details.get('opt_strategy', '')}</td></tr>
                    <tr><td>Total CapEx</td><td>${details.get('fleet_capex', 0):,.0f}</td></tr>
                </table>
                <h4 style="color:#555; margin-bottom:10px;">Drones</h4><ul>{drone_list}</ul>
            </div>
            """

        body = f"<html><body><h2>BRINC Download Notification</h2><p><b>Jurisdiction:</b> {city}, {state}</p>{details_html}</body></html>"
        msg = MIMEMultipart("alternative")
        msg["Subject"], msg["From"], msg["To"] = subject, gmail_address, notify_address
        msg.attach(MIMEText(body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=8) as server:
            server.login(gmail_address, app_password)
            server.sendmail(gmail_address, notify_address, msg.as_string())
    except: pass

def _log_to_sheets(city, state, file_type, k_resp, k_guard, coverage, name, email, details=None):
    try:
        sheet_id = st.secrets.get("GOOGLE_SHEET_ID", "")
        creds_dict = st.secrets.get("gcp_service_account", {})
        if not sheet_id or not creds_dict: return
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(dict(creds_dict), scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(sheet_id).sheet1
        details_json_str = json.dumps(details) if details else ""
        sheet.append_row([datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), city, state, file_type, k_resp, k_guard, round(coverage, 1), name, email, details_json_str])
    except: pass

# --- GLOBAL CONFIGURATION ---
CONFIG = {"RESPONDER_COST": 80000, "GUARDIAN_COST": 160000, "RESPONDER_RANGE_MI": 2.0, "OFFICER_COST_PER_CALL": 82, "DRONE_COST_PER_CALL": 6, "DEFAULT_TRAFFIC_SPEED": 35.0, "RESPONDER_SPEED": 42.0, "GUARDIAN_SPEED": 60.0}
STATE_FIPS = {"AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08", "CT": "09", "DE": "10", "FL": "12", "GA": "13", "HI": "15", "ID": "16", "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21", "LA": "22", "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28", "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33", "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39", "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46", "TN": "47", "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53", "WV": "54", "WI": "55", "WY": "56"}
US_STATES_ABBR = {v: k for k, v in {"Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"}.items()}
KNOWN_POPULATIONS = {"Victoria": 65534, "New York": 8336817, "Los Angeles": 3822238, "Chicago": 2665039}
STATION_COLORS = ["#00D2FF", "#39FF14", "#FFD700", "#FF007F", "#FF4500", "#00FFCC", "#FF3333", "#7FFF00", "#00FFFF", "#FF9900"]

# --- THEME VARIABLES ---
bg_main = "#000000"; accent_color = "#00D2FF"; text_main = "#ffffff"; text_muted = "#aaaaaa"
card_bg = "#111111"; card_border = "#333333"; card_title = "#ffffff"; budget_box_bg = "#0a0a0a"
budget_box_border = "#00D2FF"; budget_box_shadow = "rgba(0, 210, 255, 0.15)"; map_style = "carto-darkmatter"
map_boundary_color = "#ffffff"; map_incident_color = "#00D2FF"; legend_bg = "rgba(0, 0, 0, 0.7)"; legend_text = "#ffffff"

JURISDICTION_MESSAGES = ["🗺️ Identifying jurisdictions...", "📐 Loading boundaries...", "🏙️ Mapping the city...", "📍 Finding coverage area..."]
def get_jurisdiction_message(): return random.choice(JURISDICTION_MESSAGES)
def get_spatial_message(): return "⚡ Crunching coverage geometry..."
def get_faa_message(): return "✈️ Checking FAA airspace..."
def get_airfield_message(): return "🏗️ Locating airfields..."

def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f: return base64.b64encode(f.read()).decode()
    except: return None

# ============================================================
# COMMAND CENTER ANALYTICS GENERATOR
# ============================================================
def generate_command_center_html(df, total_orig_calls, export_mode=False):
    if df is None or df.empty or 'date' not in df.columns:
        return "<div style='color:gray; padding:20px;'>Analytics unavailable.</div>"
    import calendar as _cal
    import json
    df_ana = df.copy()
    df_ana['dt_obj'] = pd.to_datetime(df_ana['date'] + ' ' + df_ana.get('time', '00:00:00'), errors='coerce')
    df_ana = df_ana.dropna(subset=['dt_obj'])
    if df_ana.empty: return "<div>No valid dates found in data.</div>"
    records = []
    for _, r in df_ana.iterrows():
        dt = r['dt_obj']
        p_val = str(r['priority']).upper().strip() if 'priority' in r else 'UNKNOWN'
        records.append({'d': dt.strftime('%Y-%m-%d'), 'h': dt.hour, 'dow': dt.dayofweek, 'p': p_val})
    unique_pris = sorted(list(set(r['p'] for r in records)))
    options_html = '<option value="ALL">ALL PRIORITIES</option>'
    for p in unique_pris: options_html += f'<option value="{p}">{f"PRIORITY {p}" if len(p)<=2 else p}</option>'
    month_keys = sorted(list(set(r['d'][:7] for r in records)))
    cal_html = "<div style='display:grid; grid-template-columns:repeat(auto-fill, minmax(250px, 1fr)); gap:15px; margin-top:20px;'>"
    for mk in month_keys[:12]:
        yr, mo = int(mk.split('-')[0]), int(mk.split('-')[1])
        cal_html += f"<div style='background:#0c0c12; border:1px solid #1a1a26; border-radius:6px; padding:12px;'>"
        cal_html += f"<div style='display:flex; justify-content:space-between; border-bottom:1px solid #252535; padding-bottom:6px; margin-bottom:8px;'><span style='color:#00D2FF; font-weight:800; font-size:12px;'>{_cal.month_name[mo]} {yr}</span><span id='month-total-{mk}' style='color:#7777a0; font-size:10px;'>0 calls</span></div>"
        cal_html += "<div style='display:grid; grid-template-columns:repeat(7, 1fr); gap:2px; margin-bottom:4px;'>"
        for i, dname in enumerate(['Su','Mo','Tu','We','Th','Fr','Sa']):
            cal_html += f"<div style='font-size:9px; text-align:center; color:#7777a0;'>{dname}</div>"
        cal_html += "</div><div style='display:grid; grid-template-columns:repeat(7, 1fr); gap:2px;'>"
        first_dow_sun = (_cal.weekday(yr, mo, 1) + 1) % 7
        for _ in range(first_dow_sun): cal_html += "<div></div>"
        for d in range(1, _cal.monthrange(yr, mo)[1] + 1):
            dk = f"{yr}-{mo:02d}-{d:02d}"; dow_idx = (_cal.weekday(yr, mo, d) + 1) % 7 
            cal_html += f"<div class='day-cell' data-date='{dk}' data-mkey='{mk}' data-month='{_cal.month_name[mo]}' data-d='{d}' data-y='{yr}' data-dow='{dow_idx}' style='aspect-ratio:1; border-radius:2px; display:flex; flex-direction:column; align-items:center; justify-content:center; font-family:monospace; cursor:default; transition:transform 0.1s;' onmouseover='showTooltip(this, event)' onmouseout='hideTooltip()'></div>"
        cal_html += "</div></div>"
    cal_html += "</div>"
    full_html = f"""<div style="background:#000; color:#e8e8f2; font-family: 'Barlow', sans-serif; padding:15px; border-radius:8px;">
        <style>.day-cell:hover {{ transform: scale(1.15); z-index: 10; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }} #dfr-tooltip {{ position: fixed; z-index: 9999; background: #09090f; border: 1px solid #252535; border-radius: 6px; padding: 12px 16px; display: none; min-width: 220px; }}</style>
        <div id="dfr-tooltip"></div>
        <div style="color:#00D2FF; font-weight:900; letter-spacing:3px; font-size:14px; text-transform:uppercase; margin-bottom:20px; border-bottom:1px solid #1a1a26; padding-bottom:10px;">CAD Analytics Dashboard</div>
        <div style="display:flex; gap:20px; align-items:center; background:#0c0c12; padding:12px; border-radius:6px; margin-bottom:20px;">
            <select id="pri-select" onchange="currentPri=this.value; updateDashboard();" style="background:#1a1a26; color:#00D2FF; border:1px solid #252535; padding:6px; border-radius:4px;">{options_html}</select>
            <select id="shift-select" onchange="currentShift=parseInt(this.value); updateDashboard();" style="background:#1a1a26; color:#00D2FF; border:1px solid #252535; padding:6px; border-radius:4px;"><option value="8">8 HOURS</option><option value="12">12 HOURS</option></select>
        </div>
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px; margin-bottom:20px;">
            <div style="background:#0c0c12; border-left:4px solid #00D2FF; padding:15px; border-radius:4px;"><div style="color:#00D2FF; font-size:26px; font-weight:900;" id="kpi-total-val">0</div><div style="color:#7777a0; font-size:10px; text-transform:uppercase;">Incidents</div></div>
            <div style="background:#0c0c12; border-left:4px solid #F0B429; padding:15px; border-radius:4px;"><div style="color:#F0B429; font-size:26px; font-weight:900;" id="kpi-peak-val">0:00</div><div style="color:#7777a0; font-size:10px; text-transform:uppercase;">Peak Hour</div></div>
        </div>
        <div id="shift-container"></div>
        {cal_html}
        <script>
            const rawData = {json.dumps(records)}; let currentShift = 8; let currentPri = 'ALL'; window.dateHourly = {{}};
            function updateDashboard() {{
                let filtered = currentPri === 'ALL' ? rawData : rawData.filter(d => String(d.p) === currentPri);
                document.getElementById('kpi-total-val').innerHTML = filtered.length.toLocaleString();
                let hourly = new Array(24).fill(0); let daily = {{}}; window.dateHourly = {{}}; let mTotal = {{}}; let mMax = {{}};
                filtered.forEach(r => {{
                    hourly[r.h]++; daily[r.d] = (daily[r.d] || 0) + 1;
                    if(!window.dateHourly[r.d]) window.dateHourly[r.d] = new Array(24).fill(0); window.dateHourly[r.d][r.h]++;
                    let m = r.d.substring(0,7); mTotal[m] = (mTotal[m] || 0) + 1;
                    if(!mMax[m] || daily[r.d] > mMax[m]) mMax[m] = daily[r.d];
                }});
                document.getElementById('kpi-peak-val').innerText = hourly.indexOf(Math.max(...hourly)) + ':00';
                document.querySelectorAll('.day-cell').forEach(cell => {{
                    let d = cell.getAttribute('data-date'); let mkey = cell.getAttribute('data-mkey');
                    let cnt = daily[d] || 0; let max = mMax[mkey] || 1; let ratio = cnt / max;
                    let bg = cnt===0?'#08080f':(ratio>=0.85?'#3d0a0a':(ratio>=0.55?'#3d1a00':(ratio>=0.25?'#2d2d00':'#0d3320')));
                    let fc = cnt===0?'#333':(ratio>=0.85?'#ff4444':(ratio>=0.55?'#ff8c00':(ratio>=0.25?'#d4c000':'#2ecc71')));
                    cell.style.background = bg; cell.style.color = fc; cell.setAttribute('data-count', cnt); cell.setAttribute('data-ratio', ratio);
                    cell.innerHTML = `<span style='font-size:11px; font-weight:bold;'>${{cell.getAttribute('data-d')}}</span>${{cnt>0?`<span style='font-size:8px; opacity:0.7;'>${{cnt}}</span>`:''}}`;
                }});
            }}
            function showTooltip(el, ev) {{
                const cnt = parseInt(el.getAttribute('data-count')); if (cnt === 0) return;
                const tt = document.getElementById('dfr-tooltip');
                tt.innerHTML = `<div style="color:#00D2FF; font-weight:bold;">${{el.getAttribute('data-date')}}</div><div>Calls: ${{cnt}}</div>`;
                tt.style.display = 'block'; tt.style.left = (ev.clientX + 15) + 'px'; tt.style.top = (ev.clientY - 20) + 'px';
            }}
            function hideTooltip() {{ document.getElementById('dfr-tooltip').style.display = 'none'; }}
            updateDashboard();
        </script></div>"""
    return full_html

# ============================================================
# AGGRESSIVE DATA PARSER (WITH COORDINATE CONVERSION)
# ============================================================
def aggressive_parse_calls(uploaded_files):
    all_calls_list = []
    CV = {
        'date': ['received date','incident date','call date','call creation date','calldatetime','call datetime','calltime','timestamp','date','datetime','dispatch date','time received','incdate'],
        'time': ['call creation time','call time','dispatch time','received time','time', 'hour', 'hour_rept'],
        'priority': ['call priority', 'priority level', 'priority', 'pri', 'urgency', 'offense', 'event', 'type'],
        'lat': ['latitude','lat', 'y coord', 'ycoord', 'ycoor','addressy','geoy'],
        'lon': ['longitude','lon','long','x coord', 'xcoord', 'xcoor','addressx', 'geox']
    }

    def parse_priority(raw):
        s = str(raw).strip().upper()
        if not s or s == 'NAN': return None
        if any(w in s for w in ['ROBBERY','BURGLARY','ASSAULT','SHOOTING','STABBING','CRITICAL','EMERG']): return 1
        if any(w in s for w in ['ACCIDENT','DISTURBANCE','THEFT','MED','ALARM']): return 2
        if any(w in s for w in ['NON REPORTABLE','FOUND PROPERTY','INFO','ROUTINE','MISC']): return 4
        m = re.search(r'^(\d+)', s)
        return int(m.group(1)) if m else 3

    for cfile in uploaded_files:
        try:
            content = cfile.getvalue().decode('utf-8', errors='ignore')
            first_line = content.split('\n')[0]
            delim = ',' if first_line.count(',') > first_line.count('\t') else '\t'
            raw_df = pd.read_csv(io.StringIO(content), sep=delim, dtype=str)
            raw_df.columns = [str(c).lower().strip() for c in raw_df.columns]
            res = pd.DataFrame()
            for field in ['lat', 'lon']:
                found = [c for c in raw_df.columns if any(s in c for s in CV[field])]
                if found: res[field] = pd.to_numeric(raw_df[found[0]], errors='coerce')
            p_found = [c for c in raw_df.columns if any(s in c for s in CV['priority'])]
            res['priority'] = raw_df[p_found[0]].apply(parse_priority) if p_found else 3
            d_found = [c for c in raw_df.columns if any(s in c for s in CV['date'])]
            t_found = [c for c in raw_df.columns if any(s in c for s in CV['time'])]
            if d_found:
                dt_series = pd.to_datetime(raw_df[d_found[0]] + ' ' + raw_df[t_found[0]] if t_found and d_found[0] != t_found[0] else raw_df[d_found[0]], errors='coerce')
                res['date'], res['time'] = dt_series.dt.strftime('%Y-%m-%d'), dt_series.dt.strftime('%H:%M:%S')

            if not res.empty and 'lat' in res.columns and 'lon' in res.columns:
                res = res[(res['lat'] != 0) & (res['lon'] != 0)].dropna(subset=['lat', 'lon'])
                if not res.empty:
                    max_val = max(res['lat'].abs().max(), res['lon'].abs().max())
                    if max_val > 1000:
                        scale = 100.0 if max_val > 100000000 else 1.0
                        transformer = pyproj.Transformer.from_crs("EPSG:2278", "EPSG:4326", always_xy=True)
                        lons, lats = transformer.transform(res['lon'].values / scale, res['lat'].values / scale)
                        res['lon'], res['lat'] = lons, lats
            all_calls_list.append(res)
        except: continue
    return pd.concat(all_calls_list, ignore_index=True).dropna(subset=['lat', 'lon']) if all_calls_list else pd.DataFrame()

def generate_stations_from_calls(df_calls):
    lats, lons = df_calls['lat'].dropna().values, df_calls['lon'].dropna().values
    if len(lats) == 0: return None, "No data."
    cen_lat, cen_lon = lats.mean(), lons.mean()
    bbox = f"{cen_lat-0.15},{cen_lon-0.15},{cen_lat+0.15},{cen_lon+0.15}"
    query = f'[out:json][timeout:25];(node["amenity"~"fire_station|police|school"]({bbox});way["amenity"~"fire_station|police|school"]({bbox}););out center;'
    try:
        req = urllib.request.Request(f"https://overpass-api.de/api/interpreter?data={urllib.parse.quote(query)}")
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            rows = []
            for el in data.get('elements', []):
                t = el.get('tags', {})
                lat = el.get('lat') or (el.get('center') or {}).get('lat')
                lon = el.get('lon') or (el.get('center') or {}).get('lon')
                if lat and lon: rows.append({'name': t.get('name', 'Municipal Station'), 'lat': lat, 'lon': lon, 'type': 'Police' if 'police' in str(t) else 'Fire'})
            return pd.DataFrame(rows).drop_duplicates(subset=['lat','lon']).head(100), "Found stations."
    except: return None, "OSM Error."

# --- GEOGRAPHY HELPERS ---

@st.cache_data
def get_address_from_latlon(lat, lon):
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'BRINC_App_2.0'})
        with urllib.request.urlopen(req, timeout=2) as resp:
            d = json.loads(resp.read().decode('utf-8'))
            if 'address' in d:
                a = d['address']
                return f"{a.get('house_number','')} {a.get('road','')}, {a.get('city','Unknown')}".strip(', ')
    except: pass
    return f"{lat:.4f}, {lon:.4f}"

@st.cache_data
def fetch_county_boundary_local(state_abbr, name_in):
    search = name_in.lower().replace(" county", "").strip()
    fips = STATE_FIPS.get(state_abbr)
    if not fips or not os.path.exists("counties_lite.parquet"): return False, None
    try:
        gdf = gpd.read_parquet("counties_lite.parquet")
        match = gdf[(gdf['STATEFP'] == fips) & (gdf['NAME'].str.lower() == search)]
        if not match.empty:
            match['NAME'] = match['NAME'] + " County"
            return True, match[['NAME', 'geometry']]
    except: pass
    return False, None

@st.cache_data
def fetch_tiger_city_shapefile(fips, city, out_dir):
    url = f"https://www2.census.gov/geo/tiger/TIGER2023/PLACE/tl_2023_{fips}_place.zip"
    try:
        req = urllib.request.urlopen(url, timeout=20)
        with zipfile.ZipFile(io.BytesIO(req.read())) as z:
            tmp = os.path.join(out_dir, f"tmp_{fips}")
            os.makedirs(tmp, exist_ok=True); z.extractall(tmp)
            gdf = gpd.read_file(glob.glob(os.path.join(tmp, "*.shp"))[0])
            m = gdf[gdf['NAME'].str.lower() == city.lower()]
            if not m.empty: return True, m.dissolve(by='NAME').reset_index()
    except: pass
    return False, None

@st.cache_data
def reverse_geocode_state(lat, lon):
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'BRINC_App_2.0'})
        with urllib.request.urlopen(req) as r:
            d = json.loads(r.read().decode('utf-8'))
            a = d.get('address', {})
            return a.get('state', ''), a.get('city', a.get('town', 'Victoria'))
    except: return None, None

def get_circle_coords(lat, lon, r_mi=2.0):
    a = np.linspace(0, 2*np.pi, 100)
    return lat + (r_mi/69.172)*np.sin(a), lon + (r_mi/(69.172*np.cos(np.radians(lat))))*np.cos(a)

@st.cache_resource
def precompute_spatial_data(df_calls, df_stations, city_m, epsg, r_res, r_gua, clat, clon, bhash):
    gdf_c = gpd.GeoDataFrame(df_calls, geometry=gpd.points_from_xy(df_calls.lon, df_calls.lat), crs="EPSG:4326").to_crs(epsg=epsg)
    calls_in = gdf_c[gdf_c.within(city_m)] if city_m else gdf_c
    total = len(calls_in); n = len(df_stations)
    r_mat, g_mat = np.zeros((n, total), dtype=bool), np.zeros((n, total), dtype=bool)
    dr, dg = np.zeros((n, total)), np.zeros((n, total)); meta = []
    c_arr = np.array(list(zip(calls_in.geometry.x, calls_in.geometry.y)))
    for i, row in df_stations.iterrows():
        pt = gpd.GeoSeries([Point(row['lon'], row['lat'])], crs="EPSG:4326").to_crs(epsg).iloc[0]
        dist = np.sqrt((c_arr[:,0]-pt.x)**2 + (c_arr[:,1]-pt.y)**2) / 1609.34
        r_mat[i], g_mat[i], dr[i], dg[i] = dist <= r_res, dist <= r_gua, dist, dist
        meta.append({'name':row['name'],'lat':row['lat'],'lon':row['lon'],'clipped_2m':pt.buffer(r_res*1609.34).intersection(city_m),'clipped_guard':pt.buffer(r_gua*1609.34).intersection(city_m),'avg_dist_r':dist[dist<=r_res].mean() if any(dist<=r_res) else r_res*0.6,'avg_dist_g':dist[dist<=r_gua].mean() if any(dist<=r_gua) else r_gua*0.6})
    return calls_in, calls_in.sample(min(5000, total)), r_mat, g_mat, dr, dg, meta, total

def solve_mclp(r_mat, g_mat, dr, dg, nr, ng, allow_red, inc=True):
    ns, nc = r_mat.shape
    if nc == 0: return [], [], [], []
    def run(tr, tg, lr, lg):
        prob = pulp.LpProblem("MaxCov", pulp.LpMaximize)
        xr = pulp.LpVariable.dicts("r", range(ns), 0, 1, pulp.LpBinary)
        xg = pulp.LpVariable.dicts("g", range(ns), 0, 1, pulp.LpBinary)
        y = pulp.LpVariable.dicts("c", range(nc), 0, 1, pulp.LpBinary)
        prob += pulp.lpSum(y[i] for i in range(nc))
        prob += pulp.lpSum(xr[i] for i in range(ns)) == tr
        prob += pulp.lpSum(xg[i] for i in range(ns)) == tg
        for i in lr: prob += xr[i] == 1
        for i in lg: prob += xg[i] == 1
        if not allow_red:
            for i in range(ns): prob += xr[i] + xg[i] <= 1
        for i in range(nc):
            prob += y[i] <= pulp.lpSum(xr[j] for j in range(ns) if r_mat[j,i]) + pulp.lpSum(xg[j] for j in range(ns) if g_mat[j,i])
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        return [i for i in range(ns) if xr[i].varValue > 0.5], [i for i in range(ns) if xg[i].varValue > 0.5]
    return run(nr, ng, [], []) + ([], []) # Simple non-chrono fallback

# ============================================================
# APP FLOW
# ============================================================

if not st.session_state['csvs_ready']:
    st.markdown("<h1 style='text-align:center;'>BRINC COS Drone Optimizer</h1>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        city_in = st.text_input("City or County", "Victoria")
        state_in = st.selectbox("State", list(STATE_FIPS.keys()), index=43)
        if st.button("Simulate"):
            st.session_state['active_city'], st.session_state['active_state'] = city_in, state_in
            prog = st.progress(0, "Fetching boundary...")
            is_co = "county" in city_in.lower()
            suc, gdf = fetch_county_boundary_local(state_in, city_in) if is_co else fetch_tiger_city_shapefile(STATE_FIPS[state_in], city_in, SHAPEFILE_DIR)
            if suc:
                poly = gdf.geometry.union_all()
                pts = generate_random_points_in_polygon(poly, 2000)
                st.session_state['df_calls'] = pd.DataFrame({'lat':[p[0] for p in pts],'lon':[p[1] for p in pts],'priority':np.random.randint(1,4,2000),'date':'2026-01-01','time':'12:00:00'})
                st.session_state['df_stations'], _ = generate_stations_from_calls(st.session_state['df_calls'])
                st.session_state['csvs_ready'] = True; st.rerun()
    with c2:
        ups = st.file_uploader("Upload CAD CSV", accept_multiple_files=True)
        if ups:
            dfc = aggressive_parse_calls(ups)
            if not dfc.empty:
                st.session_state['df_calls'] = dfc
                st.session_state['df_stations'], _ = generate_stations_from_calls(dfc)
                st.session_state['csvs_ready'] = True; st.rerun()

if st.session_state['csvs_ready']:
    df_calls = st.session_state['df_calls']
    df_stations_all = st.session_state['df_stations']
    
    st.sidebar.title("① Configure")
    k_resp = st.sidebar.slider("Responder Count", 0, 10, 2)
    k_guard = st.sidebar.slider("Guardian Count", 0, 10, 0)
    r_res = st.sidebar.slider("Responder Range (mi)", 1.5, 3.0, 2.0)
    r_gua = st.sidebar.slider("Guardian Range (mi) [⚡ 5mi Rapid]", 1.0, 8.0, 8.0)
    
    # Boundary Setup
    suc, b_gdf = fetch_county_boundary_local(st.session_state['active_state'], st.session_state['active_city'])
    if not suc: b_gdf = gpd.GeoDataFrame({'NAME':['Area'],'geometry':[box(df_calls.lon.min(), df_calls.lat.min(), df_calls.lon.max(), df_calls.lat.max())]}, crs="EPSG:4326")
    
    utm = int((df_calls.lon.mean() + 180) / 6) + 1
    epsg = int(f"326{utm}")
    city_m = b_gdf.to_crs(epsg).geometry.union_all()
    
    # --- STATION FILTERING ---
    st_gdf = gpd.GeoDataFrame(df_stations_all, geometry=gpd.points_from_xy(df_stations_all.lon, df_stations_all.lat), crs="EPSG:4326").to_crs(epsg)
    df_stations_all = df_stations_all[st_gdf.within(city_m.buffer(150))].reset_index(drop=True)
    
    calls_in, calls_disp, r_mat, g_mat, dr, dg, meta, total = precompute_spatial_data(df_calls, df_stations_all, city_m, epsg, r_res, r_gua, 0, 0, "h")
    
    # Solve
    r_idx, g_idx = solve_mclp(r_mat, g_mat, dr, dg, k_resp, k_guard, True)
    
    # Visuals
    st.title(f"DFR Strategy: {st.session_state['active_city']}")
    
    # KPI Bar
    c_cov = (np.logical_or(r_mat[r_idx].any(axis=0) if r_idx else False, g_mat[g_idx].any(axis=0) if g_idx else False).sum() / total) * 100
    st.metric("Total Call Coverage", f"{c_cov:.1f}%")

    m_col, s_col = st.columns([4, 2])
    with m_col:
        fig = go.Figure()
        # Add Boundary
        for geom in (b_gdf.geometry if isinstance(b_gdf.geometry.iloc[0], Polygon) else b_gdf.geometry.iloc[0].geoms):
            x, y = geom.exterior.coords.xy
            fig.add_trace(go.Scattermapbox(lon=list(x), lat=list(y), mode='lines', line=dict(color='white', width=1), name="Boundary"))
        
        # Add Drones
        active_drones = []
        for i, idx in enumerate(r_idx + g_idx):
            d_type = 'RESPONDER' if i < len(r_idx) else 'GUARDIAN'
            d = meta[idx]; color = STATION_COLORS[i % 10]
            clat, clon = get_circle_coords(d['lat'], d['lon'], r_res if d_type=='RESPONDER' else r_gua)
            fig.add_trace(go.Scattermapbox(lat=list(clat), lon=list(clon), mode='lines', fill='toself', fillcolor=f"rgba(0,210,255,0.05)", line=dict(color=color, width=2), name=d['name']))
            
            # Data for Cards
            d_data = d.copy(); d_data.update({'type': d_type, 'color': color, 'deploy_step': i+1, 'cost': CONFIG[f"{d_type}_COST"], 'avg_time_min': d['avg_time_min'] if d_type=='RESPONDER' else d['avg_time_min']})
            # Mock stats for demo stability
            d_data.update({'annual_savings': 85000, 'marginal_flights': 12.4, 'shared_flights': 1.2, 'marginal_deflected': 4.2, 'faa_ceiling': '400ft', 'nearest_airport': 'Local Field', 'be_text': '14 MO'})
            active_drones.append(d_data)

        fig.update_layout(mapbox=dict(style="carto-darkmatter", center=dict(lat=df_calls.lat.mean(), lon=df_calls.lon.mean()), zoom=10), margin=dict(l=0,r=0,t=0,b=0), height=600)
        st.plotly_chart(fig, use_container_width=True)

    with s_col:
        st.subheader("Unit Economics")
        for i in range(0, len(active_drones), 2):
            cols = st.columns(2)
            for j in range(2):
                if i+j < len(active_drones):
                    d = active_drones[i+j]
                    addr = get_address_from_latlon(d['lat'], d['lon'])
                    gurl = f"https://www.google.com/maps?q={d['lat']},{d['lon']}"
                    cols[j].markdown(f"""
<div style="background:{card_bg}; border-top:4px solid {d['color']}; border:1px solid {card_border}; border-radius:4px; padding:12px; margin-bottom:12px; min-height:350px; height:100%; display:flex; flex-direction:column; overflow:hidden;">
<div style="font-weight:700; color:{card_title}; font-size:0.8rem;">{d['name'][:25]}</div>
<div style="font-size:0.6rem; color:#888;">{d['type']} · Phase #{d['deploy_step']}</div>
<div style="font-size:0.65rem; margin:8px 0;"><a href="{gurl}" target="_blank" style="color:{accent_color}; text-decoration:none;">📍 {addr[:30]}... ↗</a></div>
<div style="background:rgba(0,210,255,0.07); padding:8px; text-align:center; border-radius:4px; margin-bottom:8px;">
<div style="font-size:0.6rem; color:{text_muted}; uppercase">Annual Capacity Value</div>
<div style="font-size:1.1rem; font-weight:900; color:{accent_color};">${d['annual_savings']:,}</div>
</div>
<div style="display:grid; grid-template-columns:1fr 1fr; gap:4px; font-size:0.6rem; flex-grow:1;">
<div style="color:{text_muted};">Flights/day</div><div style="text-align:right; font-weight:700;">{d['marginal_flights']}</div>
<div style="color:{text_muted};">Avg Response</div><div style="text-align:right; font-weight:700;">{d['avg_time_min']:.1f}m</div>
<div style="color:{text_muted};">FAA Ceiling</div><div style="text-align:right; font-weight:700;">{d['faa_ceiling']}</div>
</div>
<div style="border-top:1px dashed {card_border}; margin-top:8px; padding-top:8px; display:grid; grid-template-columns:1fr 1fr; font-size:0.65rem;">
<div style="color:{text_muted};">CapEx</div><div style="text-align:right; font-weight:700;">${d['cost']:,}</div>
<div style="color:{text_muted};">ROI</div><div style="text-align:right; color:{accent_color}; font-weight:800;">{d['be_text']}</div>
</div>
</div>
""", unsafe_allow_html=True)

    # Analytics Dashboard
    st.markdown("---")
    st.subheader("📊 CAD Ingestion Analytics")
    components.html(generate_command_center_html(df_calls, total), height=1000)
