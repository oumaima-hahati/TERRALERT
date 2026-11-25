#!/usr/bin/env python3
"""Evaluate previous-day FWI against next-day FIRMS detections."""

import csv
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

BASE = Path("data/wildfires/processed")
FWI = BASE / "wildfire_fwi_historical.csv"
FIRMS = BASE / "firms_fwi_comparison.csv"
OUTPUT = BASE / "fwi_previous_day_evaluation.csv"

HIGH = {"High", "Very High", "Extreme"}

with FWI.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

lookup = {}
for row in rows:
    key = (row["commune"], row["date"])
    if key in lookup:
        raise ValueError(f"Duplicate FWI key: {key}")
    lookup[key] = row

with FIRMS.open(newline="", encoding="utf-8") as f:
    fire_rows = list(csv.DictReader(f))

fire_days = {
    (r["commune"], r["fire_date"])
    for r in fire_rows
    if r["comparison_status"] == "matched"
}

counts = Counter()
results = []

for (commune, day), current in sorted(lookup.items()):
    if current["quality"] != "provisional":
        continue

    previous_day = (
        date.fromisoformat(day) - timedelta(days=1)
    ).isoformat()

    previous = lookup.get((commune, previous_day))

    # Exclude missing days and warm-up values.
    if previous is None or previous["quality"] != "provisional":
        continue

    detected = (commune, day) in fire_days
    high = previous["danger_level"] in HIGH

    if detected and high:
        counts["TP"] += 1
    elif detected:
        counts["FN"] += 1
    elif high:
        counts["FP"] += 1
    else:
        counts["TN"] += 1

    results.append({
        "commune": commune,
        "target_date": day,
        "fwi_date": previous_day,
        "previous_day_fwi": previous["fwi"],
        "previous_day_danger": previous["danger_level"],
        "high_or_above": int(high),
        "firms_detection_next_day": int(detected),
    })

if not results:
    raise ValueError("No valid consecutive-day pairs found")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0]))
    writer.writeheader()
    writer.writerows(results)

tp = counts["TP"]
fn = counts["FN"]
fp = counts["FP"]
tn = counts["TN"]

def pct(a, b):
    return round(100 * a / b, 2) if b else None

print("=== PREVIOUS-DAY FWI EVALUATION ===")
print("Evaluated commune-days:", len(results))
print("FIRMS detection days:", tp + fn)
print()
print("Fire-days preceded by High+ FWI:", tp)
print("Fire-days preceded by below-High FWI:", fn)
print("No-detection days preceded by High+ FWI:", fp)
print("No-detection days preceded by below-High FWI:", tn)
print()
print("Detection-day sensitivity (%):", pct(tp, tp + fn))
print("High+ rate on no-detection days (%):", pct(fp, fp + tn))
print()
print("Saved:", OUTPUT)
