#!/usr/bin/env python3
"""Extract CHIRPS v3 SAT daily rainfall at 11 commune points."""

import argparse
import csv
import math
import tempfile
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import rasterio

LOCATIONS = Path("data/weather/locations/commune_coordinates.csv")
OUTPUT = Path("data/weather/chirps_v3/daily")

BASE_URL = (
    "https://data.chc.ucsb.edu/products/CHIRPS/"
    "v3.0/daily/final/sat"
)


def extract_day(day, locations):
    filename = f"chirps-v3.0.sat.{day:%Y.%m.%d}.tif"
    url = f"{BASE_URL}/{day.year}/{filename}"

    with tempfile.TemporaryDirectory() as temp_dir:
        raster_path = Path(temp_dir) / filename

        request = urllib.request.Request(
            url,
            headers={"User-Agent": "TERRALERT academic research"}
        )

        with urllib.request.urlopen(request, timeout=180) as response:
            with raster_path.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)

        with rasterio.open(raster_path) as raster:
            if raster.crs.to_epsg() != 4326:
                raise ValueError("Unexpected CHIRPS CRS")

            points = [
                (float(r["longitude"]), float(r["latitude"]))
                for r in locations
            ]

            samples = list(raster.sample(points, masked=True))

            results = []

            for location, sample in zip(locations, samples):
                value = sample[0]

                if hasattr(value, "mask") and bool(value.mask):
                    rainfall = None
                else:
                    rainfall = float(value)

                if rainfall is not None:
                    if not math.isfinite(rainfall) or rainfall < 0:
                        rainfall = None

                results.append({
                    "commune": location["commune"],
                    "date": day.isoformat(),
                    "precipitation_mm": (
                        round(rainfall, 4)
                        if rainfall is not None else ""
                    ),
                    "source": "CHIRPS_v3_SAT",
                })

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default="2024-01-07")
    args = parser.parse_args()

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)

    if end < start:
        parser.error("End date precedes start date")

    if (end - start).days > 31:
        parser.error("Use a period of at most 32 days per run")

    with LOCATIONS.open(encoding="utf-8", newline="") as file:
        locations = list(csv.DictReader(file))

    if len(locations) != 11:
        raise ValueError("Expected exactly 11 communes")

    results = []

    day = start

    while day <= end:
        print("Processing:", day, flush=True)
        daily = extract_day(day, locations)
        results.extend(daily)
        day += timedelta(days=1)

    OUTPUT.mkdir(parents=True, exist_ok=True)

    target = OUTPUT / (
        f"chirps_v3_sat_{start:%Y%m%d}_{end:%Y%m%d}.csv"
    )

    temporary = target.with_suffix(".csv.tmp")

    with temporary.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "commune", "date", "precipitation_mm", "source"
            ]
        )
        writer.writeheader()
        writer.writerows(results)

    temporary.replace(target)

    print("\n=== CHIRPS EXTRACTION ===")
    print("Days:", (end - start).days + 1)
    print("Communes:", len(locations))
    print("Records:", len(results))
    print("Missing rainfall values:", sum(
        r["precipitation_mm"] == "" for r in results
    ))
    print("Output:", target)


if __name__ == "__main__":
    main()
