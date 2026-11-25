#!/usr/bin/env python3
"""Build TERRALERT heatwave population-exposure GIS layer."""

import csv
import os
import shutil
import sqlite3
from pathlib import Path
from shapely import wkb

SOURCE = Path.home() / "Downloads/communes_11_fixed.gpkg"
SUMMARY = Path(
    "data/heatwaves/processed/"
    "heatwave_population_exposure_summary.csv"
)
OUTPUT = Path(
    "data/heatwaves/processed/"
    "heatwave_exposure_communes.gpkg"
)

if not SOURCE.exists() or not SUMMARY.exists():
    raise SystemExit("Missing commune boundaries or exposure summary")

with SUMMARY.open(encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

summary = {r["commune"].strip(): r for r in rows}

if len(summary) != 11 or len(rows) != 11:
    raise ValueError("Expected 11 unique study areas")

if OUTPUT.exists():
    raise SystemExit(
        f"Output already exists: {OUTPUT}. "
        "Existing GIS data will not be overwritten."
    )

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
temporary = OUTPUT.with_name(
    "heatwave_exposure_communes.tmp.gpkg"
)

if temporary.exists():
    raise SystemExit(f"Temporary file already exists: {temporary}")

shutil.copy2(SOURCE, temporary)

def geometry(blob):
    if blob is None:
        return None
    if blob[:2] != b"GP":
        raise ValueError("Invalid GeoPackage geometry")

    sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    envelope = (blob[3] >> 1) & 7
    if envelope not in sizes:
        raise ValueError("Unsupported GeoPackage envelope")

    return wkb.loads(blob[8 + sizes[envelope]:])

def bound(blob, index):
    geom = geometry(blob)
    if geom is None or geom.is_empty:
        return None
    return float(geom.bounds[index])

try:
    with sqlite3.connect(temporary) as conn:
        conn.create_function(
            "ST_IsEmpty", 1,
            lambda b: int(geometry(b).is_empty)
            if b is not None else None
        )

        for name, index in [
            ("ST_MinX", 0),
            ("ST_MinY", 1),
            ("ST_MaxX", 2),
            ("ST_MaxY", 3),
        ]:
            conn.create_function(
                name, 1, lambda b, i=index: bound(b, i)
            )

        table = "communes_11_fixed"

        names = {
            row[0] for row in conn.execute(
                f'SELECT nom_fr FROM "{table}"'
            )
        }

        if names != set(summary):
            raise ValueError(
                f"GIS name mismatch: {names ^ set(summary)}"
            )

        columns = [
            ("hcp_geo_code", "TEXT"),
            ("population_2024", "INTEGER"),
            ("heatwave_events", "INTEGER"),
            ("heatwave_days", "INTEGER"),
            ("potential_person_days_2024", "INTEGER"),
            ("reference_year", "INTEGER"),
            ("exposure_note", "TEXT"),
        ]

        for name, dtype in columns:
            conn.execute(
                f'ALTER TABLE "{table}" '
                f'ADD COLUMN "{name}" {dtype}'
            )

        for commune, row in summary.items():
            population = int(row["population_2024"])
            events = int(row["heatwave_events"])
            days = int(row["heatwave_days"])
            person_days = int(
                row["potential_person_days_2024"]
            )

            if (
                population <= 0
                or events < 0
                or days < 0
                or person_days != population * days
            ):
                raise ValueError(
                    f"Invalid exposure values: {commune}"
                )

            conn.execute(f"""
                UPDATE "{table}"
                SET hcp_geo_code = ?,
                    population_2024 = ?,
                    heatwave_events = ?,
                    heatwave_days = ?,
                    potential_person_days_2024 = ?,
                    reference_year = 2024,
                    exposure_note = ?
                WHERE nom_fr = ?
            """, (
                row["hcp_geo_code"],
                population,
                events,
                days,
                person_days,
                "Potential area-wide exposure; "
                "RGPH 2024 population reference; "
                "not observed health impact",
                commune,
            ))

        count, total_population = conn.execute(f"""
            SELECT COUNT(*), SUM(population_2024)
            FROM "{table}"
        """).fetchone()

        if count != 11 or total_population != 1429892:
            raise ValueError(
                "GIS population/count validation failed"
            )

        conn.commit()

        integrity = conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity != "ok":
            raise ValueError(
                f"GeoPackage integrity check failed: {integrity}"
            )

    os.replace(temporary, OUTPUT)

except Exception:
    if temporary.exists():
        temporary.unlink()
    raise

print("=== TERRALERT HEATWAVE EXPOSURE GIS ===")
print("Study areas:", count)
print("Reference population:", total_population)
print("Reference year: 2024")
print("CRS: EPSG:32630 (preserved)")
print("Database integrity:", integrity)
print("Output:", OUTPUT)
print("\nSUCCESS: Heatwave exposure GIS layer created!")
