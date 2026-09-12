#!/usr/bin/env python3
"""
Download and Build Canada Boundary Lite Parquet Files
======================================================

One-off data-prep script: downloads StatCan cartographic boundary files
(provinces/territories, census divisions, census subdivisions) and StatCan
population/dwelling counts, simplifies geometry, and writes the bundled
"lite" parquet files the app reads at runtime — mirrors how
counties_lite.parquet / places_lite.parquet were built for the US path.

Run this once when Canada boundary data needs to be (re)built. NOT called
at app runtime.

Usage:
  python download_ca_boundary_layers.py

Output (repo root):
  provinces_lite.parquet   (PRUID, NAME, POPULATION, geometry)
  cd_lite.parquet          (PRUID, NAME, POPULATION, geometry)
  csd_lite.parquet         (PRUID, NAME, NAMELSAD, POPULATION, geometry)

Before running: confirm the boundary-file URLs below still match StatCan's
current index (https://www12.statcan.gc.ca/census-recensement/2021/geo/
sip-pis/boundary-limites/index-eng.cfm) — StatCan occasionally moves files
when a new boundary vintage is published, the same reason
modules/boundaries.py tries multiple TIGER years for the US path. If a
column referenced below (e.g. CDNAME) is missing after download, print
`gdf.columns.tolist()` and add the real name to the candidate list in
`_first_present`.

Population data note
---------------------
StatCan table 98-10-0001 ("Population and dwelling counts: Canada,
provinces and territories") only covers the 13 province/territory rows —
not enough to attach population to census divisions or census
subdivisions. Table 98-10-0002 ("Population and dwelling counts: Canada,
provinces and territories, census divisions and census subdivisions")
contains the full hierarchy (Canada + provinces + CDs + CSDs, ~5,468 rows)
in one CSV, so this script uses that table for every level instead.

That table is also "wide" (one column per stat/year, e.g. "Population and
dwelling counts (13): Population, 2021 [1]") rather than the tidy
GEO/VALUE shape a StatCan "add data point -> download" CSV usually has, so
the 2021 population column is located by substring match instead of an
exact-name candidate list.

Roughly 290 names (e.g. "Division No.  1", which is reused by several
provinces, or "Victoria") are not unique across all of Canada, so a plain
name->population dict would silently misattribute population for those
rows. The population table's DGUID column encodes the 2-digit PRUID at a
fixed offset for every sub-Canada row (schema prefix "2021A000<N>" is
always 9 characters, so characters [9:11] are the PRUID for provinces,
CDs, and CSDs alike) — that lets us build a (PRUID, name) composite key
that disambiguates duplicate names, with a name-only fallback for any
row that still misses (e.g. minor punctuation/spacing drift between the
two datasets).

CRS note
--------
The StatCan boundary shapefiles are delivered in EPSG:3347 (Statistics
Canada Lambert Conformal Conic, coordinates in metres), not EPSG:4326.
Geometry is simplified in that native metre CRS FIRST (see
`_simplify_then_reproject`), then reprojected to EPSG:4326 for storage —
simplifying only after reprojecting would mean transforming Canada's full,
enormously detailed Arctic-archipelago coastline through pyproj before
any vertex reduction, which is far slower, and a degrees tolerance is not
a uniform real-world distance at Canada's latitudes anyway.

File-size note (why there's an island-area filter below)
----------------------------------------------------------
Simplifying vertex density alone is not enough to hit a reasonable bundle
size for Canada: Canada's provinces/CDs/CSDs are riddled with tens of
thousands of small islands and lake-islands (Nunavut alone contributes
62,547 separate polygon rings, even after 100m simplification), and
Douglas-Peucker simplification reduces vertices *along* a ring but never
removes a whole ring, however small. That leaves a large fixed "floor" of
tiny 4-8 vertex rings no amount of extra SIMPLIFY_TOLERANCE_METERS budges.
This is a real characteristic of Canadian geography (nothing comparable
exists in the US TIGER counties/places files this pipeline mirrors), so
the fix is the standard cartographic-generalization technique of dropping
the smallest polygon parts of each feature outright: parts smaller than
MIN_ISLAND_AREA_M2 are dropped (falling back to the single largest part if
every part of a feature is that small, so no feature ever loses its
geometry entirely). At the chosen 1 km^2 threshold this drops ~97% of
Nunavut's polygon count while retaining 99.87% of its area — i.e. it
discards uninhabited slivers, not meaningful landmass. If Task 4 or a
later task needs those small islands preserved (e.g. exact point-in-polygon
correctness for a real flight over a tiny islet), lower or remove this
filter and accept a larger bundle instead.
"""
import io
import os
import zipfile
import glob
import urllib.request

import geopandas as gpd
import pandas as pd

STATCAN_BASE = "https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/files-fichiers"
BOUNDARY_FILES = {
    "province": f"{STATCAN_BASE}/lpr_000b21a_e.zip",
    "cd": f"{STATCAN_BASE}/lcd_000b21a_e.zip",
    "csd": f"{STATCAN_BASE}/lcsd000b21a_e.zip",
}

