#!/usr/bin/env python3
"""Retrospective monthly-percentile heatwave detection for TERRALERT."""

import pandas as pd
from pathlib import Path

SOURCE = Path(
    "data/weather/processed/"
    "daily_weather_nasa_chirps_2001_2025.csv"
)
OUT = Path("data/heatwaves/processed")
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(SOURCE, parse_dates=["date"])
df = df.sort_values(["commune", "date"]).copy()

assert len(df) == 100441
assert df["commune"].nunique() == 11
assert not df.duplicated(["commune", "date"]).any()

df["month"] = df["date"].dt.month

# Baseline: 2001–2025, separate for each commune and month.
thresholds = (
    df.groupby(["commune", "month"])["temperature_max_c"]
    .quantile(0.90)
    .reset_index(name="threshold_p90_c")
)

df = df.merge(
    thresholds,
    on=["commune", "month"],
    how="left",
    validate="many_to_one"
)

# Strict exceedance; at least 3 consecutive calendar days.
df["hot_day"] = (
    df["temperature_max_c"] > df["threshold_p90_c"]
)

events = []
daily_records = []

for commune, group in df.groupby("commune", sort=True):
    group = group.sort_values("date").copy()

    # A new group starts when hot/non-hot status changes
    # or a calendar date is missing.
    gap = group["date"].diff().dt.days.ne(1)
    change = group["hot_day"].ne(group["hot_day"].shift())

    group["segment"] = (gap | change).cumsum()
    group["heatwave"] = False
    group["heatwave_id"] = ""

    event_number = 0

    for _, segment in group.groupby("segment"):
        if not segment["hot_day"].all() or len(segment) < 3:
            continue

        event_number += 1
        event_id = (
            f"{commune.replace(' ', '_')}_HW_{event_number:04d}"
        )

        group.loc[segment.index, "heatwave"] = True
        group.loc[segment.index, "heatwave_id"] = event_id

        events.append({
            "heatwave_id": event_id,
            "commune": commune,
            "start_date": segment["date"].min().date().isoformat(),
            "end_date": segment["date"].max().date().isoformat(),
            "duration_days": len(segment),
            "peak_temperature_c": round(
                segment["temperature_max_c"].max(), 2
            ),
            "mean_temperature_c": round(
                segment["temperature_mean_c"].mean(), 2
            ),
            "mean_threshold_c": round(
                segment["threshold_p90_c"].mean(), 2
            ),
        })

    daily_records.append(group.drop(columns="segment"))

daily = pd.concat(daily_records, ignore_index=True)
events_df = pd.DataFrame(events)

thresholds.to_csv(
    OUT / "heatwave_monthly_thresholds_2001_2025.csv",
    index=False
)

daily.to_csv(
    OUT / "heatwave_daily_2001_2025.csv",
    index=False
)

events_df.to_csv(
    OUT / "heatwave_events_2001_2025.csv",
    index=False
)

summary = (
    daily.groupby("commune")
    .agg(
        total_days=("date", "size"),
        heatwave_days=("heatwave", "sum")
    )
    .reset_index()
)

event_counts = (
    events_df.groupby("commune")
    .size()
    .rename("heatwave_events")
    .reset_index()
)

summary = summary.merge(
    event_counts, on="commune", how="left"
)
summary["heatwave_events"] = (
    summary["heatwave_events"].fillna(0).astype(int)
)
summary["heatwave_pct"] = (
    100 * summary["heatwave_days"] / summary["total_days"]
).round(2)

summary.to_csv(
    OUT / "heatwave_commune_summary.csv",
    index=False
)

assert len(daily) == 100441
assert len(thresholds) == 132
assert daily["threshold_p90_c"].notna().all()
assert daily.loc[daily["heatwave"], "heatwave_id"].ne("").all()
assert int(summary["heatwave_days"].sum()) == int(
    events_df["duration_days"].sum()
)

print("=== TERRALERT HISTORICAL HEATWAVES ===")
print("Communes:", daily["commune"].nunique())
print("Daily records:", len(daily))
print("Monthly thresholds:", len(thresholds))
print("Heatwave events:", len(events_df))
print("Total heatwave commune-days:",
      int(summary["heatwave_days"].sum()))

print("\n=== COMMUNE SUMMARY ===")
print(
    summary[
        ["commune", "heatwave_events",
         "heatwave_days", "heatwave_pct"]
    ].to_string(index=False)
)

print("\nOutput:", OUT)
print("Definition: monthly P90 Tmax, >=3 consecutive days")
print("Status: RETROSPECTIVE RESEARCH")
print("\nSUCCESS: Historical heatwave detection completed!")
