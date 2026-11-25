#!/usr/bin/env python3
"""Convert TERRALERT historical hourly weather to daily records."""

import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

SOURCE = Path("data/weather/historical/era5_seamless")
OUTPUT = Path("data/weather/processed/daily_weather.csv")

FIELDS = [
    "commune", "date", "source_model", "hours",
    "temperature_mean_c", "temperature_max_c",
    "humidity_mean_pct", "humidity_min_pct",
    "wind_speed_mean_kmh", "wind_speed_max_kmh",
    "precipitation_total_mm",
]

def mean(values):
    return sum(values) / len(values)

def fmt(value):
    return round(value, 3)

records = {}
files = sorted(SOURCE.glob("era5_seamless_????_??.json"))

if not files:
    raise SystemExit("No historical weather files found.")

for path in files:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if payload.get("model") != "era5_seamless":
        raise ValueError(f"Unexpected model in {path}")

    names = payload["communes"]
    results = payload["data"]

    if len(names) != 11 or len(results) != 11:
        raise ValueError(f"Invalid commune count in {path}")

    for commune, result in zip(names, results):
        hourly = result["hourly"]
        times = hourly["time"]

        variables = [
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "precipitation",
        ]

        for variable in variables:
            values = hourly[variable]
            if len(values) != len(times):
                raise ValueError(f"Length mismatch: {path}, {variable}")
            if any(v is None for v in values):
                raise ValueError(f"Missing values: {path}, {variable}")

        days = defaultdict(list)

        for i, timestamp in enumerate(times):
            dt = datetime.fromisoformat(timestamp)
            if dt.minute != 0:
                raise ValueError(f"Unexpected timestamp: {timestamp}")

            day = dt.date().isoformat()
            days[day].append(i)

        for day, indices in days.items():
            if len(indices) != 24:
                raise ValueError(
                    f"Incomplete day: {commune}, {day}, {len(indices)} hours"
                )

            key = (commune, day)
            if key in records:
                raise ValueError(f"Duplicate day: {key}")

            def values(variable):
                return [hourly[variable][i] for i in indices]

            temp = values("temperature_2m")
            rh = values("relative_humidity_2m")
            wind = values("wind_speed_10m")
            rain = values("precipitation")

            records[key] = {
                "commune": commune,
                "date": day,
                "source_model": "era5_seamless",
                "hours": 24,
                "temperature_mean_c": fmt(mean(temp)),
                "temperature_max_c": fmt(max(temp)),
                "humidity_mean_pct": fmt(mean(rh)),
                "humidity_min_pct": fmt(min(rh)),
                "wind_speed_mean_kmh": fmt(mean(wind)),
                "wind_speed_max_kmh": fmt(max(wind)),
                "precipitation_total_mm": fmt(sum(rain)),
            }

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=FIELDS)
    writer.writeheader()

    for key in sorted(records):
        writer.writerow(records[key])

print("=== HISTORICAL WEATHER STANDARDIZATION ===")
print("Monthly files processed:", len(files))
print("Daily records created:", len(records))
print("Communes:", len({key[0] for key in records}))
print("First date:", min(key[1] for key in records))
print("Last date:", max(key[1] for key in records))
print("Output:", OUTPUT)
