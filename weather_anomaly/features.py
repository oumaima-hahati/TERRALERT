"""Feature preparation for TERRALERT weather anomaly detection."""

import numpy as np
import pandas as pd

SOURCE = (
    "data/weather/processed/"
    "daily_weather_nasa_chirps_2001_2025.csv"
)

BASE_VARIABLES = [
    "temperature_max_c",
    "temperature_min_c",
    "humidity_mean_pct",
    "wind_mean_ms",
]

FEATURES = [
    "temperature_max_anomaly",
    "temperature_min_anomaly",
    "humidity_anomaly",
    "wind_anomaly",
    "log_rainfall",
    "log_rainfall_3d",
]


def load_weather(path=SOURCE):
    df = pd.read_csv(path, parse_dates=["date"])

    df = df.sort_values(
        ["commune", "date"]
    ).reset_index(drop=True)

    if df.duplicated(["commune", "date"]).any():
        raise ValueError(
            "Duplicate commune-date records detected"
        )

    return df


def prepare_features(df):
    df = df.copy()

    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month

    # Baselines calculated from the training period only.
    training = df[df["year"].between(2001, 2020)]

    baseline = training.groupby("month")[
        BASE_VARIABLES
    ].mean()

    for variable in BASE_VARIABLES:
        name = variable.replace("_c", "")
        name = name.replace("_mean_pct", "")
        name = name.replace("_mean_ms", "")

        output = {
            "temperature_max_c": "temperature_max_anomaly",
            "temperature_min_c": "temperature_min_anomaly",
            "humidity_mean_pct": "humidity_anomaly",
            "wind_mean_ms": "wind_anomaly",
        }[variable]

        df[output] = (
            df[variable] -
            df["month"].map(baseline[variable])
        )

    # Three-day rainfall, independently for each commune.
    df["rainfall_3d_mm"] = (
        df.groupby("commune")["precipitation_mm"]
        .transform(lambda x: x.rolling(3, min_periods=3).sum())
    )

    df["log_rainfall"] = np.log1p(
        df["precipitation_mm"]
    )

    df["log_rainfall_3d"] = np.log1p(
        df["rainfall_3d_mm"]
    )

    # First two records per commune have no 3-day history.
    df = df.dropna(subset=FEATURES).copy()

    # Remove replicated weather vectors for training.
    unique = df.drop_duplicates(
        subset=["date"] + FEATURES
    ).copy()

    return df, unique


if __name__ == "__main__":
    weather = load_weather()
    all_rows, unique_rows = prepare_features(weather)

    print("=== FEATURE PREPARATION ===")
    print("Input rows:", len(weather))
    print("Feature rows:", len(all_rows))
    print("Distinct observations:", len(unique_rows))

    print("\n=== FEATURES ===")
    print(unique_rows[FEATURES].describe().to_string())

    print("\n=== SPLITS ===")
    for name, start, end in [
        ("Training", 2001, 2020),
        ("Validation", 2021, 2023),
        ("Test", 2024, 2025),
    ]:
        subset = unique_rows[
            unique_rows["year"].between(start, end)
        ]
        print(name, len(subset))
