# TERRALERT thermal forecast — daily extrema upgrade (research only)

This patch extends the existing Open-Meteo downloader. It **retains the hourly CSV schema** consumed by wildfire FWI and adds `daily_forecast_<run>.csv` using `temperature_2m_max` and `temperature_2m_min`, UTC, and four forecast days. It does not modify historical files, perform data migration, issue alerts or change shared APIs.

## Upgrade files
- `scripts/download_wildfire_forecasts.py` (replaces downloader, preserving existing hourly output)
- `scripts/forecast_thermal_extremes.py` (daily forecast preferred; `--hourly` remains for legacy research QA)
- `tests/test_thermal_forecast.py` (existing regression tests)
- `tests/test_thermal_daily.py` (new daily-input tests)

## Run
```bash
python3 -m unittest discover -s tests -p 'test_thermal*.py' -v
python3 scripts/download_wildfire_forecasts.py
python3 scripts/forecast_thermal_extremes.py
```

Inspect both forecast artifacts: `data/weather/forecasts/open_meteo/forecast_<run>.csv` (hourly) and `daily_forecast_<run>.csv` (daily). Output: `data/weather/forecasts/thermal_extremes/thermal_extremes_<run>.json`.

## Important limitations
- NASA POWER historical dataset provides only **three distinct temperature series** for 11 commune assignments, verified via 9,131 identical Tmin/Tmax daily records for each group.
- Open-Meteo daily extrema and NASA POWER daily extrema are different sources; systematic offsets have not been calibrated.
- Four-day horizon, UTC boundaries, potential forecast revisions and the threshold-duration rule limit interpretation.
- Outputs are **provisional scientific signals**, not official warnings or calibrated event probabilities.
- This patch was tested offline; verify live Open-Meteo responses before treating the upgrade as operational.
