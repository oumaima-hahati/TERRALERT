#!/usr/bin/env python3
"""Prepare local-noon weather and preceding 24h rainfall for FWI."""

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

source = Path(
    "data/weather/historical/era5_seamless/"
    "era5_seamless_2024_01.json"
)
output = Path("data/weather/processed/fwi_weather_test_2024_01.csv")

payload = json.loads(source.read_text(encoding="utf-8"))
tz = ZoneInfo("Africa/Casablanca")
records = []

for commune, result in zip(payload["communes"], payload["data"]):
    hourly = result["hourly"]
    observations = {}

    for i, timestamp in enumerate(hourly["time"]):
        dt = datetime.fromisoformat(timestamp).replace(
            tzinfo=timezone.utc
        )
        observations[dt] = {
            "temp": hourly["temperature_2m"][i],
            "rh": hourly["relative_humidity_2m"][i],
            "wind": hourly["wind_speed_10m"][i],
            "rain": hourly["precipitation"][i],
        }

    for utc_dt, weather in sorted(observations.items()):
        local_dt = utc_dt.astimezone(tz)

        if local_dt.hour != 12 or local_dt.minute != 0:
            continue

        previous_24 = [
            observations.get(utc_dt - timedelta(hours=h))
            for h in range(24)
        ]

        if any(v is None for v in previous_24):
            continue

        if any(v["rain"] is None for v in previous_24):
            continue

        if any(weather[k] is None for k in ("temp", "rh", "wind")):
            continue

        records.append({
            "commune": commune,
            "date": local_dt.date().isoformat(),
            "observation_utc": utc_dt.isoformat(),
            "temperature_c": weather["temp"],
            "relative_humidity_pct": weather["rh"],
            "wind_speed_10m_kmh": weather["wind"],
            "rainfall_previous_24h_mm": round(
                sum(v["rain"] for v in previous_24), 3
            ),
        })

fields = [
    "commune", "date", "observation_utc",
    "temperature_c", "relative_humidity_pct",
    "wind_speed_10m_kmh", "rainfall_previous_24h_mm",
]

output.parent.mkdir(parents=True, exist_ok=True)

with output.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(records)

print("=== FWI WEATHER INPUT TEST ===")
print("Source:", payload["model"])
print("Communes:", len(set(r["commune"] for r in records)))
print("Records:", len(records))
print("First date:", min(r["date"] for r in records))
print("Last date:", max(r["date"] for r in records))
print("Output:", output)
print("Example:", records[0])
