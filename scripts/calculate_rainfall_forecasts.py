#!/usr/bin/env python3
"""TERRALERT: 24h/72h Open-Meteo forecast aggregation."""

import csv
import os
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

SOURCE = Path("data/weather/forecasts/open_meteo")
OUTPUT = Path("data/weather/forecasts/aggregated")
OUTPUT.mkdir(parents=True, exist_ok=True)

files = sorted(SOURCE.glob("forecast_*.csv"))
if not files:
    raise SystemExit("ERROR: No hourly forecast files found.")

input_file = (
    Path(os.environ["TERRALERT_HOURLY_FORECAST_FILE"])
    if os.environ.get("TERRALERT_HOURLY_FORECAST_FILE")
    else files[-1]
)

if not input_file.is_file():
    raise FileNotFoundError(input_file)
run_id = input_file.stem.removeprefix("forecast_")

with input_file.open(newline="", encoding="utf-8") as f:
    records = list(csv.DictReader(f))

required = {
    "commune", "forecast_time_utc", "retrieved_at_utc",
    "precipitation_mm", "temperature_c",
    "relative_humidity_pct", "wind_speed_kmh",
}

if not records or not required.issubset(records[0]):
    raise ValueError("Missing required forecast fields")

groups = {}
retrieval_times = set()

for r in records:
    name = r["commune"]
    stamp = datetime.fromisoformat(
        r["forecast_time_utc"].replace("Z", "+00:00")
    )

    retrieved = datetime.fromisoformat(
        r["retrieved_at_utc"].replace("Z", "+00:00")
    )

    if stamp.utcoffset() != timedelta(0):
        raise ValueError("Forecast timestamp must be UTC")

    if retrieved.utcoffset() != timedelta(0):
        raise ValueError("Retrieval timestamp must be UTC")

    retrieval_times.add(retrieved)

    values = {}
    for column in (
        "precipitation_mm", "temperature_c",
        "relative_humidity_pct", "wind_speed_kmh"
    ):
        value = float(r[column])
        if not math.isfinite(value):
            raise ValueError(f"Invalid {column}: {name}")
        values[column] = value

    if values["precipitation_mm"] < 0:
        raise ValueError(f"Negative rainfall: {name}")
    if values["wind_speed_kmh"] < 0:
        raise ValueError(f"Negative wind speed: {name}")
    if not 0 <= values["relative_humidity_pct"] <= 100:
        raise ValueError(f"Invalid humidity: {name}")

    groups.setdefault(name, []).append((stamp, values))

if len(groups) != 11 or len(records) != 1056:
    raise ValueError("Expected 11 communes x 96 hourly records")

if len(retrieval_times) != 1:
    raise ValueError("Inconsistent forecast retrieval timestamps")

retrieved = next(iter(retrieval_times))

# First whole forecast hour strictly after the download instant.
start = retrieved.replace(minute=0, second=0, microsecond=0)
if start <= retrieved:
    start += timedelta(hours=1)

results = []

for commune, rows in sorted(groups.items()):
    rows.sort(key=lambda item: item[0])

    if len(rows) != 96 or len({t for t, _ in rows}) != 96:
        raise ValueError(f"Invalid hourly coverage: {commune}")

    by_time = dict(rows)

    for horizon in (24, 72):
        expected = [
            start + timedelta(hours=i)
            for i in range(horizon)
        ]

        if any(t not in by_time for t in expected):
            raise ValueError(
                f"{commune}: incomplete future {horizon}h window"
            )

        subset = [by_time[t] for t in expected]

        rain = sum(x["precipitation_mm"] for x in subset)
        temps = [x["temperature_c"] for x in subset]

        results.append({
            "commune": commune,
            "forecast_run_id": run_id,
            "retrieved_at_utc": retrieved.isoformat(),
            "window_start_utc": start.isoformat(),
            "window_end_utc": (
                start + timedelta(hours=horizon)
            ).isoformat(),
            "horizon_hours": horizon,
            "hours_available": len(subset),
            "rainfall_total_mm": round(rain, 2),
            "temperature_mean_c": round(
                sum(temps) / len(temps), 2
            ),
            "temperature_min_c": round(min(temps), 2),
            "temperature_max_c": round(max(temps), 2),
            "humidity_mean_pct": round(
                sum(x["relative_humidity_pct"] for x in subset)
                / len(subset), 2
            ),
            "wind_mean_kmh": round(
                sum(x["wind_speed_kmh"] for x in subset)
                / len(subset), 2
            ),
            "source": "Open-Meteo",
            "status": "PROVISIONAL_RESEARCH",
        })

if len(results) != 22:
    raise ValueError("Expected 22 commune-horizon records")

output = OUTPUT / f"rainfall_weather_24h_72h_{run_id}.csv"

with output.open("x", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f, fieldnames=list(results[0].keys())
    )
    writer.writeheader()
    writer.writerows(results)

print("=== TERRALERT RAINFALL FORECASTS ===")
print("Study areas:", len(groups))
print("Forecast run:", run_id)
print("Forecast start (UTC):", start.isoformat())
print("Horizons: 24h, 72h")
print("Total records:", len(results))

for horizon in (24, 72):
    subset = [
        r for r in results
        if r["horizon_hours"] == horizon
    ]
    print(f"\n=== {horizon}h RAINFALL ===")
    for row in sorted(
        subset,
        key=lambda r: r["rainfall_total_mm"],
        reverse=True
    ):
        print(
            f'{row["commune"]:20} '
            f'{row["rainfall_total_mm"]:7.2f} mm'
        )

print("\nOutput:", output)
print("Public alerts generated: NO")
print("\nSUCCESS: 24h/72h forecasts calculated!")
