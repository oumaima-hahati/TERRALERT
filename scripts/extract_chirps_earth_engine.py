#!/usr/bin/env python3
"""Extract CHIRPS v3 SAT daily rainfall for TERRALERT communes."""

import csv
import math
from datetime import date, timedelta
from pathlib import Path

import ee

PROJECT = "terralert-research"
LOCATIONS = Path("data/weather/locations/commune_coordinates.csv")
OUTPUT = Path("data/weather/chirps_v3/earth_engine")

START = "2024-01-01"
END = "2024-01-08"  # Exclusive: January 1–7

ee.Initialize(project=PROJECT)

with LOCATIONS.open(encoding="utf-8", newline="") as f:
    locations = list(csv.DictReader(f))

if len(locations) != 11:
    raise ValueError("Expected 11 communes")

points = ee.FeatureCollection([
    ee.Feature(
        ee.Geometry.Point([
            float(row["longitude"]),
            float(row["latitude"])
        ]),
        {"commune": row["commune"]}
    )
    for row in locations
])

collection = (
    ee.ImageCollection("UCSB-CHC/CHIRPS/V3/DAILY_SAT")
    .filterDate(START, END)
    .select("precipitation")
)

print("Connecting to Earth Engine...", flush=True)

count = collection.size().getInfo()
print("CHIRPS images:", count)

if count != 7:
    raise ValueError(f"Expected 7 daily images, found {count}")

records = []

start = date.fromisoformat(START)

for offset in range(7):
    day = start + timedelta(days=offset)
    next_day = day + timedelta(days=1)

    image = ee.Image(
        collection.filterDate(
            day.isoformat(),
            next_day.isoformat()
        ).first()
    )

    sampled = image.reduceRegions(
        collection=points,
        reducer=ee.Reducer.first(),
        scale=5566
    )

    features = sampled.getInfo()["features"]

    if len(features) != 11:
        raise ValueError(f"Incorrect commune count: {day}")

    daily = {}

    for feature in features:
        props = feature["properties"]
        commune = props["commune"]
        rainfall = props.get("first")

        if (
            rainfall is None
            or not math.isfinite(float(rainfall))
            or float(rainfall) < 0
        ):
            raise ValueError(
                f"Missing or invalid precipitation: {commune}, {day}"
            )

        daily[commune] = round(float(rainfall), 4)

    if len(daily) != 11:
        raise ValueError(f"Duplicate or missing communes: {day}")

    for commune, rainfall in sorted(daily.items()):
        records.append({
            "commune": commune,
            "date": day.isoformat(),
            "precipitation_mm": rainfall,
            "source": "CHIRPS_v3_DAILY_SAT"
        })

    print(f"{day}: 11 communes OK", flush=True)

OUTPUT.mkdir(parents=True, exist_ok=True)

target = OUTPUT / "chirps_v3_test_20240101_07.csv"
temporary = target.with_suffix(".csv.tmp")

with temporary.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "commune",
            "date",
            "precipitation_mm",
            "source"
        ]
    )
    writer.writeheader()
    writer.writerows(records)

temporary.replace(target)

print("\n=== CHIRPS EXTRACTION SUCCESS ===")
print("Days:", 7)
print("Communes:", len(locations))
print("Rainfall records:", len(records))
print("Output:", target)
