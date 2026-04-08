#!/usr/bin/env python3
"""
FCC BDC 4G LTE Coverage Converter
====================================
Converts per-state carrier zip files downloaded by fcc_download_playwright.py
into per-state GeoParquet files for use in the BRINC app.

Input:  cell_coverage/raw/{STATE}_{CARRIER}.zip  (e.g. AL_ATT.zip)
Output: cell_coverage/{STATE}.parquet

Usage:
  python download_fcc_coverage.py

Requirements (all in requirements.txt):
  pip install geopandas pyarrow tqdm
"""

import io, re, sys, zipfile, traceback, tempfile, os
from pathlib import Path
from collections import defaultdict

import geopandas as gpd
import pandas as pd
from shapely.ops import unary_union

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **kw): return it

# ─── CONFIG ───────────────────────────────────────────────────────────────────

RAW_DIR    = Path("cell_coverage/raw")
OUTPUT_DIR = Path("cell_coverage")
OUTPUT_DIR.mkdir(exist_ok=True)

# FCC technology codes for 4G LTE
LTE_CODES = {"300", "400"}

CARRIER_COLORS = {
    "ATT":     "#00A8E0",
    "TMobile": "#E20074",
    "Verizon": "#CD040B",
}

CARRIER_LABELS = {
    "ATT":     "AT&T",
    "TMobile": "T-Mobile",
    "Verizon": "Verizon",
}

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def read_shapefile_from_zip(zip_path: Path) -> gpd.GeoDataFrame | None:
    """Read the first shapefile or GeoPackage found inside a zip."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()

            # Prefer shapefile
            shp_files = [n for n in names if n.lower().endswith(".shp")]
            gpkg_files = [n for n in names if n.lower().endswith(".gpkg")]

            if shp_files:
                base = shp_files[0].replace(".shp", "")
                with tempfile.TemporaryDirectory() as tmp:
                    for ext in [".shp", ".dbf", ".prj", ".shx", ".cpg"]:
                        member = base + ext
                        if member in names:
                            zf.extract(member, tmp)
                    shp_path = os.path.join(tmp, shp_files[0])
                    return gpd.read_file(shp_path)

            elif gpkg_files:
                with zf.open(gpkg_files[0]) as f:
                    return gpd.read_file(io.BytesIO(f.read()))

            else:
                print(f"    No .shp or .gpkg in {zip_path.name} — contents: {names[:5]}")
                return None

    except Exception as e:
        print(f"    Error reading {zip_path.name}: {e}")
        return None


def find_col(gdf: gpd.GeoDataFrame, candidates: list) -> str | None:
    """Find first matching column (case-insensitive)."""
    lower_map = {c.lower(): c for c in gdf.columns}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


def process_zip(zip_path: Path, state: str, carrier_key: str) -> gpd.GeoDataFrame | None:
    """
    Read one state/carrier zip, filter for LTE, return dissolved GeoDataFrame.
    """
    gdf = read_shapefile_from_zip(zip_path)
    if gdf is None or gdf.empty:
        return None

    gdf.columns = [c.lower() for c in gdf.columns]

    # Filter for LTE technology codes
    tech_col = find_col(gdf, ["technology", "tech_code", "tech", "techcode"])
    if tech_col:
        before = len(gdf)
        gdf = gdf[gdf[tech_col].astype(str).str.strip().isin(LTE_CODES)]
        if gdf.empty:
            return None

    # Ensure WGS84
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")

    # Fix geometries
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    gdf.geometry = gdf.geometry.buffer(0)

    if gdf.empty:
        return None

    # Dissolve all rows into a single coverage polygon
    merged = unary_union(gdf.geometry)

    # Simplify to ~1km tolerance — sufficient for city-level map display,
    # reduces vertex count by ~95% and keeps parquet files under 10 MB each.
    merged = merged.simplify(tolerance=0.01, preserve_topology=True)

    return gpd.GeoDataFrame(
        [{
            "state":   state,
            "carrier": CARRIER_LABELS[carrier_key],
            "color":   CARRIER_COLORS[carrier_key],
        }],
        geometry=[merged],
        crs="EPSG:4326",
    )


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    if not RAW_DIR.exists():
        print(f"ERROR: {RAW_DIR} does not exist.")
        print("Run fcc_download_playwright.py first.")
        sys.exit(1)

    # Discover all downloaded zip files: {STATE}_{CARRIER}.zip
    zip_files = sorted(RAW_DIR.glob("*.zip"))
    if not zip_files:
        print(f"No zip files found in {RAW_DIR}")
        sys.exit(1)

    print(f"Found {len(zip_files)} zip files in {RAW_DIR}\n")

    # Parse filenames → group by state
    # Expected pattern: {STATE_ABBR}_{CARRIER_KEY}.zip  e.g. AL_ATT.zip
    pattern = re.compile(r"^([A-Z]{2})_(ATT|TMobile|Verizon)\.zip$", re.IGNORECASE)
    state_carrier_map: dict[str, list[tuple[str, Path]]] = defaultdict(list)

    skipped = []
    for zp in zip_files:
        m = pattern.match(zp.name)
        if m:
            state, carrier = m.group(1).upper(), m.group(2)
            # Normalize carrier key capitalisation
            carrier = next((k for k in CARRIER_COLORS if k.lower() == carrier.lower()), carrier)
            state_carrier_map[state].append((carrier, zp))
        else:
            skipped.append(zp.name)

    if skipped:
        print(f"Skipped (unrecognised filename pattern): {skipped}\n")

    states = sorted(state_carrier_map.keys())
    print(f"Processing {len(states)} states …\n")

    written = 0
    failed  = []

    for state in tqdm(states, desc="States"):
        out_path = OUTPUT_DIR / f"{state}.parquet"

        entries = state_carrier_map[state]
        gdfs = []

        for carrier_key, zip_path in entries:
            try:
                gdf = process_zip(zip_path, state, carrier_key)
                if gdf is not None and not gdf.empty:
                    gdfs.append(gdf)
            except Exception as e:
                print(f"\n  {state}/{carrier_key}: ERROR — {e}")
                traceback.print_exc()
                failed.append(f"{state}/{carrier_key}")

        if not gdfs:
            print(f"\n  {state}: no LTE data found in any carrier zip — skipping.")
            continue

        combined = gpd.GeoDataFrame(
            pd.concat(gdfs, ignore_index=True), crs="EPSG:4326"
        )

        # Save geometry as WKB hex (standard Parquet doesn't store geometry natively)
        df = combined.copy()
        df["geometry_wkb"] = df.geometry.apply(lambda g: g.wkb_hex if g else None)
        df.drop(columns="geometry").to_parquet(
            out_path, index=False, engine="pyarrow", compression="snappy"
        )
        written += 1

    print(f"\n{'='*60}")
    print(f"Done. {written}/{len(states)} state files written to {OUTPUT_DIR.resolve()}")
    if failed:
        print(f"Errors: {', '.join(failed)}")
    print("\nNext step: push cell_coverage/*.parquet to GitHub,")
    print("then I'll wire the coverage overlay into app.py.")


if __name__ == "__main__":
    main()
