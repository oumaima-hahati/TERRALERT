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

# Shift yesterday's FWI to today's date.
previous = fwi[["commune", "date", "fwi", "danger_level"]].copy()
previous["date"] += pd.Timedelta(days=1)
previous = previous.rename(columns={"fwi": "previous_fwi"})
previous["high_previous"] = previous["danger_level"].isin(
    ["High", "Very High", "Extreme"]
)

fire_days = (
    fires[fires["comparison_status"] == "matched"]
    [["commune", "fire_date"]]
    .drop_duplicates()
    .rename(columns={"fire_date": "date"})
)

df = previous.merge(
    fire_days.assign(detected=True),
    on=["commune", "date"],
    how="left",
    validate="one_to_one"
)
df["detected"] = df["detected"].fillna(False).astype(bool)
df["year"] = df["date"].dt.year
df["month"] = df["date"].dt.month

controls = (
    df[~df["detected"]]
    .groupby(["commune", "year", "month"])
    .agg(
        control_mean_fwi=("previous_fwi", "mean"),
        control_high_rate=("high_previous", "mean"),
        control_count=("previous_fwi", "size")
    )
    .reset_index()
)

events = df[df["detected"]].merge(
    controls,
    on=["commune", "year", "month"],
    how="left",
    validate="many_to_one"
)

events = events.dropna(subset=["control_mean_fwi"])

print("=== LOCAL SEASONAL FWI COMPARISON ===")
print("Fire commune-days compared:", len(events))
print("Mean previous-day FWI on fire days:",
      round(events["previous_fwi"].mean(), 2))
print("Mean reference FWI:",
      round(events["control_mean_fwi"].mean(), 2))
print("Mean paired FWI difference:",
      round(
          (events["previous_fwi"] -
           events["control_mean_fwi"]).mean(), 2
      ))

print("\nPrevious-day High+ rate on fire days:",
      f"{events['high_previous'].mean() * 100:.2f}%")
print("Same commune/month/year reference:",
      f"{events['control_high_rate'].mean() * 100:.2f}%")

print("\nFire days above their reference mean:",
      int(
          (events["previous_fwi"] >
           events["control_mean_fwi"]).sum()
      ), "/", len(events))

print("\nNOTE: Descriptive retrospective comparison.")
print("Not a prospective accuracy or significance test.")
