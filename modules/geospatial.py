"""Geospatial utilities - boundaries, geocoding, station generation."""

import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon, MultiPolygon, box
from shapely.ops import unary_union
from pathlib import Path
import os, glob, json, re, zipfile, io, math, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
import tempfile

from modules.config import STATE_FIPS, US_STATES_ABBR, KNOWN_POPULATIONS

        _gdf = _gdf[_gdf.geometry.notna()].copy()
        _gdf = _gdf[~_gdf.geometry.is_empty].copy()
        if _gdf.empty:
            raise ValueError("Uploaded shapefile geometries were empty after loading.")

        _name_col = next((c for c in ['NAME', 'Name', 'name', 'DISTRICT', 'District', 'LABEL', 'Label'] if c in _gdf.columns), None)
        _label = Path(_by_ext['.shp'].name).stem
        if _name_col:
            _gdf['DISPLAY_NAME'] = _gdf[_name_col].astype(str).fillna('').replace('nan', '').str.strip()
            _gdf['DISPLAY_NAME'] = _gdf['DISPLAY_NAME'].replace('', _label)
        else:
            _gdf['DISPLAY_NAME'] = _label

        return _gdf[['DISPLAY_NAME', 'geometry']].copy(), _label, Path(_by_ext['.shp'].name).name


def _boundary_overlay_status(boundary_geom_4326, overlay_gdf, epsg_code):
    if boundary_geom_4326 is None or boundary_geom_4326.is_empty or overlay_gdf is None or overlay_gdf.empty:
        return None
    try:
        _overlay_utm = overlay_gdf.to_crs(epsg=epsg_code)
        _overlay_union = (_overlay_utm.geometry.union_all() if hasattr(_overlay_utm.geometry, 'union_all') else _overlay_utm.geometry.unary_union)
        _boundary_utm = gpd.GeoSeries([boundary_geom_4326], crs='EPSG:4326').to_crs(epsg=epsg_code).iloc[0]
        if _overlay_union.is_empty or _boundary_utm.is_empty:
            return None
        _inter = _overlay_union.intersection(_boundary_utm)
        _overlay_area = float(_overlay_union.area or 0)
        _boundary_area = float(_boundary_utm.area or 0)
        _inter_area = float(_inter.area or 0)
        if _overlay_area <= 0 or _boundary_area <= 0:
            return None
        _pct_overlay_inside = max(0.0, min(100.0, _inter_area / _overlay_area * 100.0))
        _pct_boundary_covered = max(0.0, min(100.0, _inter_area / _boundary_area * 100.0))
        if _inter_area <= 0:
            _status = 'no_overlap'
            _message = 'Uploaded boundary overlay does not overlap the selected city/county boundary.'
        elif _pct_overlay_inside >= 99.5:
            _status = 'inside'
            _message = f"Uploaded boundary overlay sits within the selected boundary ({_pct_overlay_inside:.1f}% inside)."
        elif _pct_boundary_covered >= 99.5:
            _status = 'contains'
            _message = f"Uploaded boundary overlay fully contains the selected boundary ({_pct_overlay_inside:.1f}% of overlay overlaps)."
        else:
            _status = 'partial'
            _message = f"Uploaded boundary overlay partially overlaps the selected boundary ({_pct_overlay_inside:.1f}% of overlay overlaps)."
        return {'status': _status, 'message': _message, 'pct_overlay_inside': _pct_overlay_inside, 'pct_boundary_covered': _pct_boundary_covered}
    except Exception:
        return None


