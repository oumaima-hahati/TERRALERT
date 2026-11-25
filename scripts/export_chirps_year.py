#!/usr/bin/env python3
"""Export one year of CHIRPS v3 SAT rainfall for 11 communes."""

import argparse
import csv
import ee
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--year", type=int, default=2024)
args = parser.parse_args()

year = args.year

if not 2000 <= year <= 2025:
    parser.error("Year must be between 2000 and 2025")

ee.Initialize(project="terralert-research")

print("Earth Engine connected successfully!", flush=True)

path = Path("data/weather/locations/commune_coordinates.csv")

with path.open(encoding="utf-8", newline="") as f:
    locations = list(csv.DictReader(f))

if len(locations) != 11:
    raise ValueError("Expected exactly 11 communes")

points = ee.FeatureCollection([
    ee.Feature(
        ee.Geometry.Point([
            float(r["longitude"]),
            float(r["latitude"])
        ]),
        {"commune": r["commune"]}
    )
    for r in locations
])

start = f"{year}-01-01"
end = f"{year + 1}-01-01"

collection = (
    ee.ImageCollection("UCSB-CHC/CHIRPS/V3/DAILY_SAT")
    .filterDate(start, end)
    .select("precipitation")
    .sort("system:time_start")
)

count = collection.size().getInfo()
expected = 366 if year % 4 == 0 and (
    year % 100 != 0 or year % 400 == 0
) else 365

print("Year:", year)
print("CHIRPS images:", count)

if count != expected:
    raise ValueError(
        f"Expected {expected} daily images, found {count}"
    )

images = collection.toList(count)

def extract_image(index):
    image = ee.Image(images.get(index))

    day = ee.Date(
        image.get("system:time_start")
    ).format("YYYY-MM-dd")

    sampled = image.reduceRegions(
        collection=points,
        reducer=ee.Reducer.first(),
        scale=5566
    )

    return sampled.map(
        lambda feature: ee.Feature(None, {
            "commune": feature.get("commune"),
            "date": day,
            "precipitation_mm": feature.get("first"),
            "source": "CHIRPS_v3_DAILY_SAT"
        })
    )

indices = ee.List.sequence(0, count - 1)

table = ee.FeatureCollection(
    indices.map(extract_image)
).flatten()

filename = f"terralert_chirps_v3_sat_{year}"

task = ee.batch.Export.table.toDrive(
    collection=table,
    description=filename,
    folder="TERRALERT_CHIRPS",
    fileNamePrefix=filename,
    fileFormat="CSV",
    selectors=[
        "commune",
        "date",
        "precipitation_mm",
        "source"
    ]
)

task.start()

print("\n=== CHIRPS EXPORT SUBMITTED ===")
print("Year:", year)
print("Expected rows:", expected * 11)
print("Task ID:", task.id)
print("Drive folder: TERRALERT_CHIRPS")
print("Filename:", filename + ".csv")
print("Status:", task.status().get("state"))
