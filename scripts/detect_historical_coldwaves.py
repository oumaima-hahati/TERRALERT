#!/usr/bin/env python3
"""Historical cold-wave detection — TERRALERT research baseline."""

from pathlib import Path
import pandas as pd

SOURCE = Path(
    "data/weather/processed/"
    "daily_weather_nasa_chirps_2001_2025.csv"
)

OUT = Path("data/coldwaves/processed")
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(SOURCE, parse_dates=["date"])

required = {"commune", "date", "temperature_min_c"}
if not required.issubset(df.columns):
    raise ValueError(f"Missing columns: {required - set(df.columns)}")

if df[list(required)].isna().any().any():
    raise ValueError("Missing required values")

if df.duplicated(["commune", "date"]).any():
    raise ValueError("Duplicate commune-date records")

if df["commune"].nunique() != 11:
    raise ValueError("Expected 11 study areas")

df = df.sort_values(["commune", "date"]).copy()
df["month"] = df["date"].dt.month

thresholds = (
    df.groupby(["commune", "month"])["temperature_min_c"]
    .quantile(0.10)
    .reset_index(name="threshold_p10_c")
)

df = df.merge(
    thresholds,
    on=["commune", "month"],
    how="left",
    validate="many_to_one"
)

df["cold_day"] = (
    df["temperature_min_c"] < df["threshold_p10_c"]
)

events = []
daily_records = []

for commune, group in df.groupby("commune", sort=True):
    group = group.sort_values("date").copy()

    date_gap = group["date"].diff().dt.days.ne(1)
    status_change = group["cold_day"].ne(
        group["cold_day"].shift()
    )

    group["segment"] = (date_gap | status_change).cumsum()
    group["coldwave"] = False
    group["coldwave_id"] = ""

    event_number = 0

    for _, segment in group.groupby("segment"):
        if not segment["cold_day"].all():
            continue

        if len(segment) < 3:
            continue

        event_number += 1

        event_id = (
            f"{commune.replace(' ', '_')}_"
            f"CW_{event_number:04d}"
        )

        group.loc[segment.index, "coldwave"] = True
        group.loc[segment.index, "coldwave_id"] = event_id

        events.append({
            "coldwave_id": event_id,
            "commune": commune,
            "start_date": segment["date"].min().date().isoformat(),
            "end_date": segment["date"].max().date().isoformat(),
            "duration_days": len(segment),
            "minimum_temperature_c": round(
                segment["temperature_min_c"].min(), 2
            ),
            "mean_temperature_c": round(
                segment["temperature_min_c"].mean(), 2
            ),
            "mean_threshold_c": round(
                segment["threshold_p10_c"].mean(), 2
            ),
            "maximum_deficit_c": round(
                (
                    segment["threshold_p10_c"]
                    - segment["temperature_min_c"]
                ).max(), 2
            ),
        })

    daily_records.append(
        group.drop(columns=["segment"])
    )

daily = pd.concat(daily_records, ignore_index=True)

events_df = pd.DataFrame(
    events,
    columns=[
        "coldwave_id",
        "commune",
        "start_date",
        "end_date",
        "duration_days",
        "minimum_temperature_c",
        "mean_temperature_c",
        "mean_threshold_c",
        "maximum_deficit_c",
    ]
)

summary = (
    daily.groupby("commune", as_index=False)
    .agg(
        total_days=("date", "size"),
        coldwave_days=("coldwave", "sum"),
    )
)

counts = (
    events_df.groupby("commune")
    .size()
    .rename("coldwave_events")
    .reset_index()
)

summary = summary.merge(
    counts,
    on="commune",
    how="left",
    validate="one_to_one"
)

summary["coldwave_events"] = (
    summary["coldwave_events"].fillna(0).astype(int)
)

summary["coldwave_pct"] = (
    summary["coldwave_days"]
    / summary["total_days"] * 100
).round(2)

if len(daily) != len(df):
    raise ValueError("Daily records were lost")

if len(thresholds) != 132:
    raise ValueError("Expected 132 monthly thresholds")

if daily["threshold_p10_c"].isna().any():
    raise ValueError("Missing thresholds")

if int(summary["coldwave_days"].sum()) != int(
    events_df["duration_days"].sum()
):
    raise ValueError("Cold-wave day totals do not match")

thresholds.to_csv(
    OUT / "coldwave_monthly_thresholds_2001_2025.csv",
    index=False
)

daily.to_csv(
    OUT / "coldwave_daily_2001_2025.csv",
    index=False
)

events_df.to_csv(
    OUT / "coldwave_events_2001_2025.csv",
    index=False
)

summary.to_csv(
    OUT / "coldwave_commune_summary.csv",
    index=False
)

print("=== TERRALERT HISTORICAL COLD WAVES ===")
print("Communes:", daily["commune"].nunique())
print("Daily records:", len(daily))
print("Monthly thresholds:", len(thresholds))
print("Cold-wave events:", len(events_df))
print(
    "Total cold-wave commune-days:",
    int(summary["coldwave_days"].sum())
)

if not events_df.empty:
    print(
        "Longest episode:",
        int(events_df["duration_days"].max()),
        "days"
    )
    print(
        "Minimum temperature:",
        events_df["minimum_temperature_c"].min(),
        "°C"
    )

print("\n=== COMMUNE SUMMARY ===")
print(
    summary[
        ["commune", "coldwave_events",
         "coldwave_days", "coldwave_pct"]
    ].to_string(index=False)
)

print("\nOutput:", OUT)
print("Definition: monthly P10 Tmin, >=3 consecutive days")
print("Status: RETROSPECTIVE RESEARCH")
print("\nSUCCESS: Cold-wave detection completed!")
