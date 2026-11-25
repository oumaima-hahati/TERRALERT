#!/usr/bin/env python3
"""Calculate provisional FWI using recent and forecast weather."""

import csv
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

WEATHER_DIR = Path("data/weather/forecasts/fwi_inputs")
OUTPUT_DIR = Path("data/wildfires/forecasts")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

files = sorted(WEATHER_DIR.glob("fwi_weather_*.csv"))

if not files:
    raise SystemExit("No operational FWI weather file found.")

selected = os.environ.get("TERRALERT_FWI_WEATHER_FILE")
source_weather = Path(selected) if selected else files[-1]

if (
    not source_weather.is_file()
    or source_weather.resolve().parent != WEATHER_DIR.resolve()
    or not source_weather.name.startswith("fwi_weather_")
):
    raise ValueError("Invalid operational FWI input file")
run_id = source_weather.stem.replace("fwi_weather_", "")

base_script = Path("scripts/calculate_wildfire_fwi.py")
generated_script = OUTPUT_DIR / f"_fwi_calculator_{run_id}.py"

all_output = OUTPUT_DIR / f"fwi_all_{run_id}.csv"
forecast_output = OUTPUT_DIR / f"fwi_forecast_{run_id}.csv"

with source_weather.open(encoding="utf-8", newline="") as f:
    weather = list(csv.DictReader(f))

period_lookup = {
    (row["commune"], row["date"]): row["period"]
    for row in weather
}

if len(period_lookup) != len(weather):
    raise ValueError("Duplicate weather commune-date records")

if set(period_lookup.values()) != {"recent", "forecast"}:
    raise ValueError("Expected recent and forecast weather records")

code = base_script.read_text(encoding="utf-8")

replacements = {
    "data/weather/processed/fwi_weather_historical.csv":
        str(source_weather),
    "data/wildfires/processed/wildfire_fwi_historical.csv":
        str(all_output),
}

for old, new in replacements.items():
    if code.count(old) != 1:
        raise ValueError(f"Unexpected calculator source: {old}")
    code = code.replace(old, new)

generated_script.write_text(code, encoding="utf-8")

print("=== CALCULATING OPERATIONAL FWI ===", flush=True)

subprocess.run(
    [sys.executable, str(generated_script)],
    check=True
)

with all_output.open(encoding="utf-8", newline="") as f:
    all_rows = list(csv.DictReader(f))

if len(all_rows) != len(weather):
    raise ValueError("FWI row count mismatch")

forecast_rows = []

for row in all_rows:
    key = (row["commune"], row["date"])

    if key not in period_lookup:
        raise ValueError(f"Unexpected FWI record: {key}")

    if period_lookup[key] != "forecast":
        continue

    if row["quality"] != "provisional":
        raise ValueError(f"Forecast still in warm-up: {key}")

    row["model_status"] = "PROVISIONAL_RESEARCH"
    row["weather_source"] = "Open-Meteo"
    row["forecast_run"] = run_id

    forecast_rows.append(row)

dates = sorted({row["date"] for row in forecast_rows})

if len(forecast_rows) != 33 or len(dates) != 3:
    raise ValueError(
        f"Expected 33 forecast rows over 3 dates; "
        f"got {len(forecast_rows)} rows over {len(dates)} dates"
    )

for day in dates:
    if sum(row["date"] == day for row in forecast_rows) != 11:
        raise ValueError(f"Incomplete commune coverage: {day}")

fields = list(forecast_rows[0])

with forecast_output.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(
        sorted(forecast_rows, key=lambda r: (r["date"], r["commune"]))
    )

print("\n=== TERRALERT PROVISIONAL FWI FORECAST ===")
print("Forecast run:", run_id)
print("Communes:", len({r["commune"] for r in forecast_rows}))
print("Forecast dates:", dates)
print("Forecast records:", len(forecast_rows))
print("FWI minimum:", min(float(r["fwi"]) for r in forecast_rows))
print("FWI maximum:", max(float(r["fwi"]) for r in forecast_rows))

print("\nDanger distribution:")
for level, count in sorted(
    Counter(r["danger_level"] for r in forecast_rows).items()
):
    print(f"{level}: {count}")

print("\nSaved:", forecast_output)
print("Public alerts generated: NO")
print("Status: PROVISIONAL RESEARCH")
print("\nSUCCESS: Provisional wildfire forecasts calculated!")
