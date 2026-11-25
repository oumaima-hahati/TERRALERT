"""Train the initial TERRALERT weather Isolation Forest model."""

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from weather_anomaly.features import (
    FEATURES,
    load_weather,
    prepare_features,
)


def main():
    weather = load_weather()
    _, unique = prepare_features(weather)

    train = unique[unique["year"].between(2001, 2020)]
    validation = unique[unique["year"].between(2021, 2023)]
    test = unique[unique["year"].between(2024, 2025)]

    print("=== DATASET SPLITS ===")
    print("Training:", len(train))
    print("Validation:", len(validation))
    print("Testing:", len(test))

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("isolation_forest", IsolationForest(
            n_estimators=100,
            max_samples=256,
            contamination="auto",
            random_state=42,
            n_jobs=1,
        )),
    ])

    print("\n=== TRAINING ===")

    X_train = train[FEATURES].to_numpy(dtype=float)
    model.fit(X_train)

    print("PASS: Isolation Forest trained successfully")

    print("\n=== ANOMALY SCORE DISTRIBUTION ===")

    for name, frame in [
        ("Training", train),
        ("Validation", validation),
        ("Testing", test),
    ]:
        X = frame[FEATURES].to_numpy(dtype=float)

        # Lower scores indicate more unusual observations.
        scores = model.decision_function(X)
        predictions = model.predict(X)

        flagged = int((predictions == -1).sum())
        percentage = flagged / len(frame) * 100

        print(f"\n{name}")
        print("Records:", len(frame))
        print("Mean anomaly score:", round(float(scores.mean()), 4))
        print("Minimum score:", round(float(scores.min()), 4))
        print("Maximum score:", round(float(scores.max()), 4))
        print("Flagged observations:", flagged)
        print("Flagged percentage:", round(percentage, 2), "%")

        assert np.isfinite(scores).all()

    print("\n=== MOST UNUSUAL TEST OBSERVATIONS ===")

    X_test = test[FEATURES].to_numpy(dtype=float)
    scores = model.decision_function(X_test)

    results = test[
        ["commune", "date", "precipitation_mm",
         "temperature_max_c", "temperature_min_c"]
    ].copy()

    results["anomaly_score"] = scores

    print(
        results.nsmallest(10, "anomaly_score")
        .to_string(index=False)
    )

    print("\nSUCCESS: Initial model experiment completed")
    print("No model artifact or CSV output saved yet.")


if __name__ == "__main__":
    main()
