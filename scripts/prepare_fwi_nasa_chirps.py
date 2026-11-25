#!/usr/bin/env python3
"""Prepare provisional TERRALERT FWI inputs using NASA POWER + CHIRPS."""

import csv
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path("data/weather")
NASA = BASE / "nasa_power/hourly"
CHIRPS = BASE / "chirps_v3/earth_engine"
OUTPUT = BASE / "processed/fwi_weather_nasa_chirps_2001_2025.csv"

TZ = ZoneInfo("Africa/Casablanca")
FIELDS = [
    "commune",
    "date",
    "observation_utc",
    "temperature_c",
    "relative_humidity_pct",
    "wind_speed_10m_kmh",
    "rainfall_previous_24h_mm",
]

with (BASE / "locations/commune_coordinates.csv").open(
    encoding="utf-8-sig", newline=""
) as f:
    communes = {row["commune"] for row in csv.DictReader(f)}

print("=== LOADING CHIRPS RAINFALL ===", flush=True)

rain = {}

# Include 2000 for the first rainfall lookback in 2001.
for year in range(2000, 2026):
    path = CHIRPS / f"terralert_chirps_v3_sat_{year}.csv"

    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            value = float(row["precipitation_mm"])
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"Invalid rainfall: {row}")

            key = (row["commune"], row["date"])
            if key in rain:
                raise ValueError(f"Duplicate rainfall: {key}")

            rain[key] = value

print("CHIRPS records:", len(rain), flush=True)

print("\n=== PROCESSING NASA POWER ===", flush=True)

files = sorted(NASA.glob("nasa_power_*.json"))
if len(files) != 275:
    raise ValueError(f"Expected 275 NASA files, got {len(files)}")

results = []
seen = set()

for number, path in enumerate(files, 1):

    with path.open(encoding="utf-8") as f:
        content = json.load(f)

    commune = content["commune"]
    year = int(content["year"])

    if commune not in communes or not 2001 <= year <= 2025:
        raise ValueError(f"Unexpected commune/year: {path.name}")

    if (commune, year) in seen:
        raise ValueError(f"Duplicate NASA archive: {commune}, {year}")
    seen.add((commune, year))

    if content.get("time_standard") != "UTC":
        raise ValueError(f"Expected UTC timestamps: {path.name}")

    params = content["data"]["properties"]["parameter"]

    for variable in ("T2M", "RH2M", "WS10M"):
        if variable not in params:
            raise ValueError(f"Missing {variable}: {path.name}")

    start = datetime(year, 1, 1)
    end = datetime(year + 1, 1, 1)

    current = start

    while current < end:
        local_noon = current.replace(
            hour=12,
            tzinfo=TZ
        )

        utc_noon = local_noon.astimezone(timezone.utc)
        timestamp = utc_noon.strftime("%Y%m%d%H")

        def get_value(variable):
            raw = params[variable].get(timestamp)
            if raw is None:
                raise ValueError(
                    f"Missing {variable}: {commune}, {timestamp}"
                )

            value = float(raw)
            if not math.isfinite(value) or value <= -900:
                raise ValueError(
                    f"Invalid {variable}: {commune}, {timestamp}"
                )
            return value

        temp = get_value("T2M")
        humidity = get_value("RH2M")
        wind_ms = get_value("WS10M")

        if not 0 <= humidity <= 100 or wind_ms < 0:
            raise ValueError(
                f"Invalid humidity/wind: {commune}, {current.date()}"
            )

        previous_day = (
            current.date() - timedelta(days=1)
        ).isoformat()

        rainfall_key = (commune, previous_day)

        if rainfall_key not in rain:
            raise ValueError(
                f"Missing CHIRPS rainfall: {rainfall_key}"
            )

        results.append({
            "commune": commune,
            "date": current.date().isoformat(),
            "observation_utc": utc_noon.isoformat(),
            "temperature_c": round(temp, 3),
            "relative_humidity_pct": round(humidity, 3),
            "wind_speed_10m_kmh": round(wind_ms * 3.6, 3),
            "rainfall_previous_24h_mm": rain[rainfall_key],
        })

        current += timedelta(days=1)

    if number % 25 == 0:
        print(f"Processed {number}/275 files", flush=True)

expected = 100441

if len(results) != expected:
    raise ValueError(
        f"Expected {expected} records, got {len(results)}"
    )

keys = [(r["commune"], r["date"]) for r in results]
if len(set(keys)) != expected:
    raise ValueError("Duplicate commune-date records")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
temp_path = OUTPUT.with_suffix(".csv.tmp")

with temp_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(sorted(
        results,
        key=lambda r: (r["commune"], r["date"])
    ))

temp_path.replace(OUTPUT)

print("\n=== FWI WEATHER PREPARATION ===")
print("Communes:", len(communes))
print("Records:", len(results))
print("Period: 2001–2025")
print("Weather source: NASA POWER")
print("Rainfall source: CHIRPS v3 DAILY_SAT")
print("Rainfall timing: Previous calendar day (approximation)")
print("Observation: 12:00 Africa/Casablanca civil time")
print("ERA5 used: NO")
print("Saved:", OUTPUT)
print("\nSUCCESS: Provisional FWI inputs created!")
