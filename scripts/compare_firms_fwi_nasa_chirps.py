#!/usr/bin/env python3
"""Compare historical FIRMS vegetation-fire detections with daily FWI."""

import csv
import sqlite3
from collections import Counter
from datetime import date
from pathlib import Path

FIRMS = Path.home() / "Downloads/historical_fires.gpkg"
FWI = Path("data/wildfires/processed/wildfire_fwi_nasa_chirps_2001_2025.csv")
OUTPUT = Path("data/wildfires/processed/firms_fwi_comparison_nasa_chirps.csv")

with FWI.open(newline="", encoding="utf-8") as f:
    fwi_rows = list(csv.DictReader(f))

fwi_lookup = {
    (r["commune"].strip(), r["date"]): r
    for r in fwi_rows
}

if len(fwi_lookup) != len(fwi_rows):
    raise ValueError("Duplicate FWI commune-date records")

with sqlite3.connect(FIRMS) as conn:
    fires = conn.execute("""
        SELECT fid, ACQ_DATE, ACQ_TIME, TYPE,
               nom_fr, LATITUDE, LONGITUDE, FRP
        FROM historical_fires
    """).fetchall()

results = []
excluded = Counter()

for fid, acq_date, acq_time, fire_type, commune, lat, lon, frp in fires:

    # MODIS TYPE=0: presumed vegetation fire
    if str(fire_type).strip() != "0":
        excluded["non_vegetation_type"] += 1
        continue

    if not commune or not acq_date:
        excluded["missing_commune_or_date"] += 1
        continue

    fire_date = date.fromisoformat(str(acq_date)[:10]).isoformat()
    commune = commune.strip()

    match = fwi_lookup.get((commune, fire_date))

    if match is None:
        status = "no_weather_overlap"
        fwi_value = ""
        danger = ""
    elif match["quality"] != "provisional":
        status = "warmup_excluded"
        fwi_value = match["fwi"]
        danger = match["danger_level"]
    else:
        status = "matched"
        fwi_value = match["fwi"]
        danger = match["danger_level"]

    results.append({
        "fire_id": fid,
        "commune": commune,
        "fire_date": fire_date,
        "acquisition_time": acq_time,
        "latitude": lat,
        "longitude": lon,
        "frp": frp,
        "fwi": fwi_value,
        "danger_level": danger,
        "comparison_status": status,
    })

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

fields = [
    "fire_id", "commune", "fire_date", "acquisition_time",
    "latitude", "longitude", "frp", "fwi",
    "danger_level", "comparison_status",
]

with OUTPUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(results)

statuses = Counter(r["comparison_status"] for r in results)
matched = [r for r in results if r["comparison_status"] == "matched"]

print("=== FIRMS VS FWI HISTORICAL COMPARISON ===")
print("Total FIRMS detections:", len(fires))
print("Excluded non-vegetation detections:",
      excluded["non_vegetation_type"])
print("Other exclusions:",
      excluded["missing_commune_or_date"])
print("Vegetation-fire detections prepared:", len(results))
print("Matched with valid post-warm-up FWI:", statuses["matched"])
print("Excluded during FWI warm-up:", statuses["warmup_excluded"])
print("Outside available weather dates:", statuses["no_weather_overlap"])

print("\n=== DANGER LEVELS AT MATCHED FIRE DETECTIONS ===")
counts = Counter(r["danger_level"] for r in matched)

for level in [
    "Very Low", "Low", "Moderate",
    "High", "Very High", "Extreme"
]:
    print(f"{level:12}: {counts[level]}")

print("\n=== MATCHES BY COMMUNE ===")
for commune, count in Counter(
    r["commune"] for r in matched
).most_common():
    print(f"{commune:20}: {count}")

print("\nSaved:", OUTPUT)
