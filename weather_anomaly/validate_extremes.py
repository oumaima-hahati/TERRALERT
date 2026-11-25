"""Compare weather anomalies with historical extreme-weather indicators."""

import pandas as pd
import numpy as np

from weather_anomaly.features import load_weather

PREDICTIONS = (
    "weather_anomaly/.local/"
    "weather_anomalies_2024_2025.csv"
)


def main():
    weather = load_weather()
    weather["year"] = weather["date"].dt.year
    weather["month"] = weather["date"].dt.month

    train = weather[
        weather["year"].between(2001, 2020)
    ].copy()

    test = pd.read_csv(
        PREDICTIONS,
        parse_dates=["date"],
    )
    test["month"] = test["date"].dt.month

    print("=== HISTORICAL REFERENCE THRESHOLDS ===")
    print("Reference period: 2001–2020")
    print("Evaluation period: 2024–2025")

    # Commune/month temperature thresholds.
    reference = (
        train.groupby(["commune", "month"])
        .agg(
            hot_threshold=("temperature_max_c",
                           lambda s: s.quantile(0.95)),
            cold_threshold=("temperature_min_c",
                            lambda s: s.quantile(0.05)),
        )
        .reset_index()
    )

    # Commune-level rainfall thresholds calculated
    # from days with at least 1 mm of rainfall.
    wet_days = train[train["precipitation_mm"] >= 1]

    rain_reference = (
        wet_days.groupby("commune")["precipitation_mm"]
        .quantile(0.95)
        .rename("heavy_rain_threshold")
        .reset_index()
    )

    test = test.merge(
        reference,
        on=["commune", "month"],
        how="left",
        validate="many_to_one",
    )

    test = test.merge(
        rain_reference,
        on="commune",
        how="left",
        validate="many_to_one",
    )

    assert test[
        ["hot_threshold", "cold_threshold",
         "heavy_rain_threshold"]
    ].notna().all().all()

    test["extreme_heat"] = (
        test["temperature_max_c"] >
        test["hot_threshold"]
    )

    test["extreme_cold"] = (
        test["temperature_min_c"] <
        test["cold_threshold"]
    )

    test["extreme_rain"] = (
        test["precipitation_mm"] >
        test["heavy_rain_threshold"]
    )

    test["any_reference_extreme"] = test[
        ["extreme_heat", "extreme_cold", "extreme_rain"]
    ].any(axis=1)

    flagged = test["is_anomaly"].astype(bool)

    print("\n=== EXTREME-WEATHER COMPARISON ===")
    print(
        f"{'Indicator':<24}"
        f"{'Extreme days':>15}"
        f"{'Flagged':>12}"
        f"{'Detection %':>15}"
    )

    for label, column in [
        ("Unusually hot", "extreme_heat"),
        ("Unusually cold", "extreme_cold"),
        ("Heavy rainfall", "extreme_rain"),
        ("Any reference extreme", "any_reference_extreme"),
    ]:
        extreme = test[column]
        total = int(extreme.sum())
        detected = int((flagged & extreme).sum())

        rate = 100 * detected / total if total else 0

        print(
            f"{label:<24}"
            f"{total:>15}"
            f"{detected:>12}"
            f"{rate:>14.2f}%"
        )

    print("\n=== ANOMALY INTERPRETATION ===")

    matched = flagged & test["any_reference_extreme"]
    unmatched = flagged & ~test["any_reference_extreme"]

    print("Total Isolation Forest flags:", int(flagged.sum()))
    print("Flags matching reference extremes:", int(matched.sum()))
    print("Flags without these extreme indicators:",
          int(unmatched.sum()))

    print("\n=== REFERENCE EXTREMES NOT FLAGGED ===")
    missed = (
        test["any_reference_extreme"] & ~flagged
    )
    print("Count:", int(missed.sum()))

    print("\n=== QUALITY CHECKS ===")
    assert len(test) == 8041
    assert test["commune"].nunique() == 11
    assert np.isfinite(
        test["anomaly_score"].to_numpy()
    ).all()

    print("PASS: All 11 communes included")
    print("PASS: No missing reference thresholds")
    print("PASS: No invalid anomaly scores")
    print("\nSUCCESS: Scientific comparison completed")
    print(
        "Note: Reference extremes are statistical indicators,"
        " not independently verified hazards."
    )


if __name__ == "__main__":
    main()
