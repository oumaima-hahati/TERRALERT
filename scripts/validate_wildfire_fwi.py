#!/usr/bin/env python3
"""Initial quality checks for TERRALERT historical FWI results."""

import csv
import math
from collections import defaultdict, Counter
from pathlib import Path

SOURCE = Path("data/wildfires/processed/wildfire_fwi_historical.csv")
OUTPUT = Path("data/wildfires/processed/wildfire_fwi_commune_summary.csv")

with SOURCE.open(encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))

if not rows:
    raise ValueError("FWI dataset is empty")

required = ["ffmc", "dmc", "dc", "isi", "bui", "fwi"]

by_commune = defaultdict(list)
keys = set()
errors = []

for row in rows:
    key = (row["commune"], row["date"])

    if key in keys:
        errors.append(f"Duplicate: {key}")
    keys.add(key)

    for field in required:
        value = float(row[field])

        if not math.isfinite(value):
            errors.append(f"Non-finite {field}: {key}")

        if value < 0:
            errors.append(f"Negative {field}: {key}")

    if not 0 <= float(row["ffmc"]) <= 101:
        errors.append(f"FFMC outside expected range: {key}")

    by_commune[row["commune"]].append(row)

summary = []

for commune, records in sorted(by_commune.items()):
    valid = [
        r for r in records
        if r["quality"] == "provisional"
    ]

    if not valid:
        continue

    values = [float(r["fwi"]) for r in valid]

    summary.append({
        "commune": commune,
        "records": len(valid),
        "mean_fwi": round(sum(values) / len(values), 3),
        "maximum_fwi": round(max(values), 3),
        "high_days": sum(
            r["danger_level"] in ("High", "Very High", "Extreme")
            for r in valid
        ),
        "extreme_days": sum(
            r["danger_level"] == "Extreme"
            for r in valid
        ),
    })

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "commune", "records", "mean_fwi", "maximum_fwi",
        "high_days", "extreme_days"
    ])
    writer.writeheader()
    writer.writerows(summary)

print("=== FWI INITIAL VALIDATION ===")
print("Total records:", len(rows))
print("Communes:", len(by_commune))
print("Duplicate commune-date keys:", len(rows) - len(keys))
print("Quality flags:", dict(Counter(r["quality"] for r in rows)))
print("Validation errors:", len(errors))

for error in errors[:10]:
    print("ERROR:", error)

print("\n=== FWI BY COMMUNE ===")
for row in sorted(summary, key=lambda x: x["mean_fwi"], reverse=True):
    print(
        f'{row["commune"]:20} '
        f'Mean: {row["mean_fwi"]:7.2f} '
        f'Max: {row["maximum_fwi"]:7.2f} '
        f'Extreme days: {row["extreme_days"]}'
    )

print("\n=== 10 HIGHEST FWI OBSERVATIONS ===")

valid_rows = [
    r for r in rows if r["quality"] == "provisional"
]

for row in sorted(
    valid_rows,
    key=lambda r: float(r["fwi"]),
    reverse=True
)[:10]:
    print(
        row["date"],
        row["commune"],
        "FWI:", row["fwi"]
    )

print("\nSaved:", OUTPUT)

if errors:
    raise SystemExit("Validation failed; review errors above")
