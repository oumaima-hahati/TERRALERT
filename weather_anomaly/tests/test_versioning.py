"""Independent model versioning tests: no external dataset or MLflow needed."""
import json
import pytest
from weather_anomaly.versioning import create_manifest, save_manifest, verify_manifest


def artifacts(tmp_path):
    model = tmp_path / "isolation_forest.joblib"
    model.write_bytes(b"test-model-content")
    meta = tmp_path / "model_metadata.json"
    meta.write_text(json.dumps({
        "model": "IsolationForest", "features": ["a", "b"],
        "anomaly_threshold": -0.42, "score_method": "score_samples",
        "training_period": [2001, 2020],
    }), encoding="utf-8")
    manifest = tmp_path / "model_manifest.json"
    save_manifest(create_manifest(model, meta, run_id="fixture-run"), manifest)
    return model, meta, manifest


def test_version_manifest_valid(tmp_path):
    _, _, manifest = artifacts(tmp_path)
    actual = verify_manifest(manifest)
    assert actual["model_version"] == "1.0.0"
    assert actual["mlflow_run_id"] == "fixture-run"


def test_detects_modified_model(tmp_path):
    model, _, manifest = artifacts(tmp_path)
    model.write_bytes(b"altered-model")
    with pytest.raises(ValueError, match="integrity"):
        verify_manifest(manifest)


def test_detects_modified_metadata(tmp_path):
    _, meta, manifest = artifacts(tmp_path)
    meta.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="integrity"):
        verify_manifest(manifest)


def test_missing_artifact(tmp_path):
    model, _, manifest = artifacts(tmp_path)
    model.unlink()
    with pytest.raises(FileNotFoundError, match="Missing model artifact"):
        verify_manifest(manifest)


def test_rejects_unsupported_schema(tmp_path):
    _, _, manifest = artifacts(tmp_path)
    data = json.loads(manifest.read_text())
    data["schema_version"] = 999
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="schema"):
        verify_manifest(manifest)
