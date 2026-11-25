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

fwi = fwi[fwi["quality"] == "provisional"].copy()

# Previous-day FWI as a predictor for the following day.
previous = fwi[[
    "commune", "date", "fwi", "danger_level"
]].copy()

previous["date"] += pd.Timedelta(days=1)

previous["high_previous"] = previous["danger_level"].isin(
    ["High", "Very High", "Extreme"]
)

fire_days = fires[
    fires["comparison_status"] == "matched"
][["commune", "fire_date"]].drop_duplicates()

fire_days = fire_days.rename(
    columns={"fire_date": "date"}
)

df = previous.merge(
    fire_days.assign(detected=True),
    on=["commune", "date"],
    how="left",
    validate="one_to_one"
)

df["detected"] = df["detected"].fillna(False).astype(bool)
df["month"] = df["date"].dt.month

events = df[df["detected"]].copy()

# Reference: no-detection days in the same commune and month.
controls = df[~df["detected"]].groupby(
    ["commune", "month"]
)["high_previous"].agg(["mean", "count"]).reset_index()

events = events.merge(
    controls,
    on=["commune", "month"],
    how="left",
    validate="many_to_one"
)

events = events.dropna(subset=["mean"])

if events.empty:
    raise SystemExit("No matched fire days with controls.")

observed = events["high_previous"].mean()
expected = events["mean"].mean()

print("=== SEASONALLY MATCHED FWI EVALUATION ===")
print("Matched unique fire days:", len(events))
print("Previous-day High+ on fire days:",
      f"{observed * 100:.2f}%")
print("Expected High+ from same commune/month:",
      f"{expected * 100:.2f}%")
print("Difference:",
      f"{(observed - expected) * 100:+.2f} percentage points")

if expected > 0:
    print("Relative enrichment:",
          f"{observed / expected:.2f}x")

print("\n=== FIRE DAYS BY MONTH ===")
print(
    events.groupby("month")
    .agg(
        fire_days=("detected", "size"),
        previous_high_rate=("high_previous", "mean"),
        reference_high_rate=("mean", "mean")
    )
    .round(3)
    .to_string()
)

print("\nNOTE:")
print("Seasonal matching controls for commune and month,")
print("but not year-specific conditions, fire clustering,")
print("satellite detection bias or forecast uncertainty.")
