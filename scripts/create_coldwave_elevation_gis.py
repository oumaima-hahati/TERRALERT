#!/usr/bin/env python3
"""TERRALERT: cold-wave statistics and DEM zonal analysis."""

import csv
import shutil
import sqlite3
from pathlib import Path

import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.features import geometry_mask
from shapely import wkb
from shapely.geometry import mapping

BASE = Path("data/coldwaves")
DEM = BASE / "elevation/DEM_TERRALERT_32630.tif"
POLYGONS = Path.home() / "Downloads/communes_11_fixed.gpkg"
SUMMARY = BASE / "processed/coldwave_commune_summary.csv"
OUT = BASE / "processed"
GPKG = OUT / "coldwave_elevation_communes.gpkg"
CSV = OUT / "coldwave_elevation_summary.csv"
TABLE = "communes_11_fixed"

for path in [DEM, POLYGONS, SUMMARY]:
    if not path.exists():
        raise SystemExit(f"Missing input: {path}")

if GPKG.exists():
    raise SystemExit(f"Output already exists: {GPKG}")

def unpack_gpkg(blob):
    if blob is None or blob[:2] != b"GP":
        raise ValueError("Invalid GeoPackage geometry")

    envelope = (blob[3] >> 1) & 7
    sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}

    if envelope not in sizes:
        raise ValueError("Unknown GeoPackage envelope")

    return wkb.loads(blob[8 + sizes[envelope]:])

with open(SUMMARY, newline="", encoding="utf-8") as f:
    summary_rows = list(csv.DictReader(f))

summary = {row["commune"]: row for row in summary_rows}

if len(summary) != 11 or len(summary_rows) != 11:
    raise ValueError("Expected 11 unique cold-wave summaries")

with sqlite3.connect(POLYGONS) as conn:
    crs = conn.execute(
        "SELECT srs_id FROM gpkg_contents WHERE table_name = ?",
        (TABLE,)
    ).fetchone()

    if crs is None or crs[0] != 32630:
        raise ValueError("Commune polygons must use EPSG:32630")

    features = conn.execute(
        f'SELECT nom_fr, geom FROM "{TABLE}"'
    ).fetchall()

if len(features) != 11:
    raise ValueError("Expected 11 polygons")

results = []

with rasterio.open(DEM) as src:
    if src.crs.to_epsg() != 32630:
        raise ValueError("DEM must use EPSG:32630")

    if src.res[0] <= 0 or src.res[1] <= 0:
        raise ValueError("Invalid DEM resolution")

    for commune, blob in features:
        if commune not in summary:
            raise ValueError(f"No cold-wave data: {commune}")

        geom = unpack_gpkg(blob)

        if geom.is_empty or not geom.is_valid:
            raise ValueError(f"Invalid geometry: {commune}")

        try:
            clipped, transform = mask(
                src,
                [mapping(geom)],
                crop=True,
                filled=False,
                all_touched=False
            )
        except ValueError:
            raise ValueError(
                f"Polygon outside DEM: {commune}"
            )

        band = clipped[0]

        inside = geometry_mask(
            [mapping(geom)],
            out_shape=band.shape,
            transform=transform,
            invert=True,
            all_touched=False
        )

        valid = (
            inside
            & ~np.ma.getmaskarray(band)
            & np.isfinite(np.asarray(band))
        )

        total_pixels = int(inside.sum())
        valid_pixels = int(valid.sum())

        if valid_pixels == 0:
            raise ValueError(
                f"No valid elevation pixels: {commune}"
            )

        elevations = np.asarray(band)[valid]

        coverage = (
            100 * valid_pixels / total_pixels
            if total_pixels else 0
        )

        cold = summary[commune]

        results.append({
            "commune": commune,
            "elevation_min_m": round(
                float(elevations.min()), 2
            ),
            "elevation_mean_m": round(
                float(elevations.mean()), 2
            ),
            "elevation_max_m": round(
                float(elevations.max()), 2
            ),
            "dem_coverage_pct": round(coverage, 2),
            "dem_valid_pixels": valid_pixels,
            "coldwave_events": int(
                cold["coldwave_events"]
            ),
            "coldwave_days": int(
                cold["coldwave_days"]
            ),
            "coldwave_pct": float(
                cold["coldwave_pct"]
            ),
        })

