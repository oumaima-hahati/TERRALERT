#!/usr/bin/env python3
"""TERRALERT historical weather and temperature extremes QA."""

from pathlib import Path
import json
import pandas as pd

BASE = Path("data")
WEATHER = BASE / "weather/processed/daily_weather_nasa_chirps_2001_2025.csv"
OUT = BASE / "qa"
OUT.mkdir(parents=True, exist_ok=True)

tests = []

def check(name, condition, details=""):
    passed = bool(condition)
    tests.append({
        "check": name,
        "passed": passed,
        "details": str(details)
    })
    print(f'{"PASS" if passed else "FAIL"}: {name}')

weather = pd.read_csv(WEATHER, parse_dates=["date"])

check("11 study areas", weather["commune"].nunique() == 11)
check("100441 weather records", len(weather) == 100441)
check(
    "No duplicate commune-dates",
    not weather.duplicated(["commune", "date"]).any()
)
check(
    "Weather period 2001–2025",
    weather["date"].min() == pd.Timestamp("2001-01-01")
    and weather["date"].max() == pd.Timestamp("2025-12-31")
)

numeric = [
    "temperature_mean_c", "temperature_min_c",
    "temperature_max_c", "humidity_mean_pct",
    "wind_mean_ms", "wind_mean_kmh", "precipitation_mm"
]

check(
    "No missing meteorological values",
    not weather[numeric].isna().any().any()
)

check(
    "Temperature ordering",
    (
        (weather["temperature_min_c"] <= weather["temperature_mean_c"])
        & (weather["temperature_mean_c"] <= weather["temperature_max_c"])
    ).all()
)

check(
    "Humidity within 0–100%",
    weather["humidity_mean_pct"].between(0, 100).all()
)

check(
    "Nonnegative wind and precipitation",
    (
        (weather["wind_mean_ms"] >= 0)
        & (weather["wind_mean_kmh"] >= 0)
        & (weather["precipitation_mm"] >= 0)
    ).all()
)

check(
    "Wind conversion m/s → km/h",
    (
        weather["wind_mean_kmh"]
        - weather["wind_mean_ms"] * 3.6
    ).abs().max() < 0.1
)

for kind, prefix in [
    ("Heatwave", "heatwaves"),
    ("Cold-wave", "coldwaves"),
]:
    folder = BASE / prefix / "processed"

    events = pd.read_csv(
        folder / f"{'heatwave' if prefix == 'heatwaves' else 'coldwave'}_events_2001_2025.csv",
        parse_dates=["start_date", "end_date"]
    )

    summary = pd.read_csv(
        folder / f"{'heatwave' if prefix == 'heatwaves' else 'coldwave'}_commune_summary.csv"
    )

    id_col = "heatwave_id" if prefix == "heatwaves" else "coldwave_id"
    day_col = "heatwave_days" if prefix == "heatwaves" else "coldwave_days"
    event_col = "heatwave_events" if prefix == "heatwaves" else "coldwave_events"

    expected = 1025 if prefix == "heatwaves" else 1200
    expected_days = 4192 if prefix == "heatwaves" else 5057

    check(
        f"{kind}: expected event count",
        len(events) == expected,
        f"{len(events)} events"
    )

    check(
        f"{kind}: unique event IDs",
        not events[id_col].duplicated().any()
    )

    check(
        f"{kind}: minimum 3-day duration",
        events["duration_days"].ge(3).all()
    )

    check(
        f"{kind}: continuous event dates",
        (
            (events["end_date"] - events["start_date"]).dt.days + 1
            == events["duration_days"]
        ).all()
    )

    check(
        f"{kind}: event-day totals",
        events["duration_days"].sum() == expected_days
        and summary[day_col].sum() == expected_days
    )

    check(
        f"{kind}: event counts match summary",
        summary[event_col].sum() == len(events)
    )

    check(
        f"{kind}: all study areas represented",
        events["commune"].nunique() == 11
        and summary["commune"].nunique() == 11
    )

results = {
    "project": "TERRALERT",
    "validation": "Weather, Heatwave & Cold-Wave QA",
    "period": "2001–2025",
    "total_checks": len(tests),
    "passed": sum(t["passed"] for t in tests),
    "failed": sum(not t["passed"] for t in tests),
    "checks": tests,
    "scope": "Internal structural QA; not independent scientific validation"
}

output = OUT / "weather_extremes_qa.json"
output.write_text(
    json.dumps(results, indent=2),
    encoding="utf-8"
)

print("\n=== TERRALERT WEATHER EXTREMES QA ===")
print("Checks:", results["total_checks"])
print("Passed:", results["passed"])
print("Failed:", results["failed"])
print("Report:", output)

if results["failed"]:
    raise SystemExit("QA FAILED — review the checks above.")

print("\nSUCCESS: Internal weather-extremes QA passed!")
