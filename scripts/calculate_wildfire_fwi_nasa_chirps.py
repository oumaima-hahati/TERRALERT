#!/usr/bin/env python3
"""Calculate provisional daily Canadian FWI for TERRALERT."""

import csv
import math
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from cffdrs.fwi import (
    fine_fuel_moisture_code,
    duff_moisture_code,
    drought_code,
    initial_spread_index,
    buildup_index,
    fire_weather_index,
)

SOURCE = Path("data/weather/processed/fwi_weather_nasa_chirps_2001_2025.csv")
LOCATIONS = Path("data/weather/locations/commune_coordinates.csv")
OUTPUT = Path("data/wildfires/processed/wildfire_fwi_nasa_chirps_2001_2025.csv")

INITIAL_FFMC = 85.0
INITIAL_DMC = 6.0
INITIAL_DC = 15.0
WARMUP_DAYS = 30

FIELDS = [
    "commune", "date", "temperature_c",
    "relative_humidity_pct", "wind_speed_kmh",
    "rainfall_24h_mm", "ffmc", "dmc", "dc",
    "isi", "bui", "fwi", "danger_level",
    "segment", "days_since_reset", "quality",
]

def danger_level(fwi):
    if fwi < 5.2:
        return "Very Low"
    if fwi < 11.2:
        return "Low"
    if fwi < 21.3:
        return "Moderate"
    if fwi < 38:
        return "High"
    if fwi < 50:
        return "Very High"
    return "Extreme"

def finite(value, name):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"Non-finite {name}: {value}")
    return result

with LOCATIONS.open(encoding="utf-8", newline="") as f:
    locations = {
        row["commune"]: float(row["latitude"])
        for row in csv.DictReader(f)
    }

if len(locations) != 11:
    raise ValueError("Expected 11 commune coordinates")

weather = defaultdict(list)

with SOURCE.open(encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        weather[row["commune"]].append(row)

if set(weather) != set(locations):
    raise ValueError("Weather communes do not match coordinates")

# Verify the FWI library executes before processing history.
test_ffmc = fine_fuel_moisture_code(
    ffmc_yda=85.0, temp=25.0, rh=40.0, ws=15.0, prec=0.0
)
if not math.isfinite(float(test_ffmc)):
    raise RuntimeError("FWI library smoke test failed")

results = []
total_resets = 0

for commune in sorted(weather):
    rows = sorted(weather[commune], key=lambda r: r["date"])
    latitude = locations[commune]

    ffmc_previous = INITIAL_FFMC
    dmc_previous = INITIAL_DMC
    dc_previous = INITIAL_DC

    previous_date = None
    segment = 0
    days_since_reset = 0

    for row in rows:
        current_date = date.fromisoformat(row["date"])

        if previous_date is not None and current_date <= previous_date:
            raise ValueError(f"Duplicate/out-of-order date: {commune}")

        if previous_date is None or (
            current_date - previous_date != timedelta(days=1)
        ):
            ffmc_previous = INITIAL_FFMC
            dmc_previous = INITIAL_DMC
            dc_previous = INITIAL_DC
            days_since_reset = 0
            segment += 1

            if previous_date is not None:
                total_resets += 1

        temp = finite(row["temperature_c"], "temperature")
        rh = finite(row["relative_humidity_pct"], "humidity")
        wind = finite(row["wind_speed_10m_kmh"], "wind")
        rain = finite(row["rainfall_previous_24h_mm"], "rain")

        if not 0 <= rh <= 100 or wind < 0 or rain < 0:
            raise ValueError(
                f"Invalid meteorological inputs: {commune}, {current_date}"
            )

        month = current_date.month

        ffmc = finite(
            fine_fuel_moisture_code(
                ffmc_yda=ffmc_previous,
                temp=temp, rh=rh, ws=wind, prec=rain
            ),
            "FFMC",
        )

        dmc = finite(
            duff_moisture_code(
                dmc_yda=dmc_previous,
                temp=temp, rh=rh, prec=rain,
                lat=latitude, mon=month
            ),
            "DMC",
        )

        dc = finite(
            drought_code(
                dc_yda=dc_previous,
                temp=temp, rh=rh, prec=rain,
                lat=latitude, mon=month
            ),
            "DC",
        )

        isi = finite(
            initial_spread_index(ffmc=ffmc, ws=wind),
            "ISI",
        )

        bui = finite(
            buildup_index(dmc=dmc, dc=dc),
            "BUI",
        )

        fwi = finite(
            fire_weather_index(isi=isi, bui=bui),
            "FWI",
        )

        days_since_reset += 1

        results.append({
            "commune": commune,
            "date": current_date.isoformat(),
            "temperature_c": temp,
            "relative_humidity_pct": rh,
            "wind_speed_kmh": wind,
            "rainfall_24h_mm": rain,
            "ffmc": round(ffmc, 3),
            "dmc": round(dmc, 3),
            "dc": round(dc, 3),
            "isi": round(isi, 3),
            "bui": round(bui, 3),
            "fwi": round(fwi, 3),
            "danger_level": danger_level(fwi),
            "segment": segment,
            "days_since_reset": days_since_reset,
            "quality": (
                "warmup_provisional"
                if days_since_reset <= WARMUP_DAYS
                else "provisional"
            ),
        })

        ffmc_previous = ffmc
        dmc_previous = dmc
        dc_previous = dc
        previous_date = current_date

if len(results) != sum(len(v) for v in weather.values()):
    raise ValueError("FWI output row count mismatch")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
temporary = OUTPUT.with_suffix(".csv.tmp")

with temporary.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(results)

temporary.replace(OUTPUT)

print("=== TERRALERT HISTORICAL WILDFIRE FWI ===")
print("Communes:", len(weather))
print("FWI records:", len(results))
print("Historical gap resets:", total_resets)
print("Warm-up records:", sum(
    r["quality"] == "warmup_provisional" for r in results
))
print("Provisional post-warm-up records:", sum(
    r["quality"] == "provisional" for r in results
))
print("FWI minimum:", min(r["fwi"] for r in results))
print("FWI maximum:", max(r["fwi"] for r in results))
print("Saved:", OUTPUT)

print("\n=== DANGER DISTRIBUTION ===")
for level in [
    "Very Low", "Low", "Moderate",
    "High", "Very High", "Extreme"
]:
    count = sum(
        r["danger_level"] == level
        and r["quality"] == "provisional"
        for r in results
    )
    print(f"{level:12}: {count}")
