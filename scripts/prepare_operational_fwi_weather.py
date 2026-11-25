#!/usr/bin/env python3
"""Prepare provisional recent and forecast FWI weather inputs."""

import csv
import math
import time
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

BASE = Path("data/weather")
LOCATIONS = BASE / "locations/commune_coordinates.csv"
OUTPUT = BASE / "forecasts/fwi_inputs"
OUTPUT.mkdir(parents=True, exist_ok=True)

TZ = ZoneInfo("Africa/Casablanca")
URL = "https://api.open-meteo.com/v1/forecast"

FIELDS = [
    "commune", "date", "observation_utc",
    "temperature_c", "relative_humidity_pct",
    "wind_speed_10m_kmh", "rainfall_previous_24h_mm",
    "period", "retrieved_at_utc",
]

with LOCATIONS.open(encoding="utf-8-sig", newline="") as f:
    communes = list(csv.DictReader(f))

if len(communes) != 11:
    raise ValueError("Expected 11 communes")

run_time = datetime.now(timezone.utc)
run_id = run_time.strftime("%Y%m%dT%H%M%SZ")

results = []
session = requests.Session()

print("=== TERRALERT OPERATIONAL FWI PREPARATION ===", flush=True)

for number, location in enumerate(communes, 1):
    name = location["commune"]

    params = {
        "latitude": float(location["latitude"]),
        "longitude": float(location["longitude"]),
        "hourly": (
            "temperature_2m,relative_humidity_2m,"
            "wind_speed_10m,precipitation"
        ),
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "temperature_unit": "celsius",
        "timezone": "UTC",
        "past_days": 35,
        "forecast_days": 4,
    }

    response = session.get(URL, params=params, timeout=60)
    response.raise_for_status()
    data = response.json()

    if data.get("timezone") != "GMT":
        raise ValueError(
            f"{name}: Unexpected API timezone: {data.get('timezone')}"
        )

    hourly = data["hourly"]
    times = hourly["time"]

    variables = [
        "temperature_2m",
        "relative_humidity_2m",
        "wind_speed_10m",
        "precipitation",
    ]

    if any(len(hourly[v]) != len(times) for v in variables):
        raise ValueError(f"{name}: Inconsistent hourly arrays")

    observations = {}

    for i, stamp in enumerate(times):
        dt = datetime.fromisoformat(stamp).replace(
            tzinfo=timezone.utc
        )

        values = {}
        for variable in variables:
            raw = hourly[variable][i]
            if raw is None or not math.isfinite(float(raw)):
                raise ValueError(f"{name}: Invalid {variable} at {stamp}")
            values[variable] = float(raw)

        if not 0 <= values["relative_humidity_2m"] <= 100:
            raise ValueError(f"{name}: Invalid humidity")
        if values["wind_speed_10m"] < 0:
            raise ValueError(f"{name}: Invalid wind")
        if values["precipitation"] < 0:
            raise ValueError(f"{name}: Invalid rainfall")
        if dt in observations:
            raise ValueError(f"{name}: Duplicate hour")

        observations[dt] = values

    first_local = min(observations).astimezone(TZ).date()
    last_local = max(observations).astimezone(TZ).date()

    current = first_local
    count = 0
    future_count = 0

    while current <= last_local:
        local_noon = datetime(
            current.year, current.month, current.day,
            12, tzinfo=TZ
        )
        utc_noon = local_noon.astimezone(timezone.utc)

        # The 24 hourly totals ending at local noon.
        rain_hours = [
            utc_noon - timedelta(hours=h)
            for h in range(23, -1, -1)
        ]

        if (
            utc_noon not in observations
            or not all(h in observations for h in rain_hours)
        ):
            current += timedelta(days=1)
            continue

        weather = observations[utc_noon]
        rainfall = sum(
            observations[h]["precipitation"]
            for h in rain_hours
        )

        is_future = utc_noon > run_time

        results.append({
            "commune": name,
            "date": current.isoformat(),
            "observation_utc": utc_noon.isoformat(),
            "temperature_c": round(
                weather["temperature_2m"], 3
            ),
            "relative_humidity_pct": round(
                weather["relative_humidity_2m"], 3
            ),
            "wind_speed_10m_kmh": round(
                weather["wind_speed_10m"], 3
            ),
            "rainfall_previous_24h_mm": round(rainfall, 3),
            "period": "forecast" if is_future else "recent",
            "retrieved_at_utc": run_time.isoformat(),
        })

        count += 1
        future_count += int(is_future)
        current += timedelta(days=1)

    print(
        f"[{number}/11] {name}: "
        f"{count} daily records, {future_count} future",
        flush=True
    )

    time.sleep(1)

keys = {(r["commune"], r["date"]) for r in results}
if len(keys) != len(results):
    raise ValueError("Duplicate commune-date records")

future = [r for r in results if r["period"] == "forecast"]
future_dates = sorted({r["date"] for r in future})

if len(future_dates) < 3:
    raise ValueError("Fewer than 3 future FWI dates available")

for day in future_dates[:3]:
    if sum(r["date"] == day for r in future) != 11:
        raise ValueError(f"Incomplete future FWI coverage: {day}")

output = OUTPUT / f"fwi_weather_{run_id}.csv"

with output.open("x", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(sorted(
        results, key=lambda r: (r["commune"], r["date"])
    ))

print("\n=== OPERATIONAL FWI WEATHER RESULTS ===")
print("Communes:", len(communes))
print("Total daily records:", len(results))
print("Future local-noon dates:", future_dates)
print("Future commune-day records:", len(future))
print("Output:", output)
print("FWI calculated: NO")
print("Alerts generated: NO")
print("\nSUCCESS: Operational FWI weather inputs prepared!")
