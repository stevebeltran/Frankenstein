"""
download_and_build_places.py
============================
Downloads all 51 Census TIGER 2023 place shapefiles from the FTP server,
then builds places_lite.parquet for use in the Frankenstein app.

Run from your Frankenstein repo folder:
    python3 download_and_build_places.py

Output:
    places_lite.parquet  (put this next to counties_lite.parquet)
"""

import io, os, glob, shutil, zipfile, urllib.request
import geopandas as gpd
import pandas as pd
from shapely.validation import make_valid

YEAR = "2023"
FTP_BASE = f"https://www2.census.gov/geo/tiger/TIGER{YEAR}/PLACE/"

STATE_FIPS = [
    "01","02","04","05","06","08","09","10","11","12",
    "13","15","16","17","18","19","20","21","22","23",
    "24","25","26","27","28","29","30","31","32","33",
    "34","35","36","37","38","39","40","41","42","44",
    "45","46","47","48","49","50","51","53","54","55","56",
]

CACHE_DIR = "tiger_place_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

all_gdfs = []

for i, fips in enumerate(STATE_FIPS, 1):
    filename = f"tl_{YEAR}_{fips}_place.zip"
    url      = FTP_BASE + filename
    zip_path = os.path.join(CACHE_DIR, filename)
    tmp_dir  = os.path.join(CACHE_DIR, f"extracted_{fips}")

    # ── Download (skip if already cached) ──────────────────────────────────
    if not os.path.exists(zip_path):
        print(f"[{i:2d}/51] Downloading {filename} ...", end=" ", flush=True)
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "BRINC_places_builder/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                with open(zip_path, "wb") as f:
                    f.write(resp.read())
            print("downloaded")
        except Exception as e:
            print(f"FAILED: {e}")
            continue
    else:
        print(f"[{i:2d}/51] {filename} already cached")

    # ── Extract ─────────────────────────────────────────────────────────────
    try:
        os.makedirs(tmp_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp_dir)
        shp = glob.glob(os.path.join(tmp_dir, "*.shp"))[0]
    except Exception as e:
        print(f"  Extract failed: {e}")
        continue

    # ── Read + simplify ─────────────────────────────────────────────────────
    try:
        gdf = gpd.read_file(shp)
        keep = [c for c in ["STATEFP","NAME","NAMELSAD","geometry"] if c in gdf.columns]
        gdf  = gdf[keep].copy()
        gdf["geometry"] = gdf["geometry"].apply(
            lambda g: make_valid(g).simplify(0.0005, preserve_topology=True)
            if g is not None and not g.is_empty else g
        )
        gdf = gdf[gdf["geometry"].notna() & ~gdf["geometry"].is_empty]
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
        all_gdfs.append(gdf)
        print(f"  → {len(gdf):,} places")
    except Exception as e:
        print(f"  Read failed: {e}")

    # Clean up extracted folder (keep the zip for caching)
    shutil.rmtree(tmp_dir, ignore_errors=True)

# ── Merge & save ────────────────────────────────────────────────────────────
print(f"\nMerging {len(all_gdfs)} states ...", flush=True)
combined = gpd.GeoDataFrame(pd.concat(all_gdfs, ignore_index=True), crs="EPSG:4326")
print(f"Total places: {len(combined):,}")

out = "places_lite.parquet"
combined.to_parquet(out, compression="snappy", index=False)
size_mb = os.path.getsize(out) / 1024 / 1024
print(f"\nSaved: {out}  ({size_mb:.1f} MB)")

# ── Sanity check ────────────────────────────────────────────────────────────
for name, sfips in [("Victoria TX", "48"), ("Rockford IL", "17"),
                    ("Orlando FL", "12"), ("Durham NC", "37")]:
    city = name.split()[0]
    rows = combined[(combined["STATEFP"] == sfips) &
                    (combined["NAME"].str.lower() == city.lower())]
    print(f"  {name}: {'✅ found' if len(rows) else '❌ NOT FOUND'}")

print(f"\nDone! Copy {out} into your Frankenstein repo folder next to counties_lite.parquet")
