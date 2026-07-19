"""Historical deputy-arrival and modeled DFR arrival comparison helpers."""

from __future__ import annotations

import re
from typing import Iterable, Mapping

import numpy as np
import pandas as pd


BASELINE_COLUMNS = {
    "CFS Time": "response_from_cfs_min",
    "First Assigned Time": "response_from_assigned_min",
    "First Enroute Time": "response_from_enroute_min",
}


def _compact(value) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def find_column(df: pd.DataFrame, *names: str):
    """Return the first case/punctuation-insensitive matching column."""
    lookup = {_compact(column): column for column in df.columns}
    for name in names:
        match = lookup.get(_compact(name))
        if match is not None:
            return match
    return None


def _combine_date_and_time(date_values, time_values, reference=None) -> pd.Series:
    date_text = pd.Series(date_values).fillna("").astype(str).str.strip()
    time_text = pd.Series(time_values, index=date_text.index).fillna("").astype(str).str.strip()
    combined = pd.to_datetime(date_text + " " + time_text, format="mixed", errors="coerce")
    combined = combined.where(date_text.ne("") & time_text.ne(""))
    if reference is not None:
        reference = pd.to_datetime(pd.Series(reference, index=combined.index), errors="coerce")
        rollover = combined.notna() & reference.notna() & (combined < reference)
        combined.loc[rollover] = combined.loc[rollover] + pd.Timedelta(days=1)
    return combined


