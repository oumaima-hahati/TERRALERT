#!/usr/bin/env python3
"""Historical FIRMS association and previous-day FWI evaluation."""

import pandas as pd
from pathlib import Path

BASE = Path("data/wildfires/processed")

fwi = pd.read_csv(
    BASE / "wildfire_fwi_nasa_chirps_2001_2025.csv",
    parse_dates=["date"]
)

fires = pd.read_csv(
    BASE / "firms_fwi_comparison_nasa_chirps.csv",
    parse_dates=["fire_date"]
)

# Only use valid FWI records after initial warm-up.
fwi = fwi[fwi["quality"] == "provisional"].copy()

fwi["high_or_above"] = fwi["danger_level"].isin(
    ["High", "Very High", "Extreme"]
)

# Count unique commune-days, not repeated hotspots.
matched = fires[
    fires["comparison_status"] == "matched"
].copy()

fire_days = matched[
    ["commune", "fire_date"]
].drop_duplicates()

fire_days = fire_days.rename(
    columns={"fire_date": "date"}
)

fwi["detected_fire_day"] = (
    pd.MultiIndex.from_frame(fwi[["commune", "date"]])
    .isin(pd.MultiIndex.from_frame(fire_days))
)

same_day = fwi[fwi["detected_fire_day"]]
no_detection = fwi[~fwi["detected_fire_day"]]

# For each detected fire day, find the previous day's FWI.
previous = fire_days.copy()
previous["date"] -= pd.Timedelta(days=1)

previous = previous.merge(
    fwi[["commune", "date", "fwi", "danger_level", "high_or_above"]],
    on=["commune", "date"],
    how="left",
    validate="one_to_one",
)

valid_previous = previous.dropna(subset=["fwi"])

def percentage(n, total):
    return round(100 * n / total, 2) if total else 0

same_high = int(same_day["high_or_above"].sum())
previous_high = int(valid_previous["high_or_above"].sum())
no_detection_high = int(no_detection["high_or_above"].sum())

print("=== TERRALERT WILDFIRE EVALUATION ===")

print("\n1. FIRMS EVENT COVERAGE")
print("Matched hotspots:", len(matched))
print("Unique detected commune-days:", len(fire_days))

print("\n2. SAME-DAY ASSOCIATION")
print("Detected days with valid FWI:", len(same_day))
print("High+ detected days:", same_high)
print("High+ rate:", percentage(same_high, len(same_day)), "%")

print("\n3. PREVIOUS-DAY WARNING")
print("Detected days with previous-day FWI:", len(valid_previous))
print("Previous-day High+:", previous_high)
print(
    "Previous-day High+ rate:",
    percentage(previous_high, len(valid_previous)), "%"
)

print("\n4. DAYS WITHOUT FIRMS DETECTIONS")
print("No-detection commune-days:", len(no_detection))
print("High+ no-detection days:", no_detection_high)
print(
    "High+ no-detection rate:",
    percentage(no_detection_high, len(no_detection)), "%"
)

print("\n5. BASELINE")
print(
    "Overall High+ frequency:",
    percentage(
        int(fwi["high_or_above"].sum()), len(fwi)
    ), "%"
)

print("\nNOTE:")
print("No FIRMS detection does not prove absence of fire.")
print("Results are retrospective associations, not forecast skill.")