# StatCan "Population and dwelling counts" (2021 Census), full table CSV download.
# NOTE: table 98-10-0001 (the brief's original source) only has the 13
# province/territory rows. 98-10-0002 has the same stats for Canada,
# provinces/territories, census divisions, AND census subdivisions in one
# table (~5,468 rows), so we use it for all three geography levels.
POPULATION_CSV_URL = "https://www150.statcan.gc.ca/n1/tbl/csv/98100002-eng.zip"

SIMPLIFY_TOLERANCE_DEGREES = 0.001  # ~100m — matches the visual detail of the existing US lite files
# Simplify is applied BEFORE reprojection, in the source CRS's native metres
# (see _to_wgs84 below), so this is the metre-equivalent of
# SIMPLIFY_TOLERANCE_DEGREES (~100m). Doing it in this order is both faster
# (vertex count drops before the expensive per-vertex reprojection instead of
# after) and more correct (a degrees tolerance is not a uniform real-world
# distance at Canada's latitudes, whereas metres in EPSG:3347 are).
SIMPLIFY_TOLERANCE_METERS = 100
# See "File-size note" above. 1 km^2: empirically drops ~97% of Nunavut's
# polygon-ring count while keeping 99.87% of its area.
MIN_ISLAND_AREA_M2 = 1_000_000
TEMP_DIR = "temp_ca_boundary_download"


def _safe_extractall(zip_file, dest_dir):
    root = os.path.abspath(dest_dir)
    for member in zip_file.namelist():
        target = os.path.abspath(os.path.join(root, member))
        if target != root and not target.startswith(root + os.sep):
            raise ValueError(f"Unsafe path in archive: {member}")
    zip_file.extractall(dest_dir)


