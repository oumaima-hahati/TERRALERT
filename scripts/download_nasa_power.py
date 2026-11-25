#!/usr/bin/env python3
"""Download validated NASA POWER hourly data by commune and year."""

import argparse
import calendar
import csv
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

LOCATIONS = Path("data/weather/locations/commune_coordinates.csv")
OUTPUT = Path("data/weather/nasa_power/hourly")
PARAMETERS = ("T2M", "RH2M", "WS10M", "PRECTOTCORR")
EXPECTED_UNITS = {
    "T2M": "C",
    "RH2M": "%",
    "WS10M": "m/s",
    "PRECTOTCORR": "mm/hour",
}

def validate(data, year):
    variables = data["properties"]["parameter"]
    units = data["parameters"]
    expected_hours = (366 if calendar.isleap(year) else 365) * 24

    for variable in PARAMETERS:
        if units[variable]["units"] != EXPECTED_UNITS[variable]:
            raise ValueError(f"Unexpected units for {variable}")

        values = variables[variable]

        if len(values) != expected_hours:
            raise ValueError(f"Incomplete year: {variable}")

        first = datetime(year, 1, 1)
        for i in range(expected_hours):
            timestamp = (first + timedelta(hours=i)).strftime("%Y%m%d%H")
            value = values.get(timestamp)

            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"Missing or invalid {variable}: {timestamp}")
            if value <= -900:
                raise ValueError(f"Missing-value sentinel: {variable}, {timestamp}")
            if variable == "RH2M" and not 0 <= value <= 100:
                raise ValueError(f"Invalid humidity: {timestamp}")
            if variable in ("WS10M", "PRECTOTCORR") and value < 0:
                raise ValueError(f"Invalid {variable}: {timestamp}")

    return expected_hours

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--limit", type=int, default=2)
    args = parser.parse_args()

    if not 2001 <= args.year <= 2025:
        parser.error("Choose a year from 2001 to 2025")
    if args.limit < 1:
        parser.error("--limit must be positive")

    with LOCATIONS.open(newline="", encoding="utf-8") as f:
        locations = list(csv.DictReader(f))

    if len(locations) != 11:
        raise ValueError("Expected 11 commune locations")

    OUTPUT.mkdir(parents=True, exist_ok=True)

    for location in locations[:args.limit]:
        commune = location["commune"]
        slug = commune.lower().replace(" ", "_").replace("é", "e")
        path = OUTPUT / f"nasa_power_{slug}_{args.year}.json"

        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
                validate(existing["data"], args.year)
                print("Already valid, skipping:", commune, flush=True)
                continue
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                raise SystemExit(
                    f"Existing file needs review: {path}: {exc}"
                )

        params = {
            "parameters": ",".join(PARAMETERS),
            "community": "AG",
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "start": f"{args.year}0101",
            "end": f"{args.year}1231",
            "format": "JSON",
            "time-standard": "UTC",
        }

        url = (
            "https://power.larc.nasa.gov/api/temporal/hourly/point?"
            + urllib.parse.urlencode(params)
        )

        print("Downloading:", commune, args.year, flush=True)

        try:
            with urllib.request.urlopen(url, timeout=240) as response:
                data = json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                print("NASA POWER rate limit reached. Stopping.")
                print("Retry-After:", exc.headers.get("Retry-After", "unspecified"))
                raise SystemExit(2)
            raise

        hours = validate(data, args.year)

        payload = {
            "source": "NASA POWER hourly API",
            "time_standard": "UTC",
            "commune": commune,
            "year": args.year,
            "requested_latitude": float(location["latitude"]),
            "requested_longitude": float(location["longitude"]),
            "data": data,
        }

        temp = path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(payload), encoding="utf-8")
        temp.replace(path)

        print(f"Saved: {path} | Hours: {hours}", flush=True)
        time.sleep(3)

    print("\nSUCCESS: Selected communes processed")

if __name__ == "__main__":
    main()
