import csv
import json
import math
from collections import defaultdict
from datetime import datetime, date, timedelta
from pathlib import Path

BASE = Path("data/weather")
NASA = BASE / "nasa_power/hourly"
CHIRPS = BASE / "chirps_v3/earth_engine"
OUT = BASE / "processed"
OUT.mkdir(parents=True, exist_ok=True)

with (BASE / "locations/commune_coordinates.csv").open(
    encoding="utf-8-sig", newline=""
) as f:
    communes = {r["commune"] for r in csv.DictReader(f)}

variables = ("T2M", "RH2M", "WS10M", "PRECTOTCORR")

def clean(value):
    try:
        value = float(value)
        return value if math.isfinite(value) and value > -900 else None
    except (ValueError, TypeError):
        return None

print("=== LOADING CHIRPS ===", flush=True)

rainfall = {}

for year in range(2001, 2026):
    path = CHIRPS / f"terralert_chirps_v3_sat_{year}.csv"

    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            key = (row["commune"], row["date"])
            if key in rainfall:
                raise ValueError(f"Duplicate CHIRPS key: {key}")
            rainfall[key] = clean(row["precipitation_mm"])

print("CHIRPS records:", len(rainfall), flush=True)

print("\n=== PROCESSING NASA POWER ===", flush=True)

files = sorted(NASA.glob("nasa_power_*.json"))
print("NASA files:", len(files), flush=True)

if len(files) != 275:
    raise ValueError(f"Expected 275 NASA files, found {len(files)}")

records = {}
seen_files = set()

for i, path in enumerate(files, 1):
    with path.open(encoding="utf-8") as f:
        content = json.load(f)

    commune = content["commune"]
    year = int(content["year"])

    if commune not in communes or not 2001 <= year <= 2025:
        raise ValueError(f"Unexpected commune/year in {path.name}")

    if (commune, year) in seen_files:
        raise ValueError(f"Duplicate NASA file for {commune}, {year}")
    seen_files.add((commune, year))

    if content.get("time_standard") != "UTC":
        raise ValueError(f"Unexpected time standard: {path.name}")

    params = content["data"]["properties"]["parameter"]

    if any(name not in params for name in variables):
        raise ValueError(f"Missing NASA variable: {path.name}")

    start = date(year, 1, 1)
    ndays = (date(year + 1, 1, 1) - start).days

    expected_hours = {
        (datetime(year, 1, 1) + timedelta(hours=h)).strftime(
            "%Y%m%d%H"
        )
        for h in range(ndays * 24)
    }

    for name in variables:
        if set(params[name]) != expected_hours:
            raise ValueError(
                f"Incomplete hourly timestamps: {path.name}, {name}"
            )

    daily = defaultdict(lambda: defaultdict(list))

    for name in variables:
        for timestamp, value in params[name].items():
            day = datetime.strptime(timestamp, "%Y%m%d%H").date()
            daily[day][name].append(clean(value))

    for day, values in daily.items():
        key = (commune, day.isoformat())

        def mean_valid(name):
            valid = [v for v in values[name] if v is not None]
            return round(sum(valid) / len(valid), 3) if valid else ""

        def count_valid(name):
            return sum(v is not None for v in values[name])

        temperatures = [
            v for v in values["T2M"] if v is not None
        ]

        nasa_rain = [
            v for v in values["PRECTOTCORR"]
            if v is not None
        ]

        chirps_rain = rainfall.get(key)

        records[key] = {
            "commune": commune,
            "date": day.isoformat(),
            "temperature_mean_c": mean_valid("T2M"),
            "temperature_min_c": (
                round(min(temperatures), 3) if temperatures else ""
            ),
            "temperature_max_c": (
                round(max(temperatures), 3) if temperatures else ""
            ),
            "humidity_mean_pct": mean_valid("RH2M"),
            "wind_mean_ms": mean_valid("WS10M"),
            "wind_mean_kmh": (
                round(float(mean_valid("WS10M")) * 3.6, 3)
                if mean_valid("WS10M") != "" else ""
            ),
            "precipitation_mm": (
                chirps_rain if chirps_rain is not None else ""
            ),
            "nasa_precipitation_mm": (
                round(sum(nasa_rain), 3)
                if len(nasa_rain) == 24 else ""
            ),
            "temp_hours": count_valid("T2M"),
            "humidity_hours": count_valid("RH2M"),
            "wind_hours": count_valid("WS10M"),
            "nasa_rain_hours": count_valid("PRECTOTCORR"),
            "weather_source": "NASA_POWER",
            "rainfall_source": "CHIRPS_v3_DAILY_SAT",
            "time_standard": "UTC",
        }

    if i % 25 == 0:
        print(f"Processed {i}/275 NASA files", flush=True)

expected = 11 * sum(
    (date(y + 1, 1, 1) - date(y, 1, 1)).days
    for y in range(2001, 2026)
)

if len(records) != expected:
    raise ValueError(
        f"Expected {expected} daily records, got {len(records)}"
    )

if len(rainfall) != expected or set(records) != set(rainfall):
    raise ValueError("NASA/CHIRPS commune-date coverage mismatch")

output = OUT / "daily_weather_nasa_chirps_2001_2025.csv"

with output.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f, fieldnames=list(next(iter(records.values())).keys())
    )
    writer.writeheader()
    for key in sorted(records):
        writer.writerow(records[key])

incomplete = sum(
    any(
        record[field] != 24
        for field in ("temp_hours", "humidity_hours", "wind_hours")
    ) or record["precipitation_mm"] == ""
    for record in records.values()
)

print("\n=== STANDARDIZATION RESULTS ===")
print("Expected records:", expected)
print("Actual records:", len(records))
print("Communes:", len(communes))
print("Years: 2001–2025")
print("Incomplete weather days:", incomplete)
print("Output:", output)
print("ERA5 used: NO")

if incomplete:
    print("\nWARNING: Some records have missing weather observations.")
    print("Review quality before modelling.")
else:
    print("\nSUCCESS: Complete standardized daily dataset created!")