def normalize_arrival_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Add canonical York-style CAD fields without removing source columns.

    The function is deliberately alias-based so similar CAD exports can benefit.
    Arrival timestamps containing only a clock time are rolled into the next day
    when they precede the CFS timestamp.
    """
    if df is None or df.empty:
        return df

    result = df.copy()
    date_col = find_column(result, "CFS Date", "Call Date", "Incident Date", "date")
    cfs_time_col = find_column(result, "CFS Time", "Call Time", "time")
    assigned_col = find_column(result, "First Assigned Time")
    enroute_col = find_column(result, "First Enroute Time")
    arrived_col = find_column(result, "First Arrived Time", "TimeArrived", "Time Arrived")
    beat_col = find_column(result, "Beat")
    explicit_district_col = find_column(result, "District")

    if date_col is not None and "date" not in result.columns:
        parsed_date = pd.to_datetime(result[date_col], errors="coerce")
        result["date"] = parsed_date.dt.strftime("%Y-%m-%d")
    if cfs_time_col is not None and "time" not in result.columns:
        result["time"] = result[cfs_time_col].fillna("").astype(str).str.strip()

    if beat_col is not None:
        beat_values = result[beat_col].fillna("").astype(str).str.strip()
        if "Beat" not in result.columns:
            result["Beat"] = beat_values
        derived_district = beat_values.str.extract(r"^\s*([1-4])", expand=False)
        if explicit_district_col is not None:
            explicit = result[explicit_district_col].fillna("").astype(str).str.strip()
            derived_district = explicit.where(explicit.ne(""), derived_district)
        result["District"] = derived_district.fillna("")

    if date_col is None or cfs_time_col is None:
        return result

    cfs_datetime = _combine_date_and_time(result[date_col], result[cfs_time_col])
    result["cfs_datetime"] = cfs_datetime
    result["TimeDispatched"] = cfs_datetime

    timing_sources = {
        "first_assigned_datetime": assigned_col,
        "first_enroute_datetime": enroute_col,
        "first_arrived_datetime": arrived_col,
    }
    for output_col, source_col in timing_sources.items():
        if source_col is None:
            result[output_col] = pd.NaT
        else:
            result[output_col] = _combine_date_and_time(
                result[date_col], result[source_col], reference=cfs_datetime
            )

    result["TimeArrived"] = result["first_arrived_datetime"]
    result["response_from_cfs_min"] = (
        result["first_arrived_datetime"] - result["cfs_datetime"]
    ).dt.total_seconds() / 60.0
    result["response_from_assigned_min"] = (
        result["first_arrived_datetime"] - result["first_assigned_datetime"]
    ).dt.total_seconds() / 60.0
    result["response_from_enroute_min"] = (
        result["first_arrived_datetime"] - result["first_enroute_datetime"]
    ).dt.total_seconds() / 60.0

    for column in BASELINE_COLUMNS.values():
        result.loc[result[column] < 0, column] = np.nan
    return result


def available_baselines(df: pd.DataFrame) -> list[str]:
    if df is None or df.empty:
        return []
    return [
        label
        for label, column in BASELINE_COLUMNS.items()
        if column in df.columns and pd.to_numeric(df[column], errors="coerce").notna().any()
    ]


def _haversine_miles(station_lat, station_lon, call_lats, call_lons):
    earth_radius_miles = 3958.8
    phi1 = np.radians(float(station_lat))
    phi2 = np.radians(call_lats)
    delta_phi = phi2 - phi1
    delta_lambda = np.radians(call_lons - float(station_lon))
    a = (
        np.sin(delta_phi / 2.0) ** 2
        + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2.0) ** 2
    )
    return earth_radius_miles * 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))


def compute_arrival_advantage(
    calls: pd.DataFrame,
    active_drones: Iterable[Mapping],
    baseline: str = "CFS Time",
    close_threshold_min: float = 2.0,
) -> pd.DataFrame:
    """Compare actual deputy response with the fastest in-range active drone."""
    result = normalize_arrival_fields(calls)
    response_col = BASELINE_COLUMNS.get(baseline, BASELINE_COLUMNS["CFS Time"])
    if response_col not in result.columns:
        result[response_col] = np.nan

    deputy_response = pd.to_numeric(result[response_col], errors="coerce")
    call_lats = pd.to_numeric(result.get("lat"), errors="coerce")
    call_lons = pd.to_numeric(result.get("lon"), errors="coerce")
    eligible = deputy_response.notna() & call_lats.notna() & call_lons.notna()

    fastest = np.full(len(result), np.nan, dtype=float)
    station_names = np.full(len(result), "", dtype=object)
    station_keys = np.full(len(result), "", dtype=object)
    valid_positions = np.flatnonzero(eligible.to_numpy())

    for order, drone in enumerate(active_drones or []):
        try:
            speed_mph = float(drone.get("speed_mph", 0) or 0)
            radius_miles = float(drone.get("radius_m", 0) or 0) / 1609.344
            station_lat = float(drone.get("lat"))
            station_lon = float(drone.get("lon"))
        except (TypeError, ValueError):
            continue
        if speed_mph <= 0 or radius_miles <= 0 or not len(valid_positions):
            continue

        distances = _haversine_miles(
            station_lat,
            station_lon,
            call_lats.iloc[valid_positions].to_numpy(dtype=float),
            call_lons.iloc[valid_positions].to_numpy(dtype=float),
        )
        travel_minutes = distances / speed_mph * 60.0
        in_range = distances <= radius_miles
        current = fastest[valid_positions]
        better = in_range & (np.isnan(current) | (travel_minutes < current))
        if not np.any(better):
            continue
        positions = valid_positions[better]
        fastest[positions] = travel_minutes[better]
        station_names[positions] = str(drone.get("name", "Station"))
        station_keys[positions] = str(
            drone.get("arrival_station_key")
            or f"{drone.get('type', 'DRONE')}:{drone.get('idx', order)}"
        )

    result["arrival_baseline"] = baseline
    result["arrival_deputy_response_min"] = deputy_response
    result["arrival_drone_response_min"] = fastest
    result["arrival_station"] = station_names
    result["arrival_station_key"] = station_keys
    result["arrival_advantage_min"] = deputy_response - result["arrival_drone_response_min"]
    result["arrival_drone_wins"] = result["arrival_advantage_min"] > 0
    result["arrival_eyes_on_min"] = result["arrival_advantage_min"].clip(lower=0)

    result["arrival_category"] = "Missing arrival"
    has_arrival = deputy_response.notna()
    analyzed = has_arrival & result["arrival_drone_response_min"].notna()
    result.loc[has_arrival & ~analyzed, "arrival_category"] = "Outside coverage"
    close = analyzed & (result["arrival_advantage_min"].abs() < float(close_threshold_min))
    result.loc[close, "arrival_category"] = "Close"
    result.loc[analyzed & ~close & result["arrival_drone_wins"], "arrival_category"] = "Drone first"
    result.loc[analyzed & ~close & ~result["arrival_drone_wins"], "arrival_category"] = "Deputy first"
    return result


def _group_summary(df: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    rows = []
    for keys, group in df.groupby(group_columns, dropna=False, sort=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        arrivals = group["arrival_deputy_response_min"].notna()
        analyzed = arrivals & group["arrival_drone_response_min"].notna()
        wins = analyzed & group["arrival_drone_wins"]
        row = {column: value for column, value in zip(group_columns, keys)}
        row.update({
            "Calls": int(len(group)),
            "Arrival Data": int(arrivals.sum()),
            "Compared": int(analyzed.sum()),
            "Drone First": int(wins.sum()),
            "Drone First %": float(wins.sum() / analyzed.sum() * 100.0) if analyzed.any() else np.nan,
            "Median Eyes-On Min": float(group.loc[wins, "arrival_eyes_on_min"].median()) if wins.any() else np.nan,
        })
        rows.append(row)
    return pd.DataFrame(rows)


def build_arrival_summary(df: pd.DataFrame) -> dict:
    """Build overall, district, beat, day, and station arrival summaries."""
    if df is None or df.empty or "arrival_deputy_response_min" not in df.columns:
        return {}
    arrivals = df["arrival_deputy_response_min"].notna()
    analyzed = arrivals & df["arrival_drone_response_min"].notna()
    wins = analyzed & df["arrival_drone_wins"]
    summary = {
        "total_calls": int(len(df)),
        "calls_with_arrival": int(arrivals.sum()),
        "calls_analyzed": int(analyzed.sum()),
        "drone_wins": int(wins.sum()),
        "drone_wins_pct": float(wins.sum() / analyzed.sum() * 100.0) if analyzed.any() else 0.0,
        "arrival_completeness_pct": float(arrivals.sum() / len(df) * 100.0) if len(df) else 0.0,
        "median_eyes_on_min": float(df.loc[wins, "arrival_eyes_on_min"].median()) if wins.any() else 0.0,
    }

    group_specs = {
        "district_summary": [find_column(df, "District")],
        "beat_summary": [find_column(df, "Beat")],
        "day_summary": [find_column(df, "Day of Week")],
        "station_summary": ["arrival_station_key", "arrival_station"],
    }
    for output_name, columns in group_specs.items():
        valid_columns = [column for column in columns if column and column in df.columns]
        source = df
        if output_name == "station_summary":
            source = df[analyzed & df["arrival_station_key"].astype(str).ne("")]
        elif valid_columns:
            source = df[df[valid_columns[0]].fillna("").astype(str).str.strip().ne("")]
        summary[output_name] = _group_summary(source, valid_columns) if valid_columns and not source.empty else pd.DataFrame()
    return summary
