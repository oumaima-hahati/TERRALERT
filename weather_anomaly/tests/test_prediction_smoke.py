"""Dataset-independent smoke tests for real prediction logic."""
import json
import numpy as np
import pandas as pd
import joblib
import pytest
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from weather_anomaly.features import FEATURES, prepare_features
from weather_anomaly.versioning import create_manifest, save_manifest
import weather_anomaly.predict as prediction_module


def sample_weather():
    dates = pd.date_range("2001-01-01", "2025-12-31", freq="MS")
    records = []
    for ci, commune in enumerate(("TEST_A", "TEST_B")):
        for i, date in enumerate(dates):
            cycle = np.sin(2 * np.pi * date.month / 12)
            records.append({
                "commune": commune, "date": date,
                "temperature_max_c": 26 + 8 * cycle + ci + i * 0.0001,
                "temperature_min_c": 15 + 6 * cycle + ci,
                "humidity_mean_pct": 60 + 5 * cycle + ci,
                "wind_mean_ms": 3 + 0.3 * cycle + ci * 0.2,
                "precipitation_mm": float(i % 9) * 2,
                "weather_source": "TEST", "rainfall_source": "TEST",
            })
    return pd.DataFrame.from_records(records)


@pytest.fixture
def configured_model(tmp_path, monkeypatch):
    weather = sample_weather()
    _, unique = prepare_features(weather)
    train = unique[unique["year"].between(2001, 2020)]
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("isolation_forest", IsolationForest(n_estimators=10, random_state=42)),
    ])
    pipeline.fit(train[FEATURES].to_numpy(float))
    scores = pipeline.score_samples(train[FEATURES].to_numpy(float))
    threshold = float(np.quantile(scores, 0.05))
    path = tmp_path / "isolation_forest.joblib"
    joblib.dump(pipeline, path)
    metadata_path = tmp_path / "model_metadata.json"
    metadata_path.write_text(json.dumps({
        "model": "IsolationForest", "features": FEATURES,
        "anomaly_threshold": threshold, "score_method": "score_samples",
    }))
    save_manifest(create_manifest(path, metadata_path), tmp_path / "model_manifest.json")
    monkeypatch.setattr(prediction_module, "LOCAL", tmp_path)
    monkeypatch.setattr(prediction_module, "MODEL_PATH", path)
    monkeypatch.setattr(prediction_module, "METADATA_PATH", metadata_path)
    monkeypatch.setattr(prediction_module, "load_weather", lambda: weather)
    return tmp_path


def test_prediction_exports_scores_and_flags(configured_model):
    rows = prediction_module.predict(2024, 2025)
    assert not rows.empty
    assert rows["commune"].nunique() == 2
    assert np.isfinite(rows["anomaly_score"]).all()
    assert rows["is_anomaly"].dtype == bool
    assert (rows["result_type"] == "STATISTICAL_ANOMALY_RESEARCH").all()
    assert (configured_model / "weather_anomalies_2024_2025.csv").exists()


def test_prediction_rejects_tampered_model(configured_model):
    (configured_model / "isolation_forest.joblib").write_bytes(b"broken")
    with pytest.raises(ValueError, match="integrity"):
        prediction_module.predict(2024, 2025)
