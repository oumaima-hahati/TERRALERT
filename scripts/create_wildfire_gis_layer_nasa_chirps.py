#!/usr/bin/env python3
"""Attach historical FWI statistics to TERRALERT commune polygons."""

import csv
import os
import shutil
import sqlite3
from pathlib import Path

SOURCE = Path.home() / "Downloads/communes_11_fixed.gpkg"
SUMMARY = Path("data/wildfires/processed/wildfire_fwi_commune_summary_nasa_chirps.csv")
OUTPUT = Path("data/wildfires/processed/wildfire_fwi_communes_nasa_chirps.gpkg")

if not SOURCE.exists() or not SUMMARY.exists():
    raise SystemExit("Missing commune boundaries or FWI summary")

with SUMMARY.open(encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))

summary = {}
for row in rows:
    name = row["commune"].strip()
    if name in summary:
        raise ValueError(f"Duplicate commune: {name}")
    summary[name] = row

if len(summary) != 11:
    raise ValueError(f"Expected 11 communes, found {len(summary)}")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
temporary = OUTPUT.with_name(OUTPUT.stem + ".tmp.gpkg")

if temporary.exists():
    temporary.unlink()

shutil.copy2(SOURCE, temporary)

try:
    with sqlite3.connect(temporary) as conn:
        from shapely import wkb

        def geometry(blob):
            if blob is None:
                return None

            if blob[:2] != b"GP":
                raise ValueError("Invalid GeoPackage geometry")

            envelope_sizes = {
                0: 0, 1: 32, 2: 48, 3: 48, 4: 64
            }

            envelope_type = (blob[3] >> 1) & 7
            if envelope_type not in envelope_sizes:
                raise ValueError("Invalid GeoPackage envelope")

            offset = 8 + envelope_sizes[envelope_type]
            return wkb.loads(blob[offset:])

        def spatial_bound(blob, index):
            geom = geometry(blob)
            if geom is None or geom.is_empty:
                return None
            return float(geom.bounds[index])

        conn.create_function(
            "ST_IsEmpty", 1,
            lambda blob: int(geometry(blob).is_empty)
            if blob is not None else None
        )
        conn.create_function(
            "ST_MinX", 1, lambda blob: spatial_bound(blob, 0)
        )
        conn.create_function(
            "ST_MinY", 1, lambda blob: spatial_bound(blob, 1)
        )
        conn.create_function(
            "ST_MaxX", 1, lambda blob: spatial_bound(blob, 2)
        )
        conn.create_function(
            "ST_MaxY", 1, lambda blob: spatial_bound(blob, 3)
        )
        layers = conn.execute("""
            SELECT table_name
            FROM gpkg_contents
            WHERE data_type = 'features'
        """).fetchall()

        if len(layers) != 1 or layers[0][0] != "communes_11_fixed":
            raise ValueError("Unexpected GeoPackage layer")

        table = "communes_11_fixed"

        names = {
            r[0] for r in conn.execute(
                'SELECT nom_fr FROM "communes_11_fixed"'
            )
        }

        if names != set(summary):
            raise ValueError(
                f"Commune mismatch. Missing: {names - set(summary)}; "
                f"Extra: {set(summary) - names}"
            )

        columns = [
            ("fwi_mean", "REAL"),
            ("fwi_max", "REAL"),
            ("fwi_days", "INTEGER"),
            ("high_days", "INTEGER"),
            ("extreme_days", "INTEGER"),
            ("high_pct", "REAL"),
            ("data_note", "TEXT"),
        ]

        for column, dtype in columns:
            conn.execute(
                f'ALTER TABLE "{table}" ADD COLUMN "{column}" {dtype}'
            )

        for name, row in summary.items():
            days = int(row["records"])
            high = int(row["high_days"])

            if days <= 0 or not 0 <= high <= days:
                raise ValueError(f"Invalid statistics for {name}")

            conn.execute("""
                UPDATE communes_11_fixed
                SET fwi_mean = ?,
                    fwi_max = ?,
                    fwi_days = ?,
                    high_days = ?,
                    extreme_days = ?,
                    high_pct = ?,
                    data_note = ?
                WHERE nom_fr = ?
            """, (
                float(row["mean_fwi"]),
                float(row["maximum_fwi"]),
                days,
                high,
                int(row["extreme_days"]),
                round(high / days * 100, 2),
                "Provisional NASA POWER + CHIRPS v3 FWI; 2001-2025; previous-day rainfall approximation",
                name,
            ))

        total, populated = conn.execute("""
            SELECT COUNT(*), COUNT(fwi_mean)
            FROM communes_11_fixed
        """).fetchone()

        if total != 11 or populated != 11:
            raise ValueError("GIS layer validation failed")

        conn.commit()

    os.replace(temporary, OUTPUT)

except Exception:
    if temporary.exists():
        temporary.unlink()
    raise

print("=== TERRALERT WILDFIRE GIS LAYER ===")
print("Communes:", total)
print("FWI values populated:", populated)
print("CRS: EPSG:32630 (preserved)")
print("Output:", OUTPUT)
print("\nSUCCESS: Historical wildfire GIS layer created")
