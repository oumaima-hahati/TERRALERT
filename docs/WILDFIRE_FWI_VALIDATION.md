# TERRALERT — Wildfire FWI Preliminary Validation

## 1. Study area

11 communes in the Tangier–Assilah study area, Morocco.

## 2. Weather inputs

Source: Open-Meteo Historical API, ERA5-Seamless.

Variables:
- Air temperature at 2 m (°C)
- Relative humidity at 2 m (%)
- Wind speed at 10 m (km/h)
- Precipitation over the preceding 24 hours (mm)

Weather inputs were extracted at local civil noon.

Available history:
- January 2000 to July 2006
- January 2024

The complete 2000–2025 historical dataset is not yet available.

## 3. Canadian Fire Weather Index

Calculated components:
- FFMC
- DMC
- DC
- ISI
- BUI
- FWI

The model carries moisture-code values forward between
consecutive days and reinitializes them after historical gaps.

Initial values:
- FFMC = 85
- DMC = 6
- DC = 15

The first 30 days of each continuous segment are flagged
as provisional warm-up observations.

## 4. Numerical checks

Total FWI records: 26,763
Post-warm-up records: 26,103
Warm-up records: 660
Historical discontinuity resets: 11
Duplicate commune-date records: 0
Detected numerical validation errors: 0
Maximum calculated FWI: 84.863

These checks do not constitute independent verification
of the Canadian FWI equations.

## 5. FIRMS historical comparison

Historical MODIS detections: 220
Presumed vegetation-fire detections (TYPE=0): 177
Detections matched with post-warm-up FWI: 29
Detections without weather overlap: 148

Matched detections by danger category:
- High: 13
- Very High: 6
- Extreme: 10

The 29 matched detections correspond to 17 unique
commune-days with satellite fire detections.

## 6. Exploratory evaluation

Same-day FWI:
- 17/17 detection-days classified High or above
- Detection-day sensitivity: 100%
- High+ rate on no-detection days: 36.31%

Previous-day FWI:
- 16/17 detection-days preceded by High+ FWI
- Detection-day sensitivity: 94.12%
- High+ rate on no-detection days: 36.29%

These statistics are descriptive and do not demonstrate
operational forecasting accuracy.

## 7. Observation timing

Of 29 matched satellite detections:
- 3 occurred before the same-day FWI weather observation
- 26 occurred at or after the observation

Observation time alone does not establish when an
operational warning could have been issued.

## 8. Investigated missed detection-day

Commune: Hjar Ennhal
Date: 2003-08-29
Previous-day FWI: 18.265 (Moderate)
Same-day FWI: 25.590 (High)
FIRMS acquisition: 11:25 UTC
Same-day weather observation: 12:00 UTC

The previous-day FWI decrease coincided with increased
humidity and 1.1 mm of precipitation.

## 9. Scientific limitations

- Only 17 unique detected fire-days could be evaluated.
- Historical weather coverage is incomplete.
- FIRMS hotspots are not independently confirmed incidents.
- Multiple hotspots may correspond to the same wildfire.
- Absence of a FIRMS hotspot does not prove absence of fire.
- Danger thresholds are not calibrated for the study area.
- Neighboring communes may share coarse weather grid cells.
- Local civil noon is not necessarily the standardized
  observation convention for the Canadian FWI system.
- Monthly state initialization and warm-up require further review.
- Independent FWI reference-value testing is pending.
- CHIRPS rainfall comparison remains pending.
- This is not an operational early-warning validation.

## 10. Current status

Provisional FWI model: Implemented
Numerical validation: Passed
Historical FIRMS comparison: Completed for overlapping dates
Independent scientific validation: Pending
Operational alert validation: Pending

Results must not be presented as calibrated wildfire
probabilities or confirmed fire predictions.
