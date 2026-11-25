# TERRALERT — Weather Anomaly Detection Validation

## 1. Objective

Develop and evaluate an Isolation Forest model for
detecting statistically unusual weather observations
in the TERRALERT study area.

The model is intended for research and exploratory
monitoring. It does not issue official hazard warnings.

## 2. Data

Sources:
- NASA POWER: temperature, humidity and wind.
- CHIRPS v3: daily precipitation estimates.

Coverage:
- 2001–2025.
- 11 communes.
- 100,441 daily commune observations.
- Three distinct NASA POWER weather histories.

Spatially repeated observations were handled during
model training. Predictions are generated separately
for all 11 communes.

## 3. Feature engineering

Six model features:
1. Maximum temperature anomaly.
2. Minimum temperature anomaly.
3. Humidity anomaly.
4. Wind-speed anomaly.
5. Log-transformed daily rainfall.
6. Log-transformed three-day rainfall.

Monthly reference averages were calculated using
2001–2020 observations only.

## 4. Training configuration

Algorithm: Isolation Forest.

Parameters:
- n_estimators: 100
- max_samples: 256
- contamination: auto
- random_state: 42
- n_jobs: 1

StandardScaler was fitted on training observations.

Chronological evaluation:
- Training: 2001–2020.
- Validation: 2021–2023.
- Testing: 2024–2025.

Distinct feature observations:
- Training: 60,877.
- Validation: 9,034.
- Testing: 5,999.

## 5. Threshold calibration

Anomaly threshold derived from the bottom 5%
of training Isolation Forest scores.

Threshold: -0.563954

Flagged proportions:
- Training: 5.00%.
- Validation: 4.79%.
- Testing: 4.62%.

This threshold is provisional and has not
been calibrated against verified hazard events.

## 6. Commune-level prediction results

Evaluation period: 2024–2025.

Total commune-day records: 8,041.
Flagged anomalies: 337.
Flagged proportion: 4.19%.

All 11 communes were included.

Predictions contain source references, measurement
values, anomaly scores and a research-only label.

## 7. Extreme-weather comparison

Reference indicators from 2001–2020:

- Hot day: daily maximum temperature above the
  monthly 95th percentile for its commune.
- Cold night: daily minimum temperature below
  the monthly 5th percentile for its commune.
- Heavy rainfall: daily CHIRPS rainfall above
  the commune's 95th percentile of wet days
  (wet day defined as rainfall >= 1 mm).

Results for 2024–2025:

| Indicator | Reference observations | Flagged | Overlap |
|---|---:|---:|---:|
| Unusually hot | 1,092 | 129 | 11.81% |
| Unusually cold | 100 | 9 | 9.00% |
| Heavy rainfall | 83 | 76 | 91.57% |
| Any reference extreme | 1,264 | 203 | 16.06% |

Isolation Forest showed strong overlap with the
heavy-rainfall indicator but much lower overlap
with temperature extremes.

These are not independently verified hazard labels.

## 8. Temperature trend investigation

Relative to the 2001–2020 thresholds:

| Period | Hot observations | Cold observations |
|---|---:|---:|
| Training | 5.00% | 4.98% |
| Validation | 12.48% | 1.40% |
| Testing | 14.00% | 1.19% |

Values above use one representative commune from
each of the three distinct NASA POWER grids.

Observed 2021–2025 mean-temperature differences
compared with 2001–2020:

- Grid A (Al Manzla): +1.08°C.
- Grid B (Aquouass Briech): +0.83°C.
- Grid C (Médina): +0.76°C.

Estimated 2001–2025 linear trends:
- Grid A: +0.490°C/decade.
- Grid B: +0.371°C/decade.
- Grid C: +0.360°C/decade.

These are descriptive gridded-data trends,
not formal climate-change attribution.

## 9. MLflow tracking

MLflow version: 3.18.0.
Tracking backend: local SQLite.

The experiment records:
- Model hyperparameters.
- Training and evaluation periods.
- Dataset sizes.
- Anomaly rates and scores.
- Calibrated anomaly threshold.
- Serialized model and metadata artifacts.

The experiment database and generated outputs
are excluded from Git.

## 10. Automated verification

Nine prediction regression tests passed.

Checks include:
- All 11 communes are represented.
- Complete 2024–2025 prediction coverage.
- No duplicate commune-date records.
- Finite anomaly scores.
- Correct threshold application.
- Saved model reproduces predictions.
- Metadata matches model features.
- Research-only labeling.
- CSV output exists.

Tests currently require the local historical
dataset and saved model artifacts.

## 11. Scientific limitations

1. Statistical anomaly does not mean verified hazard.
2. Only three distinct NASA POWER weather histories.
3. Different CHIRPS precipitation estimates provide
   additional commune-level spatial variability.
4. The threshold is research-calibrated, not an
   operational emergency-warning threshold.
5. The model is better aligned with extreme rainfall
   than with temperature extremes.
6. Historical temperature distributions shift across
   the evaluation periods.
7. Results are based on gridded environmental data,
   not independent field-station validation.
8. No independently labeled anomaly benchmark
   has been used.
9. No real-time production deployment is implemented.

## 12. Recommended use in TERRALERT

Use Isolation Forest as an exploratory general
weather-anomaly indicator.

Continue using dedicated temperature thresholds
for heatwave and cold-wave monitoring.

Do not replace flood-risk or wildfire models
with general anomaly flags.

Do not issue public alerts from this model alone.
