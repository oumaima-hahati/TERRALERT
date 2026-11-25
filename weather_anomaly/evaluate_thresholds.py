"""Compare Isolation Forest anomaly thresholds using historical data."""

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from weather_anomaly.features import (
    FEATURES,
    load_weather,
    prepare_features,
)


def main():
    weather = load_weather()
    _, unique = prepare_features(weather)

    splits = {
        "Training": unique[unique["year"].between(2001, 2020)],
        "Validation": unique[unique["year"].between(2021, 2023)],
        "Testing": unique[unique["year"].between(2024, 2025)],
    }

    X_train = splits["Training"][FEATURES].to_numpy(dtype=float)

    # Fit preprocessing using training observations only.
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)

    model = IsolationForest(
        n_estimators=100,
        max_samples=256,
        contamination="auto",
        random_state=42,
        n_jobs=1,
    )
    model.fit(X_train_scaled)

    scores = {}

    for name, frame in splits.items():
        X = frame[FEATURES].to_numpy(dtype=float)
        scores[name] = model.score_samples(
            scaler.transform(X)
        )

    print("=== THRESHOLD COMPARISON ===")
    print("Lower scores mean more unusual weather.\n")

    print(
        f"{'Threshold':<13}"
        f"{'Training':>12}"
        f"{'Validation':>13}"
        f"{'Testing':>12}"
    )

    for fraction in (0.01, 0.02, 0.05, 0.10):
        threshold = np.quantile(
            scores["Training"], fraction
        )

        rates = [
            100 * np.mean(scores[name] <= threshold)
            for name in ("Training", "Validation", "Testing")
        ]

        print(
            f"{fraction * 100:>5.0f}% train  "
            f"{rates[0]:>10.2f}%"
            f"{rates[1]:>12.2f}%"
            f"{rates[2]:>12.2f}%"
        )

    provisional_threshold = float(
        np.quantile(scores["Training"], 0.05)
    )

    print("\n=== PROVISIONAL 5% THRESHOLD ===")
    print("Score threshold:", round(provisional_threshold, 6))
    print("This is a research candidate, not a hazard warning.")

    print("\n=== TEST PERIOD ===")
    test = splits["Testing"].copy()
    test["anomaly_score"] = scores["Testing"]
    test["is_anomaly"] = (
        test["anomaly_score"] <= provisional_threshold
    )

    print("Flagged records:", int(test["is_anomaly"].sum()))

    print("\n=== TOP 10 MOST UNUSUAL TEST RECORDS ===")
    columns = [
        "commune",
        "date",
        "temperature_max_c",
        "temperature_min_c",
        "precipitation_mm",
        "anomaly_score",
    ]

    print(
        test.nsmallest(10, "anomaly_score")[columns]
        .to_string(index=False)
    )

    print("\nSUCCESS: Threshold evaluation completed")


if __name__ == "__main__":
    main()