# --- MOBILE SUMMARY ROUTE (must run before set_page_config) ---
if st.query_params.get("view") == "mobile":
    st.set_page_config(page_title="BRINC DFR — Mobile Summary", page_icon="🚁",
                       layout="centered", initial_sidebar_state="collapsed")
    st.markdown("""
<style>
[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:#080c14!important;}
[data-testid="block-container"]{padding:1rem 1rem 3rem!important;max-width:480px!important;margin:0 auto!important;}
[data-testid="stSidebar"],[data-testid="collapsedControl"],[data-testid="stSidebarNav"]{display:none!important;}
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700;900&family=DM+Mono:wght@500&display=swap');
.mob-header{text-align:center;padding:24px 0 20px;border-bottom:1px solid rgba(0,210,255,0.2);margin-bottom:24px;}
.mob-logo{font-size:2rem;font-weight:900;color:#00D2FF;letter-spacing:3px;font-family:'DM Sans',sans-serif;line-height:1;}
.mob-logo span{color:#fff;}
.mob-city{font-size:1.35rem;font-weight:700;color:#f0f0f0;margin-top:8px;font-family:'DM Sans',sans-serif;}
.mob-tagline{font-size:0.75rem;color:#666;text-transform:uppercase;letter-spacing:1.5px;margin-top:4px;}
                    continue
                if poly_gdf.crs is None:
                    poly_gdf = poly_gdf.set_crs(epsg=4326)
                poly_gdf = poly_gdf.to_crs(epsg=4326)

                joined = gpd.sjoin(pts_gdf[['geometry']], poly_gdf[[name_col, 'geometry']], how='left', predicate='within')
                hit_counts = joined[name_col].value_counts().dropna()
                _debug_msgs.append(f"sjoin hits: {dict(list(hit_counts.items())[:10])}")
                if hit_counts.empty:
                    continue

                total = hit_counts.sum()
                for jname, cnt in hit_counts.items():
                    # Include if meets share threshold OR absolute minimum count
                    if cnt / total < min_call_share and cnt < min_call_count:
                        continue
                    row = poly_gdf[poly_gdf[name_col] == jname].copy()
                    if row.empty:
                        continue
                    display = str(jname)
                    if kind == 'county' and not display.lower().endswith('county'):
                        display = display + ' County'
                    already = any(r['DISPLAY_NAME'] == display for r in results)
                    if not already:
                        results.append({
                            'DISPLAY_NAME': display,
                            'data_count': int(cnt),
                            'geometry': row.geometry.iloc[0],
                        })
            except Exception as _e:
                _debug_msgs.append(f"{parquet_file} ERROR: {_e}\n{_tb.format_exc()[-300:]}")
                continue

            if results and parquet_file.startswith('places'):
                break

        _debug_msgs.append(f"total results: {len(results)}, names: {[r['DISPLAY_NAME'] for r in results]}")
        st.session_state['_jur_debug'] = _debug_msgs

        if not results:
            return None

        out = gpd.GeoDataFrame(results, crs='EPSG:4326')
        out = out.sort_values('data_count', ascending=False).reset_index(drop=True)
        return out

    except Exception as _e:
        _debug_msgs.append(f"OUTER ERROR: {_e}\n{_tb.format_exc()[-400:]}")
        st.session_state['_jur_debug'] = _debug_msgs
        return None


def _select_best_boundary_for_calls(df_calls, city_text, state_abbr, prefer_county=False):
    """Try place and county boundaries and keep the candidate containing the most uploaded calls."""
    candidates = []

    try:
        place_success, place_gdf = fetch_place_boundary_local(state_abbr, city_text)
        if place_success and place_gdf is not None and not place_gdf.empty:
            candidates.append(('place', place_gdf, _count_points_within_boundary(df_calls, place_gdf)))
    except Exception:
        pass

    county_names = [city_text]
    if not str(city_text).lower().endswith(" county"):
        county_names.append(f"{city_text} County")

    for cname in county_names:
        try:
            county_success, county_gdf = fetch_county_boundary_local(state_abbr, cname)
            if county_success and county_gdf is not None and not county_gdf.empty:
                candidates.append(('county', county_gdf, _count_points_within_boundary(df_calls, county_gdf)))
                break
        except Exception:
            pass

    if not candidates:
        # ── TIGER fallback: parquet not present or city not found — download from Census ──
        state_fips = STATE_FIPS.get(state_abbr)
        if state_fips:
            try:
                tiger_success, tiger_gdf = fetch_tiger_city_shapefile(state_fips, city_text, SHAPEFILE_DIR)
                if tiger_success and tiger_gdf is not None and not tiger_gdf.empty:
                    tiger_gdf = tiger_gdf.copy()
                    if 'NAME' not in tiger_gdf.columns:
                        tiger_gdf['NAME'] = city_text
                    hits = _count_points_within_boundary(df_calls, tiger_gdf)
                    candidates.append(('place', tiger_gdf, hits))
            except Exception:
                pass

    if not candidates:
        return False, None, 'place', 0

    if prefer_county:
        candidates.sort(key=lambda x: (x[2], 1 if x[0] == 'county' else 0), reverse=True)
    else:
        candidates.sort(key=lambda x: (x[2], 1 if x[0] == 'place' else 0), reverse=True)

    best_kind, best_gdf, best_hits = candidates[0]
    return True, best_gdf, best_kind, int(best_hits)

# ============================================================
# COMMAND CENTER ANALYTICS GENERATOR
# ============================================================

def _detect_datetime_series_for_labels(df):
    """Return a best-effort parsed datetime series from common CAD field patterns."""
    if df is None or len(df) == 0:
        return None
    try:
        if 'date' in df.columns and 'time' in df.columns:
            s = pd.to_datetime(df['date'].astype(str).fillna('') + ' ' + df['time'].astype(str).fillna(''), errors='coerce')
            if s.notna().sum() > 0:
                return s
        if 'date' in df.columns:
            s = pd.to_datetime(df['date'], errors='coerce')
            if s.notna().sum() > 0:
                return s
        candidates = [
            'createdtime_central', 'created time', 'createdtime', 'call datetime', 'calldatetime',
            'timestamp', 'datetime', 'incident datetime', 'received time', 'time received',
            'dispatch datetime', 'event time', 'event datetime'
        ]
        col_map = {str(c).strip().lower(): c for c in df.columns}
        for cand in candidates:
            col = cand if cand in df.columns else col_map.get(cand)
            if col is not None:
                s = pd.to_datetime(df[col], errors='coerce')
                if s.notna().sum() > 0:
                    return s
    except Exception:
        return None
    return None



def estimate_high_activity_overtime(df_calls_full, state_abbr, calls_covered_perc, dfr_dispatch_rate, deflection_rate):
    """Estimate high-activity monthly staffing pressure and officer overtime replacement cost."""
    if df_calls_full is None or len(df_calls_full) == 0:
        return None
    try:
        dt = _detect_datetime_series_for_labels(df_calls_full)
        if dt is None:
            return None
        work = df_calls_full.copy()
        work['_dt'] = pd.to_datetime(dt, errors='coerce')
        work = work.dropna(subset=['_dt'])
        if work.empty:
            return None

        work['_month'] = work['_dt'].dt.to_period('M').astype(str)
        work['_hour_key'] = work['_dt'].dt.floor('H')
        hourly = work.groupby('_hour_key').size().rename('calls').reset_index()
        hourly['_month'] = hourly['_hour_key'].dt.to_period('M').astype(str)

        monthly_rows = []
        for month, grp in hourly.groupby('_month'):
            if grp.empty:
                continue
            threshold = grp['calls'].quantile(0.75)
            busy = grp[grp['calls'] >= threshold].copy()
            if busy.empty:
                busy = grp.nlargest(max(1, int(len(grp) * 0.25)), 'calls')
            total_busy_calls = float(busy['calls'].sum())
            busy_hours = int(busy['_hour_key'].nunique())
            if busy_hours <= 0:
                continue

            officer_hourly, wage_source = CONFIG['OFFICER_HOURLY_WAGE'], 'estimate'
            overtime_hourly = officer_hourly * 1.5

            drone_relief_share = (calls_covered_perc / 100.0) * dfr_dispatch_rate * deflection_rate
            residual_busy_calls = total_busy_calls * max(0.0, 1.0 - drone_relief_share)
            overtime_cost = residual_busy_calls * CONFIG['OFFICER_COST_PER_CALL']
            overtime_hours = overtime_cost / overtime_hourly if overtime_hourly > 0 else 0.0

            monthly_rows.append({
                'month': month,
                'busy_hours': busy_hours,
                'busy_calls': total_busy_calls,
                'residual_calls': residual_busy_calls,
                'ot_hourly': overtime_hourly,
                'ot_cost': overtime_cost,
                'ot_hours': overtime_hours,
                'wage_source': wage_source,
            })

        if not monthly_rows:
            return None
        monthly_df = pd.DataFrame(monthly_rows).sort_values('month')
        return {
            'monthly': monthly_df,
            'avg_busy_hours': float(monthly_df['busy_hours'].mean()),
            'avg_ot_hours': float(monthly_df['ot_hours'].mean()),
            'avg_ot_cost': float(monthly_df['ot_cost'].mean()),
            'ot_hourly': float(monthly_df['ot_hourly'].median()),
            'wage_source': monthly_df['wage_source'].iloc[0],
            'peak_month': monthly_df.loc[monthly_df['ot_cost'].idxmax(), 'month'],
            'peak_ot_cost': float(monthly_df['ot_cost'].max()),
        }
    except Exception:
        return None



def estimate_specialty_response_savings(df_calls_full, total_calls_annual, calls_covered_perc=100.0):
    """Estimate additional annual savings from thermal-enabled search efficiency and avoided K-9 deployments.

    The model intentionally stays conservative:
    - Thermal value is applied to a subset of addressable calls that often benefit from search / locate / perimeter support.
    - K-9 value is applied to a smaller subset of addressable calls that are likely to require tracking or perimeter work.
    - If CAD call types are available, the function uses them; otherwise it falls back to conservative defaults.
    """
    addressable_calls = max(0.0, float(total_calls_annual or 0) * max(0.0, min(1.0, float(calls_covered_perc or 0) / 100.0)))
    out = {
        'addressable_calls_annual': addressable_calls,
        'thermal_rate': float(CONFIG["THERMAL_DEFAULT_APPLICABLE_RATE"]),
        'k9_rate': float(CONFIG["K9_DEFAULT_APPLICABLE_RATE"]),
        'fire_rate': float(CONFIG["FIRE_DEFAULT_APPLICABLE_RATE"]),
        'thermal_calls_annual': 0.0,
        'k9_calls_annual': 0.0,
        'fire_calls_annual': 0.0,
        'thermal_savings': 0.0,
        'k9_savings': 0.0,
        'fire_savings': 0.0,
        'additional_savings_total': 0.0,
        'source': 'default_model',
    }
    if addressable_calls <= 0:
        return out

    call_type_col = None
    if df_calls_full is not None and len(df_calls_full) > 0:
        for c in ['call_type_desc','agencyeventtypecodedesc','calldesc','description','nature','event_desc']:
            if c in df_calls_full.columns and df_calls_full[c].dropna().shape[0] > 0:
                call_type_col = c
                break

    if call_type_col is not None:
        s = df_calls_full[call_type_col].fillna('').astype(str).str.lower().str.strip()
        if not s.empty:
            thermal_pattern = (
                r'suspicious|prowler|alarm|burglar|robbery|theft|assault|shots|gun|weapon|person search|search|perimeter|'
                r'missing|welfare|suicid|disturbance|fight|domestic|trespass|subject check|unknown trouble|wanted'
            )
            k9_pattern = (
                r'k-?9|canine|track|tracking|perimeter|search|search warrant|manhunt|flee|fled|foot pursuit|'
                r'missing|burglary|robbery|woods|field|suspect search'
            )
            thermal_rate_raw = float(s.str.contains(thermal_pattern, regex=True, na=False).mean())
            k9_rate_raw = float(s.str.contains(k9_pattern, regex=True, na=False).mean())
            fire_pattern = (
                r'fire|structure fire|building fire|fire alarm|alarm fire|brush fire|grass fire|'
                r'wildfire|vegetation fire|vehicle fire|dumpster fire|smoke|smoke investigation|'
                r'odor of smoke|fire investigation|carbon monoxide|co alarm|gas leak|hazmat'
            )
            fire_rate_raw = float(s.str.contains(fire_pattern, regex=True, na=False).mean())
            out['thermal_rate'] = min(0.25, max(CONFIG["THERMAL_DEFAULT_APPLICABLE_RATE"] * 0.5, thermal_rate_raw if thermal_rate_raw > 0 else CONFIG["THERMAL_DEFAULT_APPLICABLE_RATE"]))
            out['k9_rate'] = min(0.08, max(CONFIG["K9_DEFAULT_APPLICABLE_RATE"] * 0.5, k9_rate_raw if k9_rate_raw > 0 else CONFIG["K9_DEFAULT_APPLICABLE_RATE"]))
            out['fire_rate'] = min(0.20, max(CONFIG["FIRE_DEFAULT_APPLICABLE_RATE"] * 0.5, fire_rate_raw if fire_rate_raw > 0 else CONFIG["FIRE_DEFAULT_APPLICABLE_RATE"]))
            out['source'] = f'cad_call_types:{call_type_col}'

    out['thermal_calls_annual'] = addressable_calls * out['thermal_rate']
    out['k9_calls_annual'] = addressable_calls * out['k9_rate']
    out['fire_calls_annual'] = addressable_calls * out['fire_rate']
    out['thermal_savings'] = out['thermal_calls_annual'] * float(CONFIG["THERMAL_SAVINGS_PER_CALL"])
    out['k9_savings'] = out['k9_calls_annual'] * float(CONFIG["K9_SAVINGS_PER_CALL"])
    out['fire_savings'] = out['fire_calls_annual'] * float(CONFIG["FIRE_SAVINGS_PER_CALL"])
    out['additional_savings_total'] = out['thermal_savings'] + out['k9_savings'] + out['fire_savings']
    return out

def build_high_activity_staffing_html(overtime_stats, dark=True, compact=False):
    """Return an HTML block for the High-Activity Staffing Pressure section."""
    if overtime_stats is None:
        return ""
    bg = "#06060a" if dark else "#ffffff"
    card = "#0c0c12" if dark else "#ffffff"
    border = "#1a1a26" if dark else "#e5e7eb"
    text_main = "#e8e8f2" if dark else "#111118"
    text_muted = "#7777a0" if dark else "#6b7280"
    accent = "#00D2FF"
    title_size = "13px" if compact else "0.95rem"
    body_size = "11px" if compact else "0.72rem"
    metric_size = "24px" if compact else "1.45rem"
    monthly_rows_html = "".join([
        f"<tr><td style='padding:6px 8px; border-top:1px solid {border}; color:{text_main};'>{row.month}</td>"
        f"<td style='padding:6px 8px; border-top:1px solid {border}; text-align:right; color:{text_main};'>{int(row.busy_hours):,}</td>"
        f"<td style='padding:6px 8px; border-top:1px solid {border}; text-align:right; color:{text_main};'>{row.ot_hours:,.0f}</td>"
        f"<td style='padding:6px 8px; border-top:1px solid {border}; text-align:right; color:{accent};'>${row.ot_cost:,.0f}</td></tr>"
        for row in overtime_stats['monthly'].itertuples(index=False)
    ])
    return f"""
    <div style="background:{bg}; border:1px solid {border}; border-radius:8px; padding:16px 18px; margin:14px 0 14px 0;">
        <div style="display:flex; justify-content:space-between; align-items:flex-end; gap:12px; flex-wrap:wrap; margin-bottom:10px;">
            <div>
                <div style="font-size:10px; color:{text_muted}; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;">High-Activity Staffing Pressure</div>
                <div style="font-size:{title_size}; color:{text_main}; font-weight:800;">Estimated officer overtime needed to cover residual peak demand</div>
            </div>
            <div style="font-size:10px; color:{text_muted};">Officer wage basis: <span style="color:{text_main};">{overtime_stats['wage_source']}</span></div>
        </div>
        <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:12px;">
            <div style="background:{card}; border:1px solid {border}; border-radius:6px; padding:10px; text-align:center;">
                <div style="font-size:10px; color:{text_muted}; text-transform:uppercase;">Avg High-Activity Hours / Mo</div>
                <div style="font-size:{metric_size}; font-weight:800; color:{text_main}; font-family:'IBM Plex Mono', monospace;">{overtime_stats['avg_busy_hours']:.0f}</div>
            </div>
            <div style="background:{card}; border:1px solid {border}; border-radius:6px; padding:10px; text-align:center;">
                <div style="font-size:10px; color:{text_muted}; text-transform:uppercase;">Avg OT Hours Needed / Mo</div>
                <div style="font-size:{metric_size}; font-weight:800; color:{text_main}; font-family:'IBM Plex Mono', monospace;">{overtime_stats['avg_ot_hours']:.0f}</div>
            </div>
            <div style="background:{card}; border:1px solid {border}; border-radius:6px; padding:10px; text-align:center;">
                <div style="font-size:10px; color:{text_muted}; text-transform:uppercase;">Avg OT Cost / Mo</div>
                <div style="font-size:{metric_size}; font-weight:800; color:{accent}; font-family:'IBM Plex Mono', monospace;">${overtime_stats['avg_ot_cost']:,.0f}</div>
            </div>
            <div style="background:{card}; border:1px solid {border}; border-radius:6px; padding:10px; text-align:center;">
                <div style="font-size:10px; color:{text_muted}; text-transform:uppercase;">Avg OT Hourly Rate</div>
                <div style="font-size:{metric_size}; font-weight:800; color:{text_main}; font-family:'IBM Plex Mono', monospace;">${overtime_stats['ot_hourly']:.2f}</div>
            </div>
        </div>
        <div style="font-size:{body_size}; color:{text_muted}; margin-bottom:10px;">Peak month: <span style="color:{text_main}; font-weight:700;">{overtime_stats['peak_month']}</span> · estimated OT spend <span style="color:{accent}; font-weight:700;">${overtime_stats['peak_ot_cost']:,.0f}</span></div>
        <div style="overflow-x:auto;">
            <table style="width:100%; border-collapse:collapse; font-size:{body_size};">
                <thead>
                    <tr>
                        <th style="text-align:left; padding:6px 8px; color:{text_muted}; font-weight:700; border-bottom:1px solid {border};">Month</th>
                        <th style="text-align:right; padding:6px 8px; color:{text_muted}; font-weight:700; border-bottom:1px solid {border};">High-Activity Hours</th>
                        <th style="text-align:right; padding:6px 8px; color:{text_muted}; font-weight:700; border-bottom:1px solid {border};">OT Hours</th>
                        <th style="text-align:right; padding:6px 8px; color:{text_muted}; font-weight:700; border-bottom:1px solid {border};">OT Cost</th>
                    </tr>
                </thead>
                <tbody>{monthly_rows_html}</tbody>
            </table>
        </div>
    </div>
    """

def generate_command_center_html(df, total_orig_calls, export_mode=False):
    """Generates the full Command Center visual suite with interactive Javascript filtering."""
    if df is None or df.empty:
        return "<div style='color:gray; padding:20px;'>Analytics unavailable. No incident records loaded.</div>"

    import calendar as _cal
    import json