if len({r["commune"] for r in results}) != 11:
    raise ValueError("Missing or duplicate communes")

# Save statistics as CSV.
fields = list(results[0])

with open(CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(results)

# Preserve Rayane's source DEM and original polygons.
# Create a new derived GeoPackage instead.
shutil.copy2(POLYGONS, GPKG)

try:
    with sqlite3.connect(GPKG) as conn:
        # Spatial functions required by GeoPackage RTree triggers.
        def gpkg_geometry(blob):
            return unpack_gpkg(blob) if blob is not None else None

        def geom_bound(blob, index):
            geom = gpkg_geometry(blob)
            if geom is None or geom.is_empty:
                return None
            return float(geom.bounds[index])

        conn.create_function(
            "ST_IsEmpty", 1,
            lambda blob: (
                None if blob is None
                else int(gpkg_geometry(blob).is_empty)
            )
        )

        for function_name, index in [
            ("ST_MinX", 0),
            ("ST_MinY", 1),
            ("ST_MaxX", 2),
            ("ST_MaxY", 3),
        ]:
            conn.create_function(
                function_name, 1,
                lambda blob, i=index: geom_bound(blob, i)
            )

        for field, sql_type in [
            ("elevation_min_m", "REAL"),
            ("elevation_mean_m", "REAL"),
            ("elevation_max_m", "REAL"),
            ("dem_coverage_pct", "REAL"),
            ("dem_valid_pixels", "INTEGER"),
            ("coldwave_events", "INTEGER"),
            ("coldwave_days", "INTEGER"),
            ("coldwave_pct", "REAL"),
        ]:
            conn.execute(
                f'ALTER TABLE "{TABLE}" '
                f'ADD COLUMN "{field}" {sql_type}'
            )

        for r in results:
            conn.execute(
                f'''
                UPDATE "{TABLE}"
                SET elevation_min_m = ?,
                    elevation_mean_m = ?,
                    elevation_max_m = ?,
                    dem_coverage_pct = ?,
                    dem_valid_pixels = ?,
                    coldwave_events = ?,
                    coldwave_days = ?,
                    coldwave_pct = ?
                WHERE nom_fr = ?
                ''',
                (
                    r["elevation_min_m"],
                    r["elevation_mean_m"],
                    r["elevation_max_m"],
                    r["dem_coverage_pct"],
                    r["dem_valid_pixels"],
                    r["coldwave_events"],
                    r["coldwave_days"],
                    r["coldwave_pct"],
                    r["commune"],
                )
            )

        count, missing = conn.execute(
            f'''SELECT COUNT(*),
                       SUM(elevation_mean_m IS NULL)
                FROM "{TABLE}"'''
        ).fetchone()

        integrity = conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if count != 11 or missing != 0 or integrity != "ok":
            raise ValueError("GeoPackage validation failed")

except Exception:
    GPKG.unlink(missing_ok=True)
    raise

print("=== TERRALERT COLD-WAVE ELEVATION ANALYSIS ===")
print("Communes:", len(results))
print("DEM resolution: 30 m")
print("CRS: EPSG:32630")

print("\n=== ELEVATION SUMMARY ===")
for r in sorted(results, key=lambda x: x["elevation_mean_m"],
                reverse=True):
    print(
        f'{r["commune"]:20} '
        f'Min: {r["elevation_min_m"]:7.1f} m | '
        f'Mean: {r["elevation_mean_m"]:7.1f} m | '
        f'Max: {r["elevation_max_m"]:7.1f} m | '
        f'Coverage: {r["dem_coverage_pct"]:5.1f}% | '
        f'Cold days: {r["coldwave_days"]}'
    )

print("\nDatabase integrity:", integrity)
print("CSV:", CSV)
print("GeoPackage:", GPKG)

low_coverage = [
    r["commune"] for r in results
    if r["dem_coverage_pct"] < 95
]

if low_coverage:
    print("\nWARNING: DEM coverage below 95%:")
    for name in low_coverage:
        print("-", name)

print("\nSUCCESS: Cold-wave elevation GIS generated!")
