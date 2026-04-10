"""FAA airspace, regulatory layers, and RF coverage analysis."""
import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
import plotly.graph_objects as go
from shapely.geometry import box, Point
from pathlib import Path
import os, json, math, urllib.request
from modules.config import FAA_CEILING_COLORS, FAA_DEFAULT_COLOR, STATION_COLORS

def generate_mock_faa_grid(minx, miny, maxx, maxy):
    features = []
    x_steps = np.linspace(minx, maxx, 20)
    y_steps = np.linspace(miny, maxy, 20)
    mock_airports = [{"lon": minx + 0.3 * (maxx - minx), "lat": miny + 0.3 * (maxy - miny), "radius": 0.15, "name": "Mock Intl (MCK)"}]
    for i in range(len(x_steps) - 1):
        for j in range(len(y_steps) - 1):
            cell_poly = [[x_steps[i], y_steps[j]], [x_steps[i+1], y_steps[j]], [x_steps[i+1], y_steps[j+1]], [x_steps[i], y_steps[j+1]], [x_steps[i], y_steps[j]]]
            cell_center = Point((x_steps[i] + x_steps[i+1]) / 2, (y_steps[j] + y_steps[j+1]) / 2)
            ceiling, arpt_name = None, ""
            for ap in mock_airports:
                dist_ratio = cell_center.distance(Point(ap["lon"], ap["lat"])) / ap["radius"]
                if dist_ratio < 1.0:
                    if   dist_ratio < 0.15: ceiling, arpt_name = 0,   ap["name"]
                    elif dist_ratio < 0.35: ceiling, arpt_name = 50,  ap["name"]
                    elif dist_ratio < 0.55: ceiling, arpt_name = 100, ap["name"]
                    else:                   ceiling, arpt_name = 200, ap["name"]
                    break
            if ceiling is not None:
                features.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [cell_poly]}, "properties": {"CEILING": ceiling, "ARPT_Name": arpt_name}})
    return {"type": "FeatureCollection", "features": features}

@st.cache_data
def load_cached_regulatory_layers(state_abbr, layer_type="faa_airspace"):
    """
    Load pre-cached regulatory layers (FAA, obstacles, cell towers, no-fly zones).
    These are pre-downloaded by download_regulatory_layers.py and cached as parquet.

    layer_type: "faa_airspace" | "faa_obstacles" | "cell_towers" | "no_fly_zones"
    """
    try:
        layer_dir = Path("regulatory_layers")
        if not layer_dir.exists():
            return gpd.GeoDataFrame()

        if layer_type == "faa_airspace":
            fpath = layer_dir / f"faa_airspace_{state_abbr.upper()}.parquet"
        elif layer_type == "faa_obstacles":
            fpath = layer_dir / f"faa_obstacles.parquet"
        elif layer_type == "cell_towers":
            fpath = layer_dir / f"cell_towers_{state_abbr.upper()}.parquet"
        elif layer_type == "no_fly_zones":
            fpath = layer_dir / f"no_fly_zones.parquet"
        else:
            return gpd.GeoDataFrame()

        if fpath.exists():
            gdf = gpd.read_parquet(fpath)
            return gdf
        else:
            return gpd.GeoDataFrame()

    except Exception as e:
        return gpd.GeoDataFrame()

@st.cache_data
def load_cached_airfields():
    """Load all US airfields from pre-cached parquet."""
    try:
        fpath = Path("regulatory_layers") / "airfields_us.parquet"
        if fpath.exists():
            return gpd.read_parquet(fpath)
    except Exception:
        pass
    return gpd.GeoDataFrame()

