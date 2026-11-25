#!/usr/bin/env python3
"""Prepare local-noon FWI weather for all available historical months."""

import csv
import json
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SOURCE = Path("data/weather/historical/era5_seamless")
OUTPUT = Path("data/weather/processed/fwi_weather_historical.csv")
TZ = ZoneInfo("Africa/Casablanca")

VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "precipitation",
]

FIELDS = [
    "commune",
    "date",
    "observation_utc",
    "temperature_c",
    "relative_humidity_pct",
    "wind_speed_10m_kmh",
    "rainfall_previous_24h_mm",
]

files = sorted(SOURCE.glob("era5_seamless_????_??.json"))

if not files:
    raise SystemExit("No historical weather files found")

windows = {}
last_timestamp = {}
records = []
resets = 0

for path in files:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if payload.get("model") != "era5_seamless":
        raise ValueError(f"Unexpected model: {path}")

    if len(payload["communes"]) != 11 or len(payload["data"]) != 11:
        raise ValueError(f"Incorrect commune count: {path}")

    for commune, result in zip(payload["communes"], payload["data"]):
        hourly = result["hourly"]
        times = hourly["time"]

        for variable in VARIABLES:
            values = hourly[variable]
            if len(values) != len(times):
                raise ValueError(f"Invalid length: {path}, {variable}")
            if any(v is None for v in values):
                raise ValueError(f"Missing values: {path}, {variable}")

        window = windows.setdefault(commune, deque(maxlen=24))

        for i, timestamp in enumerate(times):
            dt = datetime.fromisoformat(timestamp).replace(
                tzinfo=timezone.utc
            )

            previous = last_timestamp.get(commune)

            if previous is not None:
                if dt <= previous:
                    raise ValueError(
                        f"Duplicate or out-of-order timestamp: {commune}, {dt}"
                    )

                if dt - previous != timedelta(hours=1):
                    window.clear()
                    resets += 1

            last_timestamp[commune] = dt

            observation = {
                "temperature": hourly["temperature_2m"][i],
                "humidity": hourly["relative_humidity_2m"][i],
                "wind": hourly["wind_speed_10m"][i],
                "rain": hourly["precipitation"][i],
            }

            window.append(observation)

            local_dt = dt.astimezone(TZ)

            if local_dt.hour != 12 or local_dt.minute != 0:
                continue

            if len(window) != 24:
                continue

            records.append({
                "commune": commune,
                "date": local_dt.date().isoformat(),
                "observation_utc": dt.isoformat(),
                "temperature_c": observation["temperature"],
                "relative_humidity_pct": observation["humidity"],
                "wind_speed_10m_kmh": observation["wind"],
                "rainfall_previous_24h_mm": round(
                    sum(item["rain"] for item in window), 3
                ),
            })

    print("Processed:", path.name, flush=True)

keys = [(r["commune"], r["date"]) for r in records]

if len(keys) != len(set(keys)):
    raise ValueError("Duplicate commune-date records detected")

records.sort(key=lambda r: (r["commune"], r["date"]))

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(records)

print("\n=== HISTORICAL FWI WEATHER PREPARATION ===")
print("Monthly files:", len(files))
print("Communes:", len({r["commune"] for r in records}))
print("FWI weather records:", len(records))
print("Discontinuities detected:", resets)
print("First date:", min(r["date"] for r in records))
print("Last date:", max(r["date"] for r in records))
print("Output:", OUTPUT)
