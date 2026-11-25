import pandas as pd
from pathlib import Path

BASE = Path("data/weather/processed")
INPUT = BASE / "daily_weather_nasa_chirps_2001_2025.csv"

df = pd.read_csv(INPUT, parse_dates=["date"])

df["year"] = df["date"].dt.year
df["month"] = df["date"].dt.month

seasons = {
    12: "DJF", 1: "DJF", 2: "DJF",
    3: "MAM", 4: "MAM", 5: "MAM",
    6: "JJA", 7: "JJA", 8: "JJA",
    9: "SON", 10: "SON", 11: "SON",
}

df["season"] = df["month"].map(seasons)

# December belongs to the following DJF season.
df["season_year"] = df["year"]
df.loc[df["month"] == 12, "season_year"] += 1

# Monthly aggregates for each year and commune.
monthly = df.groupby(
    ["commune", "year", "month"], as_index=False
).agg(
    temperature_mean_c=("temperature_mean_c", "mean"),
    temperature_min_c=("temperature_min_c", "min"),
    temperature_max_c=("temperature_max_c", "max"),
    humidity_mean_pct=("humidity_mean_pct", "mean"),
    wind_mean_kmh=("wind_mean_kmh", "mean"),
    precipitation_total_mm=("precipitation_mm", "sum"),
    days=("date", "count"),
)

monthly.to_csv(
    BASE / "weather_monthly_nasa_chirps_2001_2025.csv",
    index=False,
)

# Monthly 25-year climatology.
monthly_climatology = monthly.groupby(
    ["commune", "month"], as_index=False
).agg(
    temperature_mean_c=("temperature_mean_c", "mean"),
    humidity_mean_pct=("humidity_mean_pct", "mean"),
    wind_mean_kmh=("wind_mean_kmh", "mean"),
    precipitation_mean_monthly_mm=("precipitation_total_mm", "mean"),
    years=("year", "nunique"),
)

monthly_climatology.to_csv(
    BASE / "weather_monthly_climatology_2001_2025.csv",
    index=False,
)

# Seasonal aggregates by year.
seasonal = df.groupby(
    ["commune", "season_year", "season"], as_index=False
).agg(
    temperature_mean_c=("temperature_mean_c", "mean"),
    humidity_mean_pct=("humidity_mean_pct", "mean"),
    wind_mean_kmh=("wind_mean_kmh", "mean"),
    precipitation_total_mm=("precipitation_mm", "sum"),
    days=("date", "count"),
)

# Exclude incomplete boundary winters:
# DJF 2001 lacks December 2000.
# DJF 2026 lacks January and February 2026.
seasonal = seasonal[
    ~(
        (seasonal["season"] == "DJF")
        & (seasonal["season_year"].isin([2001, 2026]))
    )
].copy()

seasonal.to_csv(
    BASE / "weather_seasonal_nasa_chirps_2001_2025.csv",
    index=False,
)

# Long-term seasonal climatology.
seasonal_climatology = seasonal.groupby(
    ["commune", "season"], as_index=False
).agg(
    temperature_mean_c=("temperature_mean_c", "mean"),
    humidity_mean_pct=("humidity_mean_pct", "mean"),
    wind_mean_kmh=("wind_mean_kmh", "mean"),
    precipitation_mean_seasonal_mm=("precipitation_total_mm", "mean"),
    seasons=("season_year", "nunique"),
)

seasonal_climatology.to_csv(
    BASE / "weather_seasonal_climatology_2001_2025.csv",
    index=False,
)

print("=== WEATHER CLIMATOLOGY RESULTS ===")
print("Daily records:", len(df))
print("Monthly records:", len(monthly))
print("Monthly climatology records:", len(monthly_climatology))
print("Seasonal records:", len(seasonal))
print("Seasonal climatology records:", len(seasonal_climatology))
print("\nSeasonal coverage:")
print(seasonal_climatology.groupby("season")["seasons"].first())
print("\nSUCCESS: Weather climatologies created!")