def _download_and_extract(url, dest_dir):
    req = urllib.request.Request(url, headers={"User-Agent": "BRINC_COS_Optimizer/1.0"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        zip_data = resp.read()
    zf = zipfile.ZipFile(io.BytesIO(zip_data))
    os.makedirs(dest_dir, exist_ok=True)
    _safe_extractall(zf, dest_dir)
    shp_files = glob.glob(os.path.join(dest_dir, "*.shp"))
    if not shp_files:
        raise RuntimeError(f"No .shp found after extracting {url}")
    return gpd.read_file(shp_files[0])


def _drop_tiny_parts(geom, min_area):
    """Drop constituent polygon parts smaller than `min_area` (in the
    geometry's current CRS units — call this before reprojecting out of a
    metres CRS so the threshold means what it says). Falls back to keeping
    the single largest part so a feature never loses its geometry entirely
    (e.g. a small province/territory that is legitimately all small
    islands)."""
    if geom.geom_type != "MultiPolygon":
        return geom
    parts = [p for p in geom.geoms if p.area >= min_area]
    if not parts:
        parts = [max(geom.geoms, key=lambda p: p.area)]
    return parts[0] if len(parts) == 1 else type(geom)(parts)


def _simplify_then_reproject(gdf):
    """StatCan boundary files ship in a projected CRS (EPSG:3347, Statistics
    Canada Lambert Conformal Conic — coordinates in metres), not lat/lon
    degrees. Simplify while still in that native metre CRS (cheap and a
    real-distance tolerance), THEN reproject the already-thinned geometry to
    EPSG:4326 for storage/display. Simplifying only after reprojecting would
    mean transforming full-resolution geometry (Canada's Arctic archipelago
    has an enormous vertex count) through pyproj first, which is far slower
    and, at a fixed degrees tolerance, not a uniform real-world distance at
    Canada's latitudes anyway."""
    print(f"[CA boundary prep]   source CRS: {gdf.crs}")
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=3347)
    gdf = gdf.copy()
    gdf["geometry"] = gdf["geometry"].apply(lambda g: _drop_tiny_parts(g, MIN_ISLAND_AREA_M2))
    gdf["geometry"] = gdf["geometry"].simplify(SIMPLIFY_TOLERANCE_METERS, preserve_topology=True)
    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    # simplify + dropping tiny parts can occasionally leave a small fraction
    # of features with minor self-intersections; buffer(0) is the standard
    # no-op-on-valid-shapes repair for that.
    invalid = ~gdf.geometry.is_valid
    if invalid.any():
        gdf.loc[invalid, "geometry"] = gdf.loc[invalid, "geometry"].buffer(0)
    return gdf


def _first_present(columns, candidates):
    for c in candidates:
        if c in columns:
            return c
    raise KeyError(f"None of {candidates} found in columns {list(columns)}")


def _first_present_substr(columns, substrings):
    """Like _first_present, but matches by substring — StatCan's wide-format
    table CSVs embed a variable cube-total count and column index in the
    header (e.g. "Population and dwelling counts (13): Population, 2021
    [1]"), so an exact-name candidate list is too brittle."""
    for sub in substrings:
        matches = [c for c in columns if sub in c]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise KeyError(f"Substring {sub!r} matched multiple columns: {matches}")
    raise KeyError(f"None of substrings {substrings} found in columns {list(columns)}")


def _load_population_lookup():
    req = urllib.request.Request(POPULATION_CSV_URL, headers={"User-Agent": "BRINC_COS_Optimizer/1.0"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        zip_data = resp.read()
    zf = zipfile.ZipFile(io.BytesIO(zip_data))
    os.makedirs(TEMP_DIR, exist_ok=True)
    csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv") and "metadata" not in n.lower()]
    zf.extractall(TEMP_DIR, members=csv_names)
    df = pd.read_csv(os.path.join(TEMP_DIR, csv_names[0]), low_memory=False)

    geo_col = _first_present(df.columns, ["GEO_NAME", "Geography", "GEO"])
    dguid_col = _first_present(df.columns, ["DGUID"])
    val_col = _first_present_substr(df.columns, ["Population, 2021"])

    df = df[df[val_col].notna()].copy()
    df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
    df = df[df[val_col].notna()]

    # DGUID schema prefix ("2021A0002" for province, "2021A0003" for CD,
    # "2021A0005" for CSD) is always 9 characters, so [9:11] is the 2-digit
    # PRUID for every row except the single national "Canada" row (which we
    # don't need — it's not present in any of the three boundary layers).
    dguid_str = df[dguid_col].astype(str)
    has_pruid = dguid_str.str.len() >= 11
    df = df[has_pruid].copy()
    df["_PRUID"] = dguid_str[has_pruid].str.slice(9, 11)

    composite = df.groupby(["_PRUID", geo_col])[val_col].first().to_dict()
    by_name = df.groupby(geo_col)[val_col].first().to_dict()
    return {"composite": composite, "by_name": by_name}


def _attach_population(gdf, name_col, population_lookup):
    gdf = gdf.copy()
    composite = population_lookup["composite"]
    by_name = population_lookup["by_name"]

    def _lookup(row):
        key = (str(row["PRUID"]), row[name_col])
        if key in composite:
            return composite[key]
        return by_name.get(row[name_col], 0)

    gdf["POPULATION"] = gdf.apply(_lookup, axis=1)
    gdf["POPULATION"] = pd.to_numeric(gdf["POPULATION"], errors="coerce").fillna(0).astype(int)
    return gdf


def build_provinces_lite(population_lookup):
    gdf = _download_and_extract(BOUNDARY_FILES["province"], os.path.join(TEMP_DIR, "province"))
    pruid_col = _first_present(gdf.columns, ["PRUID"])
    name_col = _first_present(gdf.columns, ["PRENAME", "PRNAME", "PRFNAME"])
    gdf = gdf.rename(columns={pruid_col: "PRUID", name_col: "NAME"})
    gdf = _simplify_then_reproject(gdf)
    gdf = _attach_population(gdf, "NAME", population_lookup)
    out = gdf[["PRUID", "NAME", "POPULATION", "geometry"]]
    out.to_parquet("provinces_lite.parquet")
    return out


def build_cd_lite(population_lookup):
    gdf = _download_and_extract(BOUNDARY_FILES["cd"], os.path.join(TEMP_DIR, "cd"))
    pruid_col = _first_present(gdf.columns, ["PRUID"])
    name_col = _first_present(gdf.columns, ["CDNAME"])
    gdf = gdf.rename(columns={pruid_col: "PRUID", name_col: "NAME"})
    gdf = _simplify_then_reproject(gdf)
    gdf = _attach_population(gdf, "NAME", population_lookup)
    out = gdf[["PRUID", "NAME", "POPULATION", "geometry"]]
    out.to_parquet("cd_lite.parquet")
    return out


def build_csd_lite(population_lookup):
    gdf = _download_and_extract(BOUNDARY_FILES["csd"], os.path.join(TEMP_DIR, "csd"))
    pruid_col = _first_present(gdf.columns, ["PRUID"])
    name_col = _first_present(gdf.columns, ["CSDNAME"])
    type_col = _first_present(gdf.columns, ["CSDTYPE"])
    gdf = gdf.rename(columns={pruid_col: "PRUID", name_col: "NAME"})
    gdf["NAMELSAD"] = gdf["NAME"] + " (" + gdf[type_col].astype(str) + ")"
    gdf = _simplify_then_reproject(gdf)
    gdf = _attach_population(gdf, "NAME", population_lookup)
    out = gdf[["PRUID", "NAME", "NAMELSAD", "POPULATION", "geometry"]]
    out.to_parquet("csd_lite.parquet")
    return out


if __name__ == "__main__":
    print("[CA boundary prep] downloading population lookup...")
    population_lookup = _load_population_lookup()
    print("[CA boundary prep] building provinces_lite.parquet...")
    build_provinces_lite(population_lookup)
    print("[CA boundary prep] building cd_lite.parquet...")
    build_cd_lite(population_lookup)
    print("[CA boundary prep] building csd_lite.parquet...")
    build_csd_lite(population_lookup)
    print("[CA boundary prep] done.")
