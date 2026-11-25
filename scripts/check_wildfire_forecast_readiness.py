#!/usr/bin/env python3
"""Check whether weather forecasts can support daily FWI."""

import pandas as pd
from pathlib import Path

BASE = Path("data/weather/forecasts/open_meteo")

files = sorted(BASE.glob("forecast_*.csv"))

if not files:
    raise SystemExit(
        "ERROR: No forecast CSV found. "
        "Run download_wildfire_forecasts.py first."
    )

path = files[-1]

df = pd.read_csv(path)

df["forecast_time_utc"] = pd.to_datetime(
    df["forecast_time_utc"], utc=True
)

df["retrieved_at_utc"] = pd.to_datetime(
    df["retrieved_at_utc"], utc=True
)

if df.duplicated(["commune", "forecast_time_utc"]).any():
    raise ValueError("Duplicate commune-hour records")

if df["commune"].nunique() != 11:
    raise ValueError("Expected 11 communes")

if df["retrieved_at_utc"].nunique() != 1:
    raise ValueError("Inconsistent retrieval timestamps")

issued = df["retrieved_at_utc"].iloc[0]

df["local_time"] = df[
    "forecast_time_utc"
].dt.tz_convert("Africa/Casablanca")

df["local_date"] = df["local_time"].dt.date
df["local_hour"] = df["local_time"].dt.hour

noon = df[
    (df["local_hour"] == 12)
    & (df["forecast_time_utc"] > issued)
].copy()

noon["previous_24h_complete"] = False

for index, row in noon.iterrows():
    start = row["forecast_time_utc"] - pd.Timedelta(hours=24)
    end = row["forecast_time_utc"]

    history = df[
        (df["commune"] == row["commune"])
        & (df["forecast_time_utc"] > start)
        & (df["forecast_time_utc"] <= end)
    ]

    noon.loc[index, "previous_24h_complete"] = (
        len(history) == 24
        and history["precipitation_mm"].notna().all()
    )

print("=== TERRALERT FORECAST READINESS ===")
print("File:", path.name)
print("Communes:", df["commune"].nunique())
print("Total hourly records:", len(df))
print("Retrieved at UTC:", issued)
print("First forecast UTC:", df["forecast_time_utc"].min())
print("Last forecast UTC:", df["forecast_time_utc"].max())

print("\n=== FUTURE LOCAL-NOON OBSERVATIONS ===")

summary = noon.groupby("local_date").agg(
    communes=("commune", "nunique"),
    complete_rainfall=(
        "previous_24h_complete", "sum"
    )
)

print(summary.to_string())

print("\nFully supported local-noon dates:",
      int((summary["complete_rainfall"] == 11).sum()))

print("\nNOTE:")
print("This checks forecast coverage only.")
print("It does not initialize FWI moisture codes.")
print("Forecast retrieval time is not necessarily model issue time.")
