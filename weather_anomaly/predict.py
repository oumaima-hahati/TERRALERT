"""Generate commune-level historical weather anomaly results."""

import argparse
import json
from pathlib import Path

import joblib
import numpy as np

from weather_anomaly.features import (
    FEATURES,
    load_weather,
    prepare_features,
)


ROOT = Path(__file__).resolve().parent
LOCAL = ROOT / ".local"

MODEL_PATH = LOCAL / "isolation_forest.joblib"
METADATA_PATH = LOCAL / "model_metadata.json"

OUTPUT_COLUMNS = [
    "commune",
    "date",
    "temperature_max_c",
    "temperature_min_c",
    "humidity_mean_pct",
    "wind_mean_ms",
    "precipitation_mm",
    "rainfall_3d_mm",
    "anomaly_score",
    "is_anomaly",
    "result_type",
    "weather_source",
    "rainfall_source",
]


def predict(start_year=2024, end_year=2025):
    if start_year > end_year:
        raise ValueError("Start year must not exceed end year")

    metadata = json.loads(
        METADATA_PATH.read_text(encoding="utf-8")
    )

    if metadata["features"] != FEATURES:
        raise ValueError("Model feature configuration mismatch")

    model = joblib.load(MODEL_PATH)
    threshold = float(metadata["anomaly_threshold"])

    weather = load_weather()
    prepared, _ = prepare_features(weather)

    # Score every commune-day, not only deduplicated observations.
    selected = prepared[
        prepared["year"].between(start_year, end_year)
    ].copy()

    if selected.empty:
        raise ValueError("No observations in selected period")

    X = selected[FEATURES].to_numpy(dtype=float)
    scores = model.score_samples(X)

    if not np.isfinite(scores).all():
        raise ValueError("Non-finite anomaly scores detected")

    selected["anomaly_score"] = scores
    selected["is_anomaly"] = scores <= threshold
    selected["result_type"] = "STATISTICAL_ANOMALY_RESEARCH"

    results = selected[OUTPUT_COLUMNS].sort_values(
        ["date", "commune"]
    )

    if results.duplicated(["commune", "date"]).any():
        raise ValueError("Duplicate output records")

    LOCAL.mkdir(parents=True, exist_ok=True)

    output = LOCAL / (
        f"weather_anomalies_{start_year}_{end_year}.csv"
    )

    results.to_csv(output, index=False)

    print("=== COMMUNE-LEVEL PREDICTIONS ===")
    print("Period:", start_year, "-", end_year)
    print("Communes:", results["commune"].nunique())
    print("Observations:", len(results))
    print("Flagged anomalies:", int(results["is_anomaly"].sum()))
    print(
        "Anomaly percentage:",
        round(results["is_anomaly"].mean() * 100, 2),
    )
    print("Threshold:", round(threshold, 6))
    print("Output:", output)

    print("\n=== ANOMALIES BY COMMUNE ===")
    summary = results.groupby("commune")["is_anomaly"].agg(
        ["sum", "count"]
    )
    summary["percentage"] = (
        summary["sum"] / summary["count"] * 100
    ).round(2)

    print(summary.to_string())

    print("\n=== TOP 10 MOST UNUSUAL OBSERVATIONS ===")
    print(
        results.nsmallest(10, "anomaly_score")[
            [
                "commune",
                "date",
                "precipitation_mm",
                "temperature_max_c",
                "anomaly_score",
            ]
        ].to_string(index=False)
    )

    print("\nSUCCESS: Commune-level results generated")
    print("Note: These are not verified weather hazards.")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, default=2024)
    parser.add_argument("--end-year", type=int, default=2025)
    args = parser.parse_args()

    predict(args.start_year, args.end_year)
