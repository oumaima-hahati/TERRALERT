#!/usr/bin/env python3
"""Create historical commune-level FWI statistics."""

import pandas as pd
from pathlib import Path

BASE = Path("data/wildfires/processed")

SOURCE = BASE / "wildfire_fwi_nasa_chirps_2001_2025.csv"
OUTPUT = BASE / "wildfire_fwi_commune_summary_nasa_chirps.csv"

df = pd.read_csv(SOURCE)

# Exclude the first 30 warm-up days per commune.
df = df[df["quality"] == "provisional"].copy()

df["is_high"] = df["danger_level"].isin(
    ["High", "Very High", "Extreme"]
)

df["is_extreme"] = df["danger_level"].eq("Extreme")

summary = (
    df.groupby("commune", as_index=False)
    .agg(
        records=("fwi", "size"),
        mean_fwi=("fwi", "mean"),
        maximum_fwi=("fwi", "max"),
        high_days=("is_high", "sum"),
        extreme_days=("is_extreme", "sum"),
    )
)

summary["high_pct"] = (
    summary["high_days"] / summary["records"] * 100
).round(2)

summary["mean_fwi"] = summary["mean_fwi"].round(3)
summary["maximum_fwi"] = summary["maximum_fwi"].round(3)

if len(summary) != 11:
    raise ValueError("Expected exactly 11 communes")

if summary["records"].sum() != 100111:
    raise ValueError("Unexpected post-warm-up record count")

summary.to_csv(OUTPUT, index=False)

print("=== NASA + CHIRPS WILDFIRE GIS SUMMARY ===")
print(
    summary[
        ["commune", "records", "mean_fwi",
         "high_days", "high_pct"]
    ].to_string(index=False)
)
print("\nSaved:", OUTPUT)
print("SUCCESS: Summary created!")