@st.cache_data
def load_faa_parquet(minx, miny, maxx, maxy):
    """Optimized FAA loader — uses cached state-level parquets."""
    try:
        # State bounds for coordinate-to-state mapping
        state_bounds = {
            "AL": (-88.5, 30.2, -84.9, 35.0), "AK": (-172.0, 51.3, -130.0, 71.6),
            "AZ": (-114.8, 31.3, -109.0, 37.0), "AR": (-94.4, 33.0, -89.6, 36.5),
            "CA": (-124.5, 32.5, -114.1, 42.0), "CO": (-109.1, 36.9, -102.0, 41.0),
            "CT": (-73.7, 40.9, -71.8, 42.1), "DE": (-75.8, 38.4, -75.0, 39.8),
            "FL": (-87.6, 24.5, -80.0, 31.0), "GA": (-85.6, 30.4, -80.8, 35.0),
            "HI": (-160.2, 18.9, -154.8, 22.2), "ID": (-117.2, 42.0, -111.0, 49.0),
            "IL": (-91.5, 37.0, -87.0, 42.5), "IN": (-88.1, 37.8, -84.8, 41.8),
            "IA": (-96.6, 40.3, -90.1, 43.5), "KS": (-102.0, 37.0, -94.6, 40.0),
            "KY": (-89.6, 36.5, -81.9, 39.1), "LA": (-94.0, 29.0, -88.8, 33.0),
            "ME": (-71.1, 43.0, -66.9, 47.5), "MD": (-79.5, 37.9, -75.0, 39.7),
            "MA": (-73.5, 41.2, -69.9, 42.9), "MI": (-90.4, 41.7, -83.3, 48.3),
            "MN": (-97.2, 43.5, -89.5, 49.4), "MS": (-91.7, 30.2, -88.1, 35.0),
            "MO": (-95.8, 36.0, -90.1, 40.6), "MT": (-116.0, 45.0, -104.0, 49.0),
            "NE": (-104.1, 40.0, -95.3, 43.0), "NV": (-120.0, 35.0, -114.4, 42.0),
            "NH": (-72.6, 42.7, -70.7, 45.3), "NJ": (-75.6, 38.9, -73.9, 41.4),
            "NM": (-109.0, 31.8, -103.0, 37.0), "NY": (-79.8, 40.5, -71.9, 45.0),
            "NC": (-84.3, 33.8, -75.4, 36.6), "ND": (-104.0, 45.9, -96.6, 49.0),
            "OH": (-84.8, 38.4, -80.5, 42.3), "OK": (-103.0, 33.6, -94.4, 37.0),
            "OR": (-124.6, 42.0, -116.5, 46.3), "PA": (-80.5, 39.7, -74.7, 42.3),
            "RI": (-71.9, 41.1, -71.1, 42.0), "SC": (-83.4, 32.0, -78.5, 35.2),
            "SD": (-104.0, 42.5, -96.4, 45.9), "TN": (-90.3, 35.0, -81.6, 36.7),
            "TX": (-106.6, 25.8, -93.5, 36.5), "UT": (-114.0, 37.0, -109.0, 42.0),
            "VT": (-73.4, 42.7, -71.5, 45.0), "VA": (-83.7, 36.5, -75.2, 39.5),
            "WA": (-124.7, 45.6, -116.9, 49.0), "WV": (-82.6, 37.2, -77.7, 40.6),
            "WI": (-92.9, 42.5, -86.8, 47.3), "WY": (-111.0, 41.0, -104.0, 45.0),
            "DC": (-77.1, 38.8, -76.9, 39.0),
        }

        # Find which state the map bounds fall into
        center_lon = (minx + maxx) / 2.0
        center_lat = (miny + maxy) / 2.0

        best_state = None
        for state, (sb_minx, sb_miny, sb_maxx, sb_maxy) in state_bounds.items():
            if sb_minx <= center_lon <= sb_maxx and sb_miny <= center_lat <= sb_maxy:
                best_state = state
                break

        if not best_state:
            best_state = "IL"  # Default fallback

        # Try to load state-level FAA airspace
        gdf = load_cached_regulatory_layers(best_state, "faa_airspace")

        if gdf.empty:
            # Fallback to mock if no cached data
            mock_result = generate_mock_faa_grid(minx, miny, maxx, maxy)
            return mock_result

        # Filter to bounding box
        pad = 0.05
        try:
            filtered = gdf.cx[minx-pad:maxx+pad, miny-pad:maxy+pad]
        except Exception as e:
            # If cx indexing fails, return all data
            filtered = gdf

        if filtered.empty:
            # No data in this bounding box, return empty
            return {"type": "FeatureCollection", "features": []}

        # Convert to GeoJSON
        result = json.loads(filtered.to_json())
        return result

    except Exception as e:
        return generate_mock_faa_grid(minx, miny, maxx, maxy)

def add_faa_laanc_layer_to_plotly(fig, faa_geojson, is_dark=True):
    if not faa_geojson or not faa_geojson.get("features"):
        return

    text_lons, text_lats, text_strings, text_hovers = [], [], [], []
    trace_count = 0

    for feature in faa_geojson.get("features", []):
        geom = feature.get("geometry")
        props = feature.get("properties", {})
        # Try both old and new property names for backwards compatibility
        ceiling = props.get("ceiling_ft") or props.get("CEILING")
        zone_name = props.get("name") or props.get("ARPT_Name") or props.get("ARPT_NAME") or "Airspace Zone"

        if ceiling is None or geom is None or geom.get("type") != "Polygon":
            continue

        snapped = min(FAA_CEILING_COLORS.keys(), key=lambda v: abs(v - ceiling))
        colors = FAA_CEILING_COLORS.get(snapped, FAA_DEFAULT_COLOR)
        coords = geom["coordinates"][0]

        if not coords or len(coords) < 2:
            continue

        bx, by = zip(*coords)

        # Add polygon trace
        fig.add_trace(go.Scattermap(
            mode="lines",
            lon=list(bx),
            lat=list(by),
            fill="toself",
            fillcolor=colors["fill"],
            line=dict(color=colors["line"], width=2),
            hoverinfo="text",
            text=f"<b>{ceiling} ft AGL</b><br>{zone_name}",
            name=f"LAANC {ceiling}ft",
            showlegend=False
        ))
        trace_count += 1

        # Add centroid label
        try:
            centroid = shape(geom).centroid
            text_lons.append(centroid.x)
            text_lats.append(centroid.y)
            text_strings.append(str(ceiling))
            text_hovers.append(f"{ceiling} ft — {zone_name}")
        except Exception:
            pass

    # Add text labels if any
    if text_lons:
        fig.add_trace(go.Scattermap(
            mode="text",
            lon=text_lons,
            lat=text_lats,
            text=text_strings,
            hovertext=text_hovers,
            hoverinfo="text",
            textfont=dict(size=10, color="#ffffff" if is_dark else "#000000"),
            showlegend=False,
            name="LAANC Labels"
        ))

