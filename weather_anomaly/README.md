# TERRALERT — AI Weather Anomaly Detection

## Overview

Research-oriented weather anomaly detection using
Isolation Forest and MLflow.

Study area: 11 communes in Tanger-Assilah, Morocco.

Data sources:
- NASA POWER: temperature, humidity and wind.
- CHIRPS v3: daily precipitation.

Historical period: 2001–2025.

The model identifies statistically unusual weather
observations. An anomaly is not necessarily a hazard.

## Architecture

Historical weather CSV
    |
    v
Feature engineering
    |
    v
Chronological train / validation / test split
    |
    v
Isolation Forest + StandardScaler
    |
    v
Training-derived anomaly threshold
    |
    v
MLflow experiment tracking
    |
    v
Saved model + commune-level anomaly CSV

## Requirements

Python packages:
- numpy
- pandas
- scikit-learn
- mlflow-skinny
- SQLAlchemy
- Alembic
- joblib

The project uses an isolated Python environment.

## Input dataset

Expected local file:

data/weather/processed/
daily_weather_nasa_chirps_2001_2025.csv

The source dataset is not included in this
GitHub contribution.

Required columns include:
- commune
- date
- temperature_max_c
- temperature_min_c
- humidity_mean_pct
- wind_mean_ms
- precipitation_mm

## Train and track with MLflow

From the repository root:

    python -m weather_anomaly.track_experiment

This:
1. Loads and validates historical observations.
2. Calculates seasonal weather features.
3. Trains Isolation Forest on 2001–2020 data.
4. Evaluates 2021–2023 and 2024–2025.
5. Calibrates a provisional 5% anomaly threshold.
6. Logs parameters and metrics in MLflow.
7. Saves the model and metadata locally.

## Generate predictions

    python -m weather_anomaly.predict

Optional year selection:

    python -m weather_anomaly.predict \
      --start-year 2024 --end-year 2025

Outputs are generated in:

    weather_anomaly/.local/

## Scientific validation

    python -m weather_anomaly.validate_extremes

This compares anomaly flags with historical
temperature and rainfall reference thresholds.

The validation report is available in:

    weather_anomaly/VALIDATION_REPORT.md

## Automated tests

    python -m unittest discover \
      -s weather_anomaly/tests \
      -p 'test_*.py' -v

The nine current tests require:
- The historical weather CSV.
- A previously trained model.
- Local model metadata.

They do not yet run independently in CI.

## Local artifacts

Excluded from Git:

- MLflow tracking database.
- Trained model files.
- Generated anomaly CSVs.
- Local metadata and experiment artifacts.

Do not commit generated datasets or
local environment files accidentally.

## Scientific limitations

- Statistical anomalies are not confirmed hazards.
- There are only three unique NASA POWER weather
  histories for the 11 communes.
- Model performance is not validated against
  an independent labeled anomaly benchmark.
- The model has stronger overlap with heavy
  rainfall than with temperature extremes.
- The anomaly threshold is provisional.
- No operational alerts are issued.
- No production deployment is implemented.

## Integration

The output CSV includes commune, date, weather
measurements, anomaly scores and anomaly flags.

This can later be connected to TERRALERT maps,
PostGIS or APIs.

Integration must be coordinated with the
responsible backend and frontend developers.

## Project status

The Isolation Forest and MLflow prototype is
implemented and locally tested.

Production integration and independently verified
hazard evaluation are outside this prototype's
current scope.
