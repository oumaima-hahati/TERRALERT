"""Train and track a TERRALERT Isolation Forest experiment."""

import json
from pathlib import Path

import joblib
import mlflow
import numpy as np

from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from weather_anomaly.versioning import create_manifest, save_manifest, MODEL_VERSION

from weather_anomaly.features import (
    FEATURES,
    load_weather,
    prepare_features,
)


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / ".local"
OUTPUT.mkdir(parents=True, exist_ok=True)

DB = OUTPUT / "mlflow.db"
TRACKING_URI = f"sqlite:///{DB}"


def main():
    print("=== LOAD WEATHER DATA ===")

    weather = load_weather()
    _, unique = prepare_features(weather)

    splits = {
        "train": unique[unique["year"].between(2001, 2020)],
        "validation": unique[unique["year"].between(2021, 2023)],
        "test": unique[unique["year"].between(2024, 2025)],
    }

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

    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment("TERRALERT_Weather_Anomaly")

    print("Tracking backend: SQLite")
    print("Experiment: TERRALERT_Weather_Anomaly")

    with mlflow.start_run(
        run_name="isolation_forest_baseline_v1"
    ) as run:

        mlflow.log_params({
            "algorithm": "IsolationForest",
            "model_version": MODEL_VERSION,
            "n_estimators": 100,
            "max_samples": 256,
            "contamination": "auto",
            "random_state": 42,
            "n_features": len(FEATURES),
            "train_start": 2001,
            "train_end": 2020,
            "validation_start": 2021,
            "validation_end": 2023,
            "test_start": 2024,
            "test_end": 2025,
            "threshold_quantile": 0.05,
        })

        X_train = splits["train"][FEATURES].to_numpy(
            dtype=float
        )

        print("\n=== TRAIN MODEL ===")
        model.fit(X_train)

        print("PASS: Model trained")

        scores = {}

        for name, frame in splits.items():
            X = frame[FEATURES].to_numpy(dtype=float)

            scores[name] = model.score_samples(X)

        threshold = float(
            np.quantile(scores["train"], 0.05)
        )

        print("\n=== LOG EVALUATION METRICS ===")

        mlflow.log_metric("anomaly_threshold", threshold)

        for name, frame in splits.items():
            values = scores[name]

            flags = values <= threshold
            rate = float(flags.mean() * 100)

            mlflow.log_metrics({
                f"{name}_records": len(frame),
                f"{name}_mean_score": float(values.mean()),
                f"{name}_anomaly_count": int(flags.sum()),
                f"{name}_anomaly_pct": rate,
            })

            print(
                f"{name}: {len(frame):,} records, "
                f"{int(flags.sum()):,} anomalies "
                f"({rate:.2f}%)"
            )

        print("\n=== SAVE MODEL ARTIFACT ===")

        model_path = OUTPUT / "isolation_forest.joblib"
        joblib.dump(model, model_path)

        metadata = {
            "model": "IsolationForest",
            "features": FEATURES,
            "training_period": [2001, 2020],
            "validation_period": [2021, 2023],
            "test_period": [2024, 2025],
            "anomaly_threshold": threshold,
            "score_method": "score_samples",
            "interpretation": (
                "Statistical anomaly only; "
                "not an official hazard alert"
            ),
        }

        metadata_path = OUTPUT / "model_metadata.json"

        metadata_path.write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )

        manifest_path = OUTPUT / "model_manifest.json"
        save_manifest(create_manifest(model_path, metadata_path, run_id=run.info.run_id), manifest_path)
        mlflow.set_tag("model_version", MODEL_VERSION)
        mlflow.log_artifact(str(manifest_path), artifact_path="model")

        mlflow.log_artifact(
            str(model_path),
            artifact_path="model"
        )

        mlflow.log_artifact(
            str(metadata_path),
            artifact_path="model"
        )

        print("PASS: Model and metadata saved")

        print("\n=== MLFLOW RUN ===")
        print("Run ID:", run.info.run_id)
        print("Tracking database:", DB)
        print("Anomaly threshold:", round(threshold, 6))

    print("\nSUCCESS: MLflow experiment completed")


if __name__ == "__main__":
    main()
