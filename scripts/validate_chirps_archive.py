import csv
import math
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

folder = Path("data/weather/chirps_v3/earth_engine")
locations = Path("data/weather/locations/commune_coordinates.csv")

with locations.open(encoding="utf-8-sig", newline="") as f:
    expected_communes = {
        row["commune"] for row in csv.DictReader(f)
    }

total_records = 0
errors = []

print("=== CHIRPS V3 HISTORICAL VALIDATION ===")
print(f"{'Year':<8}{'Records':<12}{'Expected':<12}Status")
print("-" * 45)

for year in range(2000, 2026):
    path = folder / f"terralert_chirps_v3_sat_{year}.csv"

    if not path.exists():
        errors.append(f"{year}: missing file")
        print(f"{year:<8}{'0':<12}{'—':<12}MISSING")
        continue

    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    start = date(year, 1, 1)
    end = date(year + 1, 1, 1)
    days = (end - start).days

    expected_dates = {
        (start + timedelta(days=i)).isoformat()
        for i in range(days)
    }

    expected_count = days * len(expected_communes)

    keys = [(r["commune"], r["date"]) for r in rows]
    dates = {r["date"] for r in rows}
    communes = {r["commune"] for r in rows}
    per_commune = Counter(r["commune"] for r in rows)

    invalid = 0
    for row in rows:
        try:
            value = float(row["precipitation_mm"])
            if not math.isfinite(value) or value < 0:
                invalid += 1
        except (ValueError, TypeError, KeyError):
            invalid += 1

    problems = []

    if len(rows) != expected_count:
        problems.append("wrong row count")
    if len(keys) != len(set(keys)):
        problems.append("duplicates")
    if dates != expected_dates:
        problems.append("missing/extra dates")
    if communes != expected_communes:
        problems.append("commune mismatch")
    if any(
        per_commune[c] != days for c in expected_communes
    ):
        problems.append("incomplete commune coverage")
    if invalid:
        problems.append(f"{invalid} invalid rainfall values")

    total_records += len(rows)

    if problems:
        errors.append(f"{year}: {', '.join(problems)}")
        status = "FAILED"
    else:
        status = "OK"

    print(f"{year:<8}{len(rows):<12}{expected_count:<12}{status}")

print("-" * 45)
print("Communes expected:", len(expected_communes))
print("Total records:", total_records)
print("Years validated:", 26 - len(errors), "/ 26")

if errors:
    print("\nVALIDATION ERRORS:")
    for error in errors:
        print("-", error)
    raise SystemExit(1)

print("\nSUCCESS: Complete CHIRPS archive validated!")
