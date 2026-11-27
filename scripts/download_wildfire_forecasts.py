#!/usr/bin/env python3
"""Download and validate hourly wildfire weather forecasts."""

import csv
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = Path("data/weather")
LOCATIONS = BASE / "locations/commune_coordinates.csv"
OUTPUT = BASE / "forecasts/open_meteo"
OUTPUT.mkdir(parents=True, exist_ok=True)

URL = "https://api.open-meteo.com/v1/forecast"

FIELDS = [
    "commune",
    "forecast_time_utc",
    "temperature_c",
    "relative_humidity_pct",
    "wind_speed_kmh",
    "precipitation_mm",
    "retrieved_at_utc",
    "source",
]

with LOCATIONS.open(encoding="utf-8-sig", newline="") as f:
    communes = list(csv.DictReader(f))

if len(communes) != 11:
    raise ValueError("Expected exactly 11 communes")

names = [row["commune"] for row in communes]
if len(set(names)) != 11:
    raise ValueError("Duplicate commune names")

run_time = datetime.now(timezone.utc)
run_id = run_time.strftime("%Y%m%dT%H%M%SZ")
retrieved_at = run_time.isoformat()

session = requests.Session()
records = []
daily_records = []
metadata = []

print("=== TERRALERT FORECAST INGESTION ===", flush=True)

for index, location in enumerate(communes, 1):
    name = location["commune"]

    params = {
        "latitude": float(location["latitude"]),
        "longitude": float(location["longitude"]),
        "hourly": (
            "temperature_2m,relative_humidity_2m,"
            "wind_speed_10m,precipitation"
        ),
        "daily": "temperature_2m_max,temperature_2m_min",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "temperature_unit": "celsius",
        "timezone": "UTC",
        "forecast_days": 4,
    }

    response = session.get(URL, params=params, timeout=45)
    response.raise_for_status()
    data = response.json()

    hourly = data["hourly"]
    fields = {
        "temperature_2m": "temperature_c",
        "relative_humidity_2m": "relative_humidity_pct",
        "wind_speed_10m": "wind_speed_kmh",
        "precipitation": "precipitation_mm",
    }

    times = hourly["time"]
    if len(times) != 96:
        raise ValueError(f"{name}: expected 96 hours, got {len(times)}")

    if any(len(hourly[key]) != len(times) for key in fields):
        raise ValueError(f"{name}: inconsistent hourly lengths")

    parsed_times = [
        datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
        for t in times
    ]

    if len(set(parsed_times)) != 96:
        raise ValueError(f"{name}: duplicate forecast timestamps")

    if any(
        (b - a).total_seconds() != 3600
        for a, b in zip(parsed_times, parsed_times[1:])
    ):
        raise ValueError(f"{name}: missing forecast hours")

    for i, timestamp in enumerate(parsed_times):
        record = {
            "commune": name,
            "forecast_time_utc": timestamp.isoformat(),
            "retrieved_at_utc": retrieved_at,
            "source": "Open-Meteo Forecast API",
        }

        for api_field, output_field in fields.items():
            value = hourly[api_field][i]

            if value is None:
                raise ValueError(f"{name}: missing {api_field}")

            value = float(value)

            if not math.isfinite(value):
                raise ValueError(f"{name}: invalid {api_field}")

            record[output_field] = value

        if not 0 <= record["relative_humidity_pct"] <= 100:
            raise ValueError(f"{name}: humidity out of range")

        if record["wind_speed_kmh"] < 0:
            raise ValueError(f"{name}: negative wind")

        if record["precipitation_mm"] < 0:
            raise ValueError(f"{name}: negative rainfall")

        records.append(record)

    # Dedicated UTC daily extrema from the forecast provider; do not alter hourly FWI input.
    daily = data["daily"]
    day_dates = daily["time"]
    if len(day_dates) != 4 or any(len(daily[k]) != 4 for k in ("temperature_2m_max", "temperature_2m_min")):
        raise ValueError(f"{name}: expected four daily forecast records")
    parsed_days = [datetime.strptime(day, "%Y-%m-%d").date() for day in day_dates]
    if len(set(parsed_days)) != 4 or any((b-a).days != 1 for a,b in zip(parsed_days, parsed_days[1:])):
        raise ValueError(f"{name}: invalid daily sequence")
    if parsed_days != sorted({dt.date() for dt in parsed_times}):
        raise ValueError(f"{name}: hourly/daily date mismatch")
    for i, day in enumerate(parsed_days):
        tmax = daily["temperature_2m_max"][i]
        tmin = daily["temperature_2m_min"][i]
        if tmax is None or tmin is None:
            raise ValueError(f"{name}: missing daily extrema on {day}")
        tmax, tmin = float(tmax), float(tmin)
        if not all(math.isfinite(t) and -100 <= t <= 70 for t in (tmax, tmin)) or tmin > tmax:
            raise ValueError(f"{name}: invalid daily extrema on {day}")
        daily_records.append({
            "commune": name, "forecast_date_utc": day.isoformat(),
            "temperature_max_c": tmax, "temperature_min_c": tmin,
            "retrieved_at_utc": retrieved_at, "source": "Open-Meteo Forecast API",
        })

    metadata.append({
        "commune": name,
        "latitude": params["latitude"],
        "longitude": params["longitude"],
        "model": data.get("model", "not_specified"),
        "timezone": data.get("timezone"),
        "hours": len(times),
    })

    print(f"[{index}/11] {name}: 96 hours OK", flush=True)
    time.sleep(1)

if len(records) != 11 * 96:
    raise ValueError("Unexpected total forecast count")

keys = {
    (row["commune"], row["forecast_time_utc"])
    for row in records
}

if len(keys) != len(records):
    raise ValueError("Duplicate commune-hour records")

if len(daily_records) != 11 * 4 or len({(r["commune"],r["forecast_date_utc"]) for r in daily_records}) != len(daily_records):
    raise ValueError("Unexpected or duplicate daily forecast rows")

csv_path = OUTPUT / f"forecast_{run_id}.csv"
daily_path = OUTPUT / f"daily_forecast_{run_id}.csv"
meta_path = OUTPUT / f"forecast_{run_id}.json"

with csv_path.open("x", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(records)

with daily_path.open("x", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "commune", "forecast_date_utc", "temperature_max_c", "temperature_min_c",
        "retrieved_at_utc", "source",
    ])
    writer.writeheader()
    writer.writerows(daily_records)

with meta_path.open("x", encoding="utf-8") as f:
    json.dump({
        "retrieved_at_utc": retrieved_at,
        "provider": "Open-Meteo",
        "endpoint": URL,
        "forecast_days": 4,
        "daily_file": str(daily_path),
        "daily_variables": ["temperature_2m_max", "temperature_2m_min"],
        "locations": metadata,
    }, f, indent=2, ensure_ascii=False)

print("\n=== FORECAST INGESTION RESULTS ===")
print("Communes:", len(communes))
print("Forecast hours per commune:", 96)
print("Total records:", len(records))
print("CSV:", csv_path)
print("Daily CSV:", daily_path)
print("Metadata:", meta_path)
print("Historical data modified: NO")
print("FWI alerts generated: NO")
print("\nSUCCESS: Forecast ingestion completed!")
