#!/usr/bin/env python3
"""Exploratory comparison of FWI danger and FIRMS detection days."""

import csv
from collections import Counter
from pathlib import Path

BASE = Path("data/wildfires/processed")
FWI = BASE / "wildfire_fwi_historical.csv"
FIRMS = BASE / "firms_fwi_comparison.csv"
OUTPUT = BASE / "fwi_detection_evaluation.csv"

HIGH = {"High", "Very High", "Extreme"}

with FWI.open(newline="", encoding="utf-8") as f:
    weather = [
        r for r in csv.DictReader(f)
        if r["quality"] == "provisional"
    ]

with FIRMS.open(newline="", encoding="utf-8") as f:
    fires = [
        r for r in csv.DictReader(f)
        if r["comparison_status"] == "matched"
    ]

fire_days = {
    (r["commune"], r["fire_date"])
    for r in fires
}

weather_keys = {
    (r["commune"], r["date"])
    for r in weather
}

if len(weather_keys) != len(weather):
    raise ValueError("Duplicate weather commune-days")

if not fire_days.issubset(weather_keys):
    raise ValueError("Fire dates missing from FWI dataset")

counts = Counter()
output_rows = []

for row in weather:
    key = (row["commune"], row["date"])
    detected = key in fire_days
    high = row["danger_level"] in HIGH

    if detected and high:
        counts["TP"] += 1
    elif detected and not high:
        counts["FN"] += 1
    elif not detected and high:
        counts["FP"] += 1
    else:
        counts["TN"] += 1

    output_rows.append({
        "commune": row["commune"],
        "date": row["date"],
        "fwi": row["fwi"],
        "danger_level": row["danger_level"],
        "fwi_high_or_above": int(high),
        "firms_vegetation_detection": int(detected),
    })

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f, fieldnames=list(output_rows[0])
    )
    writer.writeheader()
    writer.writerows(output_rows)

tp, fn = counts["TP"], counts["FN"]
fp, tn = counts["FP"], counts["TN"]

def percentage(a, b):
    return round(100 * a / b, 2) if b else None

print("=== EXPLORATORY FWI DETECTION EVALUATION ===")
print("FWI commune-days:", len(weather))
print("Matched FIRMS hotspot detections:", len(fires))
print("Unique commune-days with detection:", len(fire_days))
print()
print("Detected fire-days rated High+:", tp)
print("Detected fire-days rated below High:", fn)
print("No-detection days rated High+:", fp)
print("No-detection days rated below High:", tn)
print()
print("Detection-day sensitivity (%):",
      percentage(tp, tp + fn))
print("High+ rate on no-detection days (%):",
      percentage(fp, fp + tn))
print("High+ rate across all days (%):",
      percentage(tp + fp, len(weather)))
print()
print("Saved:", OUTPUT)
