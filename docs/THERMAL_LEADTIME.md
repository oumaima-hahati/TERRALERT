# TERRALERT — Thermal forecast lead-time annotation (research only)

This patch changes only `scripts/forecast_thermal_extremes.py` and adds tests. It does not modify the Open-Meteo downloader, historical thresholds, wildfire FWI, PostGIS, or API contracts.

The existing event window is kept, but a retrieval-day forecast is **not** regarded as a fully prospective day. For a run downloaded on 2026-11-27 at 10:24 UTC that flags November 27–30, the detector reports three fully future consecutive dates (November 28–30) and `CURRENT_DAY_INCLUDED_FUTURE_RUN_CONFIRMED`. This is not evidence that a cold wave is already underway. For a flagged run November 27–29, only two days are fully future and the assessment is `CURRENT_DAY_DEPENDENT_INSUFFICIENT_FUTURE_DAYS`. An event starting on November 28 is `UPCOMING_FULLY_FUTURE`.

New **event-level** JSON fields:
- `forecast_issued_at_utc` — timestamp supplied by ingestion
- `current_day_included` — whether the event spans the retrieval calendar date
- `fully_future_consecutive_days` — consecutive qualifying dates strictly after retrieval date
- `prospective_three_day_run` — whether >=3 fully future dates qualify
- `prospective_event_start_date_utc` — start of fully prospective 3-day run, otherwise null
- `prospective_assessment` — one of `UPCOMING_FULLY_FUTURE`, `CURRENT_DAY_INCLUDED_FUTURE_RUN_CONFIRMED`, `CURRENT_DAY_DEPENDENT_INSUFFICIENT_FUTURE_DAYS`, `NO_FULLY_FUTURE_DAYS`

Run:
```bash
python3 -m unittest discover -s tests -p 'test_thermal*.py' -v
python3 scripts/forecast_thermal_extremes.py
```

You do **not** have to re-download weather data: the detector reuses the latest saved daily forecast.

**Limitations:** NASA POWER temperatures for the 11 communes comprise only 3 unique historical daily series. Open-Meteo/NASA POWER bias and actual forecast skill have not been evaluated. Four-day forecasts cannot prove the event's actual onset. UTC-day conventions are retained. This is a provisional scientific assessment, not an alert.