def add_cell_towers_layer_to_plotly(fig, state_abbr, minx, miny, maxx, maxy):
    """Add OpenCelliD cell tower markers to map."""
    try:
        gdf = load_cached_regulatory_layers(state_abbr, "cell_towers")
        if gdf.empty: return

        # Clip to bounding box
        pad = 0.05
        bbox = box(minx-pad, miny-pad, maxx+pad, maxy+pad)
        clipped = gdf[gdf.geometry.intersects(bbox)]

        if not clipped.empty:
            fig.add_trace(go.Scattermap(
                lat=clipped.geometry.y,
                lon=clipped.geometry.x,
                mode='markers',
                marker=dict(size=5, color='#ff9500', opacity=0.6),
                name='Cell Towers',
                hovertext=['Cell Tower' for _ in clipped],
                hoverinfo='text',
                showlegend=True,
            ))
    except Exception:
        pass

def add_faa_obstacles_layer_to_plotly(fig, minx, miny, maxx, maxy):
    """Add FAA Digital Obstacle File (obstacles > 200 ft) to map."""
    try:
        gdf = load_cached_regulatory_layers("US", "faa_obstacles")
        if gdf.empty: return

        # Clip to bounding box
        pad = 0.05
        bbox = box(minx-pad, miny-pad, maxx+pad, maxy+pad)
        clipped = gdf[gdf.geometry.intersects(bbox)]

        if not clipped.empty:
            fig.add_trace(go.Scattermap(
                lat=clipped.geometry.y,
                lon=clipped.geometry.x,
                mode='markers',
                marker=dict(size=6, color='#ff3b3b', opacity=0.5, symbol='diamond'),
                name='Flight Hazards',
                hovertext=['Obstacle > 200 ft' for _ in clipped],
                hoverinfo='text',
                showlegend=True,
            ))
    except Exception:
        pass

def add_no_fly_zones_layer_to_plotly(fig, minx, miny, maxx, maxy):
    """Add no-fly zones (parks, water, restricted areas) to map."""
    try:
        gdf = load_cached_regulatory_layers("US", "no_fly_zones")
        if gdf.empty: return

        # Clip to bounding box
        pad = 0.05
        bbox = box(minx-pad, miny-pad, maxx+pad, maxy+pad)
        clipped = gdf[gdf.geometry.intersects(bbox)]

        if not clipped.empty:
            for _, row in clipped.iterrows():
                geom = row.geometry
                if geom.geom_type == 'Polygon':
                    lon, lat = zip(*geom.exterior.coords)
                    fig.add_trace(go.Scattermap(
                        lat=lat, lon=lon,
                        mode='lines', fill='toself',
                        fillcolor='rgba(100,100,255,0.15)',
                        line=dict(color='#6464ff', width=1),
                        name='No-Fly Zone',
                        hovertext=row.get('zone_type', 'No-Fly Zone'),
                        hoverinfo='text',
                        showlegend=False,
                    ))
    except Exception:
        pass

def get_station_faa_ceiling(lat, lon, faa_geojson):
    if not faa_geojson or 'features' not in faa_geojson: return "400 ft (Class G)"
    pt = Point(lon, lat)
    for feature in faa_geojson['features']:
        if 'geometry' in feature and feature['geometry']:
            try:
                s = shape(feature['geometry'])
                if s.contains(pt):
                    val = feature['properties'].get('CEILING')
                    if val is not None: return f"{val} ft (Controlled)"
            except Exception: pass
    return "400 ft (Class G)"

