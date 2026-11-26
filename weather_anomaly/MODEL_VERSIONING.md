# AI Model Versioning & Automated Prediction Tests

## Purpose

This task adds an explicit `model_version`, an SHA-256 artifact manifest,
MLflow run linkage, and dataset-independent prediction tests to the existing
Isolation Forest prototype. It does **not** claim production model registry,
scientific validation, operational alerts, or endpoint integration.

## Dependencies and ownership

The planning sheet assigns this task to **Kawtar**, with the prerequisite
"AI Weather Anomaly Detection" owned by **Oumaima**. Coordinate any change
of assignee and code ownership with Kawtar before submitting.

## Commands (from repo root)

```bash
python -m pip install pytest numpy pandas scikit-learn joblib
python -m pytest weather_anomaly/tests/test_versioning.py weather_anomaly/tests/test_prediction_smoke.py -v
```

These 7 tests use temporary data and do not need the private historical CSV.
To run *all* existing tests, provide the original 2001-2025 historical CSV and
train the actual model first (see weather_anomaly/README.md).

```bash
python -m weather_anomaly.track_experiment
python -m weather_anomaly.versioning --manifest weather_anomaly/.local/model_manifest.json
python -m weather_anomaly.predict --start-year 2024 --end-year 2025
python -m pytest weather_anomaly/tests -v
```

`track_experiment` needs MLflow and the full input CSV; see the module README.
Newly created model manifests are checked at prediction time. Legacy models
without manifests remain usable for backward compatibility, but are not
integrity-verified. Keep all `.local` artifacts out of Git.

## Version increment rules

Increment `MODEL_VERSION` in `versioning.py` when releasing a different trained
model. Retain MLflow run ID, features, score method, threshold, data period and
artifact hash to distinguish versions. The Git commit SHA is the code version;
the version in the manifest identifies the model artifact. No single test can
prove that a new model is scientifically accurate.

## Definition of Done

- [ ] New independent tests pass on a clean environment.
- [ ] Existing 9 dataset-dependent tests pass on the project owner's machine.
- [ ] Real model training writes a verifiable manifest, linked to an MLflow run.
- [ ] `git diff` contains only intended files; no data or `.local` artifacts.
- [ ] Kawtar and Oumaima agree on ownership / review.
- [ ] Feature branch pushed and PR merged after review.
- [ ] Only then mark this task Completed in the shared tracker.
