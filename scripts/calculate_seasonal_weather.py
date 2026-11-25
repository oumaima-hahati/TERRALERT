#!/usr/bin/env python3
"""Check monthly coverage and calculate complete-season weather summaries."""

import csv
import calendar
from collections import defaultdict
from datetime import date
from pathlib import Path

SOURCE = Path("data/weather/processed/daily_weather.csv")
OUTPUT = Path("data/weather/processed")
OUTPUT.mkdir(parents=True, exist_ok=True)

with SOURCE.open(encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))

monthly = defaultdict(list)
for row in rows:
    d = date.fromisoformat(row["date"])
    monthly[(row["commune"], d.year, d.month)].append(row)

coverage = []
for (commune, year, month), items in sorted(monthly.items()):
    expected = calendar.monthrange(year, month)[1]
    actual = len({r["date"] for r in items})
    coverage.append({
        "commune": commune,
        "year": year,
        "month": month,
        "days_available": actual,
        "days_expected": expected,
        "complete": actual == expected,
    })

with (OUTPUT / "weather_coverage.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    writer = csv.DictWriter(f, fieldnames=coverage[0])
    writer.writeheader()
    writer.writerows(coverage)

def season_info(d):
    if d.month in (12, 1, 2):
        return "DJF", d.year + (d.month == 12)
    if d.month in (3, 4, 5):
        return "MAM", d.year
    if d.month in (6, 7, 8):
        return "JJA", d.year
    return "SON", d.year

seasons = defaultdict(list)
for row in rows:
    d = date.fromisoformat(row["date"])
    season, year = season_info(d)
    seasons[(row["commune"], year, season)].append(row)

months_by_season = {
    "DJF": [(12, -1), (1, 0), (2, 0)],
    "MAM": [(3, 0), (4, 0), (5, 0)],
    "JJA": [(6, 0), (7, 0), (8, 0)],
    "SON": [(9, 0), (10, 0), (11, 0)],
}

summaries = []
incomplete = 0

for (commune, year, season), items in sorted(seasons.items()):
    expected_days = sum(
        calendar.monthrange(year + offset, month)[1]
        for month, offset in months_by_season[season]
    )

    if len({r["date"] for r in items}) != expected_days:
        incomplete += 1
        continue

    def avg(field):
        return sum(float(r[field]) for r in items) / len(items)

    summaries.append({
        "commune": commune,
        "year": year,
        "season": season,
        "days": len(items),
        "temperature_mean_c": round(avg("temperature_mean_c"), 3),
        "humidity_mean_pct": round(avg("humidity_mean_pct"), 3),
        "wind_mean_kmh": round(avg("wind_speed_mean_kmh"), 3),
        "precipitation_total_mm": round(
            sum(float(r["precipitation_total_mm"]) for r in items), 3
        ),
    })

fields = [
    "commune", "year", "season", "days",
    "temperature_mean_c", "humidity_mean_pct",
    "wind_mean_kmh", "precipitation_total_mm",
]

with (OUTPUT / "seasonal_weather_summary.csv").open(
    "w", newline="", encoding="utf-8"
) as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(summaries)

print("=== SEASONAL WEATHER PROCESSING ===")
print("Daily records:", len(rows))
print("Monthly coverage records:", len(coverage))
print("Complete commune-seasons:", len(summaries))
print("Incomplete commune-seasons excluded:", incomplete)
print("Outputs:")
print(" -", OUTPUT / "weather_coverage.csv")
print(" -", OUTPUT / "seasonal_weather_summary.csv")
print("\nAvailable complete seasons:")
print(sorted({(r["year"], r["season"]) for r in summaries}))
