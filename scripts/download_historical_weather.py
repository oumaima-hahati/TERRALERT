#!/usr/bin/env python3
"""Download and validate monthly ERA5-Land weather for 11 TERRALERT communes."""

import argparse
import calendar
import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

LOCATIONS = Path("data/weather/locations/commune_coordinates.csv")
OUTPUT = Path("data/weather/historical/era5_seamless")
VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "precipitation",
]

def download_month(year, month, locations):
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    expected_times = [
        (first + timedelta(days=day)).isoformat() + f"T{hour:02d}:00"
        for day in range((last - first).days + 1)
        for hour in range(24)
    ]

    output = OUTPUT / f"era5_seamless_{year}_{month:02d}.json"
    if output.exists():
        print(f"Already exists, skipping: {output}", flush=True)
        return

    params = {
        "latitude": ",".join(r["latitude"] for r in locations),
        "longitude": ",".join(r["longitude"] for r in locations),
        "start_date": first.isoformat(),
        "end_date": last.isoformat(),
        "hourly": ",".join(VARIABLES),
        "models": "era5_seamless",
        "timezone": "UTC",
    }

    url = (
        "https://archive-api.open-meteo.com/v1/archive?"
        + urllib.parse.urlencode(params)
    )

    print(f"Downloading {year}-{month:02d}...", flush=True)

    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=180) as response:
                data = json.load(response)
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                retry_after = exc.headers.get("Retry-After", "not provided")
                reason = exc.read().decode("utf-8", errors="replace")
                print("\nOPEN-METEO RATE LIMIT REACHED", flush=True)
                print("Retry-After:", retry_after, flush=True)
                print("Server response:", reason[:500], flush=True)
                print("Stopping without deleting saved months.", flush=True)
                raise SystemExit(2)

            if exc.code in (500, 502, 503, 504) and attempt < 2:
                print(f"Server error {exc.code}. Retrying...", flush=True)
                time.sleep(10 * (attempt + 1))
                continue

            raise

        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == 2:
                raise
            print(f"Request failed: {exc}. Retrying...", flush=True)
            time.sleep(10 * (attempt + 1))

    if not isinstance(data, list) or len(data) != len(locations):
        raise ValueError("Incorrect number of commune responses")

    missing_count = 0

    for location, result in zip(locations, data):
        hourly = result.get("hourly", {})

        if hourly.get("time") != expected_times:
            raise ValueError(
                f"Invalid hourly timestamps: {location['commune']}"
            )

        for variable in VARIABLES:
            values = hourly.get(variable)
            if not isinstance(values, list) or len(values) != len(expected_times):
                raise ValueError(
                    f"Invalid {variable}: {location['commune']}"
                )

            missing_count += sum(value is None for value in values)

            for value in values:
                if value is None:
                    continue
                if not isinstance(value, (int, float)):
                    raise ValueError(f"Non-numeric {variable}")
                if variable == "relative_humidity_2m" and not 0 <= value <= 100:
                    raise ValueError("Invalid relative humidity")
                if variable == "precipitation" and value < 0:
                    raise ValueError("Negative precipitation")
                if variable == "wind_speed_10m" and value < 0:
                    raise ValueError("Negative wind speed")
                if variable == "wind_direction_10m" and not 0 <= value <= 360:
                    raise ValueError("Invalid wind direction")

    if missing_count:
        raise ValueError(
            f"Incomplete weather data: {missing_count} missing values. "
            "File will not be saved."
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps({
        "source": "Open-Meteo Historical API",
        "model": "era5_seamless",
        "timezone": "UTC",
        "communes": [r["commune"] for r in locations],
        "data": data,
    }), encoding="utf-8")
    temporary.replace(output)

    print(f"Saved: {output}")
    print(f"Communes: {len(data)}")
    print(f"Hours per commune: {len(expected_times)}")
    print(f"Missing variable values: {missing_count}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, default=2024)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--start-month", type=int, default=1)
    parser.add_argument("--end-month", type=int, default=1)
    args = parser.parse_args()

    if args.start_year > args.end_year:
        parser.error("start-year must be <= end-year")
    if not 1 <= args.start_month <= 12 or not 1 <= args.end_month <= 12:
        parser.error("Months must be between 1 and 12")
    if (args.start_year, args.start_month) > (args.end_year, args.end_month):
        parser.error("Start date must precede end date")

    with LOCATIONS.open(encoding="utf-8", newline="") as handle:
        locations = list(csv.DictReader(handle))

    if len(locations) != 11:
        raise ValueError("Expected exactly 11 communes")

    for year in range(args.start_year, args.end_year + 1):
        for month in range(1, 13):
            if (year, month) < (args.start_year, args.start_month):
                continue
            if (year, month) > (args.end_year, args.end_month):
                continue
            download_month(year, month, locations)


if __name__ == "__main__":
    main()
