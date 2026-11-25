#!/usr/bin/env python3
"""Create a 33-feature provisional wildfire forecast GeoPackage."""

import csv
import os
import shutil
import sqlite3
from collections import Counter
from pathlib import Path

from shapely import wkb

SOURCE = Path.home() / "Downloads/communes_11_fixed.gpkg"
FORECAST_DIR = Path("data/wildfires/forecasts")
OUTPUT_DIR = Path("data/wildfires/gis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

files = sorted(FORECAST_DIR.glob("fwi_forecast_*.csv"))
if not files:
    raise SystemExit("No FWI forecast CSV found.")

forecast_file = files[-1]
run_id = forecast_file.stem.replace("fwi_forecast_", "")
output = OUTPUT_DIR / f"wildfire_forecast_{run_id}.gpkg"
temporary = OUTPUT_DIR / f".wildfire_forecast_{run_id}.tmp.gpkg"

if output.exists():
    raise SystemExit(f"Output already exists: {output}")

with forecast_file.open(encoding="utf-8", newline="") as f:
    forecasts = list(csv.DictReader(f))

dates = sorted({r["date"] for r in forecasts})
names = {r["commune"] for r in forecasts}
keys = [(r["commune"], r["date"]) for r in forecasts]

if len(forecasts) != 33 or len(dates) != 3:
    raise ValueError("Expected 33 records across 3 dates")

if len(names) != 11 or len(set(keys)) != 33:
    raise ValueError("Incomplete or duplicate commune-date records")

if any(Counter(r["date"] for r in forecasts)[d] != 11 for d in dates):
    raise ValueError("Incomplete date coverage")

if any(r["model_status"] != "PROVISIONAL_RESEARCH"
       for r in forecasts):
    raise ValueError("Unexpected model status")

lookup = {(r["commune"], r["date"]): r for r in forecasts}

if temporary.exists():
    temporary.unlink()

shutil.copy2(SOURCE, temporary)

def geometry(blob):
    if blob is None:
        return None
    if blob[:2] != b"GP":
        raise ValueError("Invalid GeoPackage geometry")

    sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    envelope = (blob[3] >> 1) & 7
    offset = 8 + sizes[envelope]
    return wkb.loads(blob[offset:])

def bound(blob, index):
    geom = geometry(blob)
    if geom is None or geom.is_empty:
        return None
    return float(geom.bounds[index])

try:
    with sqlite3.connect(temporary) as conn:
        conn.row_factory = sqlite3.Row

        # Required by GeoPackage spatial-index triggers.
        conn.create_function(
            "ST_IsEmpty", 1,
            lambda b: int(geometry(b).is_empty) if b else None
        )
        for function, index in [
            ("ST_MinX", 0), ("ST_MinY", 1),
            ("ST_MaxX", 2), ("ST_MaxY", 3)
        ]:
            conn.create_function(
                function, 1,
                lambda b, i=index: bound(b, i)
            )

        table = "communes_11_fixed"

        original = conn.execute(
            f'SELECT * FROM "{table}"'
        ).fetchall()

        if len(original) != 11:
            raise ValueError("Expected 11 original polygons")

        original_names = {r["nom_fr"] for r in original}
        if original_names != names:
            raise ValueError(
                f"Commune mismatch: {original_names ^ names}"
            )

        extra_columns = [
            ("forecast_date", "TEXT"),
            ("fwi", "REAL"),
            ("danger_level", "TEXT"),
            ("temperature_c", "REAL"),
            ("humidity_pct", "REAL"),
            ("wind_kmh", "REAL"),
            ("rainfall_mm", "REAL"),
            ("ffmc", "REAL"),
            ("dmc", "REAL"),
            ("dc", "REAL"),
            ("forecast_run", "TEXT"),
            ("model_status", "TEXT"),
            ("weather_source", "TEXT"),
        ]

        for name, dtype in extra_columns:
            conn.execute(
                f'ALTER TABLE "{table}" ADD COLUMN "{name}" {dtype}'
            )

        # Retain the first date's 11 polygons, then clone
        # their geometries and source attributes for dates 2 and 3.
        original_columns = [
            col for col in original[0].keys() if col != "fid"
        ]

        column_sql = ", ".join(
            f'"{name}"' for name in original_columns
        )
        placeholders = ", ".join("?" for _ in original_columns)

        feature_ids = {}

        for row in original:
            feature_ids[(row["nom_fr"], dates[0])] = row["fid"]

        for day in dates[1:]:
            for row in original:
                values = [row[col] for col in original_columns]

                cursor = conn.execute(
                    f'INSERT INTO "{table}" ({column_sql}) '
                    f'VALUES ({placeholders})',
                    values
                )

                feature_ids[(row["nom_fr"], day)] = cursor.lastrowid

        for key, record in lookup.items():
            fid = feature_ids[key]

            conn.execute(f"""
                UPDATE "{table}"
                SET forecast_date = ?,
                    fwi = ?,
                    danger_level = ?,
                    temperature_c = ?,
                    humidity_pct = ?,
                    wind_kmh = ?,
                    rainfall_mm = ?,
                    ffmc = ?,
                    dmc = ?,
                    dc = ?,
                    forecast_run = ?,
                    model_status = ?,
                    weather_source = ?
                WHERE fid = ?
            """, (
                record["date"],
                float(record["fwi"]),
                record["danger_level"],
                float(record["temperature_c"]),
                float(record["relative_humidity_pct"]),
                float(record["wind_speed_kmh"]),
                float(record["rainfall_24h_mm"]),
                float(record["ffmc"]),
                float(record["dmc"]),
                float(record["dc"]),
                record["forecast_run"],
                record["model_status"],
                record["weather_source"],
                fid,
            ))

        total = conn.execute(
            f'SELECT COUNT(*) FROM "{table}"'
        ).fetchone()[0]

        populated = conn.execute(
            f'SELECT COUNT(*) FROM "{table}" '
            'WHERE fwi IS NOT NULL'
        ).fetchone()[0]

        if total != 33 or populated != 33:
            raise ValueError("GIS feature count incorrect")

        conn.commit()

        integrity = conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity != "ok":
            raise ValueError(f"GeoPackage integrity: {integrity}")

    os.replace(temporary, output)

except Exception:
    if temporary.exists():
        temporary.unlink()
    raise

print("=== TERRALERT FORECAST GIS ===")
print("Communes:", len(names))
print("Forecast dates:", dates)
print("Polygon features:", total)
print("FWI attributes populated:", populated)
print("CRS: EPSG:32630 (preserved)")
print("Database integrity:", integrity)
print("Output:", output)
print("Status: PROVISIONAL_RESEARCH")
print("\nSUCCESS: Forecast GeoPackage created!")
