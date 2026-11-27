# TERRALERT — provisional thermal-forecast detector

This module consumes the **existing** `scripts/download_wildfire_forecasts.py` hourly Open-Meteo CSV and the **existing** retrospective monthly thresholds from 2001–2025. It does not retrain a model or change wildfire FWI, rainfall, PostGIS, or frontend code.

## Run

From the TERRALERT repository root with your Python virtual environment active:

```bash
python -m unittest discover -s tests -p 'test_thermal_forecast.py' -v
python scripts/forecast_thermal_extremes.py --hourly data/weather/forecasts/open_meteo/forecast_YYYYMMDDTHHMMSSZ.csv
```

Replace the forecast filename with an actual existing file. Alternatively, omit `--hourly` to use the latest filename. To refresh forecast data, run `python scripts/download_wildfire_forecasts.py` first, which makes 11 live Open-Meteo API calls.

JSON outputs go to `data/weather/forecasts/thermal_extremes/`; they are generated artifacts and normally should not be pushed. Source code, tests and this documentation should be committed to a **new feature branch**.

## Method

For each of 11 communes, extract the min/max of **24 hourly UTC temperature samples** on a complete UTC date. Compare maximum against the historical monthly 90th percentile of daily Tmax, and minimum against the historical monthly 10th percentile of daily Tmin. An episode is emitted only after >=3 consecutive complete forecast days exceed the respective threshold. Missing/incomplete days cannot cause an alert or be silently filled. Metadata includes input timestamp and research status.

## Scientific limitations

- Hourly sampling is only a proxy for daily extremes, potentially missing true Tmax/Tmin. For an operational detector, request forecast `daily=temperature_2m_max,temperature_2m_min`, ensure time conventions match baseline historical definitions, and validate bias.
- Hourly data in UTC may not line up with Moroccan local civil days. Day-boundary alignment must be resolved before a production alert system.
- Four-day horizons and incomplete starting days restrict full three-day episode detection. A zero-event output does **not** prove absence of risk.
- Historical thresholds derived from one source (NASA POWER) may differ systematically from Open-Meteo model temperatures. Backtesting is essential.
- These are threshold-based potential events, **not** calibrated probabilities, independently trained ML forecasts, or approved public warnings.
- Evaluate across seasons and communes, including false-alarm rate, recall, event onset error and lead time; compare against real observed events and other established operational definitions.

## Next integration steps

After validating the thermal module, add it as a *separate optional step* in the existing automated forecast orchestration without disrupting existing wildfire and rainfall steps. Agree on the database/API payload with Rayane before integration. Wildfire remains in the existing FWI pipeline; it estimates **fire-weather danger**, not ignition certainty. Do not automatically publish citizen-facing alerts until validation and review.