@st.cache_data
def fetch_airfields(minx, miny, maxx, maxy):
    """
    Fetch airfields — prefers cached US dataset, falls back to Overpass API.
    Much faster than querying Overpass per-region during app runtime.
    """
    # Try cached version first
    try:
        gdf_cached = load_cached_airfields()
        if not gdf_cached.empty:
            # Clip to bounding box with padding
            pad = 0.2
            bbox = box(minx-pad, miny-pad, maxx+pad, maxy+pad)
            clipped = gdf_cached[gdf_cached.geometry.intersects(bbox)]

            if not clipped.empty:
                airfields = []
                for _, row in clipped.iterrows():
                    airfields.append({
                        'name': row.get('name', 'Unknown Airfield'),
                        'lat': row.geometry.y,
                        'lon': row.geometry.x,
                        'iata': row.get('iata', ''),
                        'icao': row.get('icao', ''),
                    })
                return airfields
    except Exception:
        pass

    # Fallback: Query Overpass API (slower but works without pre-download)
    pad = 0.2
    query = f"""[out:json];(node["aeroway"~"aerodrome|heliport"]({miny-pad},{minx-pad},{maxy+pad},{maxx+pad});way["aeroway"~"aerodrome|heliport"]({miny-pad},{minx-pad},{maxy+pad},{maxx+pad}););out center;"""
    try:
        req = urllib.request.Request("https://overpass-api.de/api/interpreter", data=query.encode('utf-8'), headers={'User-Agent': 'BRINC_Optimizer'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            airfields = []
            for el in data.get('elements', []):
                lat = el.get('lat') or el.get('center', {}).get('lat')
                lon = el.get('lon') or el.get('center', {}).get('lon')
                name = el.get('tags', {}).get('name', 'Unknown Airfield')
                if lat and lon: airfields.append({'name': name, 'lat': lat, 'lon': lon})
            return airfields
    except Exception:
        return []

def get_nearest_airfield(lat, lon, airfields):
    if not airfields: return "No data"
    min_dist = float('inf')
    best = None
    for af in airfields:
        lat1, lon1, lat2, lon2 = map(math.radians, [lat, lon, af['lat'], af['lon']])
        a = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
        dist = 3958.8 * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        if dist < min_dist:
            y = math.sin(lon2-lon1)*math.cos(lat2)
            x = math.cos(lat1)*math.sin(lat2) - math.sin(lat1)*math.cos(lat2)*math.cos(lon2-lon1)
            bearing = (math.degrees(math.atan2(y, x)) + 360) % 360
            dirs = ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW']
            min_dist = dist
            best = (af['name'], dist, dirs[int((bearing+11.25)/22.5) % 16])
    if best:
        n = best[0][:18] + ("..." if len(best[0]) > 18 else "")
        return f"{best[1]:.1f}mi {best[2]} ({n})"
    return "No data"

def generate_random_points_in_polygon(polygon, num_points):
    # Flatten MultiPolygon to its largest component so bbox sampling stays efficient
    if isinstance(polygon, MultiPolygon):
        polygon = max(polygon.geoms, key=lambda p: p.area)
    points = []
    minx, miny, maxx, maxy = polygon.bounds
    while len(points) < num_points:
        x_coords = np.random.uniform(minx, maxx, 1000)
        y_coords = np.random.uniform(miny, maxy, 1000)
        for x, y in zip(x_coords, y_coords):
            if len(points) >= num_points: break
            if polygon.contains(Point(x, y)): points.append((y, x))
    return points

def generate_clustered_calls(polygon, num_points):
    if isinstance(polygon, MultiPolygon):
        polygon = max(polygon.geoms, key=lambda p: p.area)
    points = []
    minx, miny, maxx, maxy = polygon.bounds
    hotspots = []
    while len(hotspots) < random.randint(5, 15):
        hx, hy = random.uniform(minx, maxx), random.uniform(miny, maxy)
        if polygon.contains(Point(hx, hy)): hotspots.append((hx, hy))
    target_clustered = int(num_points * 0.75)
    while len(points) < target_clustered:
        hx, hy = random.choice(hotspots)
        px, py = np.random.normal(hx, 0.02), np.random.normal(hy, 0.02)
        if polygon.contains(Point(px, py)): points.append((py, px))
    while len(points) < num_points:
        px, py = random.uniform(minx, maxx), random.uniform(miny, maxy)
        if polygon.contains(Point(px, py)): points.append((py, px))
    np.random.shuffle(points)
    return points

def estimate_grants(population):
    if population > 1000000: return "$1.5M - $3.0M+"
    elif population > 500000: return "$500k - $1.5M"
    elif population > 250000: return "$250k - $500k"
    elif population > 100000: return "$100k - $250k"
    else: return "$25k - $100k"

def get_circle_coords(lat, lon, r_mi=2.0):
    angles = np.linspace(0, 2*np.pi, 100)
    c_lats = lat + (r_mi/69.172) * np.sin(angles)
    c_lons = lon + (r_mi/(69.172 * np.cos(np.radians(lat)))) * np.cos(angles)
    return c_lats, c_lons


# ── 4G LTE coverage overlay ───────────────────────────────────────────────────

_COVERAGE_CACHE: dict = {}   # {state_abbr: GeoDataFrame or None}

def _load_coverage(state_abbr: str):
    """Load cell_coverage/{STATE}.parquet; returns GeoDataFrame or None."""
    if state_abbr in _COVERAGE_CACHE:
        return _COVERAGE_CACHE[state_abbr]
    path = os.path.join("cell_coverage", f"{state_abbr}.parquet")
    if not os.path.exists(path):
        _COVERAGE_CACHE[state_abbr] = None
        return None
    try:
        import pyarrow.parquet as pq
        from shapely.wkb import loads as wkb_loads
        df = pd.read_parquet(path)
        df['geometry'] = df['geometry_wkb'].apply(lambda h: wkb_loads(bytes.fromhex(h)) if h else None)
        gdf = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:4326')
        _COVERAGE_CACHE[state_abbr] = gdf
        return gdf
    except Exception:
        _COVERAGE_CACHE[state_abbr] = None
        return None


def add_coverage_traces(fig, state_abbr: str, visible=True):
    """Add AT&T / T-Mobile / Verizon 4G LTE polygon traces."""
    gdf = _load_coverage(state_abbr)
    if gdf is None or gdf.empty:
        return

    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        carrier = row['carrier']
        color   = row['color']
        rings = []
        if geom.geom_type == 'Polygon':
            rings = [geom.exterior]
        elif geom.geom_type == 'MultiPolygon':
            rings = [p.exterior for p in geom.geoms]
        else:
            continue

        lons_all, lats_all = [], []
        for ring in rings:
            xs, ys = ring.coords.xy
            lons_all.extend(list(xs) + [None])
            lats_all.extend(list(ys) + [None])

        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        fig.add_trace(go.Scattermap(
            lon=lons_all, lat=lats_all,
            mode='lines', fill='toself',
            fillcolor=f"rgba({r},{g},{b},0.25)",
            line=dict(color=color, width=1),
            name=f"{carrier} 4G LTE",
            hoverinfo='name',
            visible=visible,
        ))


def _carrier_coverage_analysis(state_abbr: str, boundary_geom):
    """
    Intersects each carrier's dissolved polygon with the jurisdiction boundary.
    Returns list of dicts sorted by coverage % descending:
      {'carrier', 'color', 'pct', 'poly'}
    """
    if not state_abbr or boundary_geom is None or boundary_geom.is_empty:
        return []
    gdf = _load_coverage(state_abbr)
    if gdf is None or gdf.empty:
        return []

    boundary_area = boundary_geom.area
    if boundary_area <= 0:
        return []

    results = []
    for _, row in gdf.iterrows():
        poly = row.geometry
        if poly is None or poly.is_empty:
            results.append({'carrier': row['carrier'], 'color': row['color'], 'pct': 0.0, 'poly': None})
            continue
        try:
            clipped = poly.intersection(boundary_geom)
            pct = min(100.0, clipped.area / boundary_area * 100)
        except Exception:
            clipped = None
            pct = 0.0
        results.append({'carrier': row['carrier'], 'color': row['color'], 'pct': pct, 'poly': clipped})

    return sorted(results, key=lambda x: x['pct'], reverse=True)


def _build_carrier_mini_map(cinfo, boundary_geom, center_lat, center_lon, zoom, map_style):
    """Build a small Plotly map showing jurisdiction boundary + one carrier's coverage."""
    fig = go.Figure()

    # Jurisdiction outline
    if boundary_geom is not None and not boundary_geom.is_empty:
        geoms = [boundary_geom] if isinstance(boundary_geom, Polygon) else list(boundary_geom.geoms)
        for gi, g in enumerate(geoms):
            bx, by = g.exterior.coords.xy
            fig.add_trace(go.Scattermap(
                mode='lines', lon=list(bx), lat=list(by),
                line=dict(color='#ffffff', width=1.5),
                showlegend=False, hoverinfo='skip'
            ))

    # Coverage fill
    poly = cinfo.get('poly')
    if poly is not None and not poly.is_empty:
        color = cinfo['color']
        r, g_c, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        rings = ([poly.exterior] if poly.geom_type == 'Polygon'
                 else [p.exterior for p in poly.geoms])
        lons, lats = [], []
        for ring in rings:
            xs, ys = ring.coords.xy
            lons.extend(list(xs) + [None])
            lats.extend(list(ys) + [None])
        fig.add_trace(go.Scattermap(
            lon=lons, lat=lats, mode='lines', fill='toself',
            fillcolor=f"rgba({r},{g_c},{b},0.40)",
            line=dict(color=color, width=1),
            showlegend=False, hoverinfo='skip'
        ))

    fig.update_layout(
        map=dict(center=dict(lat=center_lat, lon=center_lon),
                 zoom=max(8, zoom - 1), style=map_style),
        margin=dict(l=0, r=0, t=0, b=0),
        height=210, showlegend=False,
    )
    return fig


# ── RF Link Budget — 3390 MHz Friis free-space model ─────────────────────────

def _rf_range_rings_3390(infra_height_m: float = 9.14,
                          drone_alt_m: float = 61.0,
                          clutter_db: float = 15.0,
                          tx_power_dbm: float = 33.0,
                          tx_gain_dbi: float = 3.0,
                          rx_gain_dbi: float = 3.0) -> list:
    """
    Returns list of (label, hex_color, radius_miles) for 3 SNR tiers at 3390 MHz.

    Link budget:
      FSPL = 20*log10(d_m) + 43.05  (at 3390 MHz)
      SNR  = tx_power + tx_gain + rx_gain - FSPL - noise_floor - clutter
           = EIRP + rx_gain - 43.05 - 20*log10(d) + 94 - clutter
    Noise floor: -174 + 10*log10(20e6 BW) + 7 NF = -94 dBm
    """
    import math as _math
    eirp = tx_power_dbm + tx_gain_dbi + rx_gain_dbi
    noise_floor_dbm = -94.0   # 20 MHz BW, 7 dB NF
    link_budget = eirp - 43.05 + abs(noise_floor_dbm) - clutter_db

    tiers = [
        ("Excellent (SNR ≥ 20 dB)", "#22c55e", 20),
        ("Good (SNR ≥ 10 dB)",      "#f59e0b", 10),
        ("Marginal (SNR ≥ 0 dB)",   "#ef4444",  0),
    ]
    rings = []
    for label, color, snr_thresh in tiers:
        d_m = 10 ** ((link_budget - snr_thresh) / 20.0)
        # Add height correction — effective slant range
        h_diff = abs(drone_alt_m - infra_height_m)
        d_horiz = max(0.0, _math.sqrt(max(0, d_m**2 - h_diff**2)))
        rings.append((label, color, d_horiz / 1609.34))  # convert to miles
    return rings


# ── ADVANCED GEOGRAPHY-AWARE RF COVERAGE ENGINE ──────────────────────────────────
# Coverage Probability model with terrain, clutter, building losses, uplink/downlink

import scipy.interpolate as _sp_interp
from scipy.spatial.distance import cdist as _cdist

@st.cache_resource
def _get_terrain_cache():
    """Global cache dict for DEM tiles to avoid re-downloading."""
    return {}

def _estimate_elevation_simple(lat, lon, cache=None):
    """Fetch elevation for a point (cached) — fallback to 100 ft if unavailable."""
    if cache is None:
        cache = {}
    key = (round(lat, 2), round(lon, 2))
    if key in cache:
        return cache[key]
    try:
        # Try OpenDEM API (no key required, open access)
        import urllib.request as _ur
        url = f"https://cloud.sdsc.edu/v1/AUTH_opentopography/Raster/SRTM_GL30/SRTM_GL30_Ellip/SRTM_GL30_Ellip_srtm.tif"
        # Fallback: use simple rule based on typical coastal vs inland
        elev = max(0, 100 + (lon % 1) * 50 - (lat % 1) * 30)  # Mock variation
    except Exception:
        elev = 100.0  # Default 100 ft mean elevation
    cache[key] = elev
    return elev

def _estimate_clutter_loss_db(lat, lon, land_use_class="suburban"):
    """
    Estimate clutter/foliage/building loss based on land-use class.
    Returns dB added to path loss (positive = attenuation).
    Simplified model; real impl would use GIS layers.
    """
    clutter_map = {
        "urban": {"base": 18.0, "var": 8.0},
        "suburban": {"base": 12.0, "var": 5.0},
        "rural": {"base": 6.0, "var": 3.0},
        "water": {"base": 2.0, "var": 1.0},
    }
    params = clutter_map.get(land_use_class, clutter_map["suburban"])
    # Add small pseudorandom variation based on coordinates
    var = (abs(lat * 137.5) % 1.0 + abs(lon * 173.2) % 1.0) / 2.0 * params["var"]
    return params["base"] + var

def _estimate_terrain_blockage_db(tx_lat, tx_lon, rx_lat, rx_lon, tx_alt_m, rx_alt_m):
    """
    Estimate terrain blockage loss using simple Fresnel zone calculation.
    If midpoint elevation is significantly above LOS, add loss.
    Returns dB penalty for terrain obstruction.
    """
    try:
        import math as _m
        # Midpoint
        mid_lat = (tx_lat + rx_lat) / 2.0
        mid_lon = (tx_lon + rx_lon) / 2.0

        # Distance
        lat_dist_m = (rx_lat - tx_lat) * 111000.0  # approx 111 km per degree latitude
        lon_dist_m = (rx_lon - tx_lon) * 111000.0 * _m.cos(_m.radians((tx_lat + rx_lat) / 2.0))
        horiz_dist = _m.sqrt(lat_dist_m**2 + lon_dist_m**2)

        if horiz_dist < 100:  # Too close, skip terrain calc
            return 0.0

        # Fresnel radius at midpoint
        freq_hz = 3.39e9  # 3390 MHz
        fresnel_r = _m.sqrt(0.5 * 3e8 / freq_hz * horiz_dist)

        # Estimate elevations (simple proxy)
        tx_elev = _estimate_elevation_simple(tx_lat, tx_lon)
        rx_elev = _estimate_elevation_simple(rx_lat, rx_lon)
        mid_elev = _estimate_elevation_simple(mid_lat, mid_lon)

        # LOS line from tx to rx
        tx_height = tx_elev + tx_alt_m
        rx_height = rx_elev + rx_alt_m
        los_height_at_mid = (tx_height + rx_height) / 2.0

        # Blockage: if terrain > 0.6 Fresnel radius above LOS, add loss
        blockage_m = max(0, mid_elev - los_height_at_mid)
        blockage_ratio = blockage_m / max(1.0, fresnel_r)

        # Knife-edge diffraction approximation
        if blockage_ratio > 0.1:
            loss_db = 6.0 * blockage_ratio**2  # ITM-style knife-edge loss
        else:
            loss_db = 0.0

        return min(25.0, loss_db)  # Cap at 25 dB
    except Exception:
        return 0.0

def _path_loss_advanced(distance_m, freq_mhz=3390, tx_alt_m=9.14, rx_alt_m=61.0,
                        tx_lat=None, tx_lon=None, rx_lat=None, rx_lon=None,
                        land_use="suburban"):
    """
    Advanced path loss model combining multiple effects:
      PL_total = FSPL + clutter_loss + terrain_loss + fade_margin

    where:
      FSPL = 20*log10(d) + 20*log10(f_mhz) + 27.55
      clutter_loss = function of land use
      terrain_loss = function of elevation difference and blockage
      fade_margin = 3 dB (flat fading margin)
    """
    import math as _m

    if distance_m < 10:
        return 0.0  # No loss at very short range

    # Free-space path loss
    fspl = 20.0 * _m.log10(distance_m) + 20.0 * _m.log10(freq_mhz) + 27.55

    # Clutter loss
    clutter_db = _estimate_clutter_loss_db(tx_lat, tx_lon, land_use) if tx_lat else 0.0

    # Terrain/blockage loss (if we have coordinates)
    terrain_db = 0.0
    if tx_lat and tx_lon and rx_lat and rx_lon:
        terrain_db = _estimate_terrain_blockage_db(tx_lat, tx_lon, rx_lat, rx_lon,
                                                   tx_alt_m, rx_alt_m)

    # Fade margin (Rayleigh/urban multipath)
    fade_db = 3.0

    total_pl = fspl + clutter_db + terrain_db + fade_db
    return total_pl

def _compute_rf_grid_coverage(tx_lat, tx_lon, tx_alt_m,
                              boundary_geom=None,
                              freq_mhz=3390,
                              tx_power_dbm=33.0,
                              tx_gain_dbi=3.0,
                              rx_gain_dbi=3.0,
                              noise_figure_db=7.0,
                              bandwidth_mhz=20.0,
                              land_use="suburban",
                              grid_resolution_m=250):
    """
    Compute coverage probability grid for a single station.

    Returns: grid_dict = {
        'lats': array, 'lons': array,
        'coverage_prob': 2D array,  # probability of successful link (uplink OR downlink)
        'uplink_prob': 2D array,
        'downlink_prob': 2D array,
        'snr_db': 2D array,
        'rx_power_dbm': 2D array,
    }
    """
    import math as _m
    import numpy as _np

    # Get boundary extent
    if boundary_geom is None or boundary_geom.is_empty:
        # Default ~5 mile radius around station
        dlat = 5 / 69.0  # 1 degree latitude ~ 69 miles
        dlon = 5 / (69.0 * _m.cos(_m.radians(tx_lat)))
        minx, miny = tx_lon - dlon, tx_lat - dlat
        maxx, maxy = tx_lon + dlon, tx_lat + dlat
    else:
        minx, miny, maxx, maxy = boundary_geom.bounds

    # Build grid
    lat_count = max(10, int((maxy - miny) * 111000 / grid_resolution_m))
    lon_count = max(10, int((maxx - minx) * 111000 * _m.cos(_m.radians((miny + maxy) / 2)) / grid_resolution_m))

    lats = _np.linspace(miny, maxy, lat_count)
    lons = _np.linspace(minx, maxx, lon_count)
    lon_grid, lat_grid = _np.meshgrid(lons, lats)

    # Noise floor calculation
    noise_floor_dbm = -174 + 10.0 * _m.log10(bandwidth_mhz * 1e6) + noise_figure_db

    # EIRP
    eirp_dbm = tx_power_dbm + tx_gain_dbi

    # Storage
    uplink_prob = _np.zeros_like(lon_grid)  # Drone TX to infra RX
    downlink_prob = _np.zeros_like(lon_grid)  # Infra TX to drone RX
    snr_db_grid = _np.zeros_like(lon_grid)
    rx_power_grid = _np.zeros_like(lon_grid)

    # Compute for each grid cell
    rx_alt_m = 61.0  # Drone altitude in meters (200 ft)
    infra_alt_m = _estimate_elevation_simple(tx_lat, tx_lon)  # Ground elevation at station

    for i in range(lat_count):
        for j in range(lon_count):
            grid_lat, grid_lon = lat_grid[i, j], lon_grid[i, j]

            # Skip if outside boundary
            if boundary_geom and not boundary_geom.is_empty:
                pt = Point(grid_lon, grid_lat)
                if not boundary_geom.contains(pt):
                    continue

            # Distance
            lat_dist = (grid_lat - tx_lat) * 111000.0
            lon_dist = (grid_lon - tx_lon) * 111000.0 * _m.cos(_m.radians((tx_lat + grid_lat) / 2))
            horiz_dist = _m.sqrt(lat_dist**2 + lon_dist**2)

            # Slant distances (assuming drone at rx_alt above grid point)
            grid_elev = _estimate_elevation_simple(grid_lat, grid_lon)
            drone_height = grid_elev + rx_alt_m
            infra_height = infra_alt_m + tx_alt_m
            slant_dist_uplink = _m.sqrt(horiz_dist**2 + (drone_height - infra_height)**2)
            slant_dist_downlink = slant_dist_uplink  # Same path

            # Path loss
            pl_uplink = _path_loss_advanced(slant_dist_uplink, freq_mhz, tx_alt_m, rx_alt_m,
                                           tx_lat, tx_lon, grid_lat, grid_lon, land_use)
            pl_downlink = _path_loss_advanced(slant_dist_downlink, freq_mhz, rx_alt_m, tx_alt_m,
                                             grid_lat, grid_lon, tx_lat, tx_lon, land_use)

            # Received power (uplink: drone TX)
            rx_pwr_uplink = eirp_dbm + rx_gain_dbi - pl_uplink
            # Received power (downlink: infra TX)
            rx_pwr_downlink = eirp_dbm + rx_gain_dbi - pl_downlink

            # SNR
            snr_uplink = rx_pwr_uplink - noise_floor_dbm
            snr_downlink = rx_pwr_downlink - noise_floor_dbm

            # Coverage probability (simple model: P = 1 / (1 + 10^(-SNR/10)))
            # i.e., logistic CDF of SNR with threshold at 0 dB
            snr_threshold = 3.0  # Need ≥3 dB for 50% link success
            if snr_uplink > snr_threshold:
                uplink_prob[i, j] = 1.0 / (1.0 + 10.0 ** (-(snr_uplink - snr_threshold) / 10.0))
            if snr_downlink > snr_threshold:
                downlink_prob[i, j] = 1.0 / (1.0 + 10.0 ** (-(snr_downlink - snr_threshold) / 10.0))

            snr_db_grid[i, j] = min(snr_uplink, snr_downlink)  # Combined SNR
            rx_power_grid[i, j] = max(rx_pwr_uplink, rx_pwr_downlink)

    # Combined coverage = both uplink AND downlink must work
    coverage_prob = uplink_prob * downlink_prob

    return {
        'lats': lats,
        'lons': lons,
        'coverage_prob': coverage_prob,
        'uplink_prob': uplink_prob,
        'downlink_prob': downlink_prob,
        'snr_db': snr_db_grid,
        'rx_power_dbm': rx_power_grid,
    }

def _plot_rf_coverage_heatmap(grid_data, station_name, center_lat, center_lon, zoom,
                              layer_type='coverage_prob', link_type='combined',
                              map_style="carto-darkmatter"):
    """
    Plot RF coverage as a Plotly heatmap overlay.

    layer_type: 'coverage_prob', 'snr_db', 'rx_power_dbm'
    link_type: 'uplink', 'downlink', 'combined'
    """
    lats = grid_data['lats']
    lons = grid_data['lons']

    if layer_type == 'coverage_prob':
        if link_type == 'uplink':
            z_data = grid_data['uplink_prob']
            title = "Uplink Coverage Probability"
            colorscale = "Viridis"
        elif link_type == 'downlink':
            z_data = grid_data['downlink_prob']
            title = "Downlink Coverage Probability"
            colorscale = "Viridis"
        else:  # combined
            z_data = grid_data['coverage_prob']
            title = "Combined Coverage Probability"
            colorscale = "Viridis"
    elif layer_type == 'snr_db':
        z_data = grid_data['snr_db']
        title = "Signal to Noise Ratio (dB)"
        colorscale = "RdYlGn"
    else:  # rx_power_dbm
        z_data = grid_data['rx_power_dbm']
        title = "Received Power (dBm)"
        colorscale = "Turbo"

    fig = go.Figure()

    # Add heatmap
    fig.add_trace(go.Heatmap(
        z=z_data,
        x=lons,
        y=lats,
        colorscale=colorscale,
        colorbar=dict(title=title.split('(')[0].strip()),
        hovertemplate="Lat: %{y:.4f}<br>Lon: %{x:.4f}<br>Value: %{z:.2f}<extra></extra>",
        name=title,
    ))

    fig.update_layout(
        title=f"{station_name} · {title}",
        xaxis_title="Longitude",
        yaxis_title="Latitude",
        height=500,
        margin=dict(l=50, r=50, t=60, b=50),
    )

    return fig
