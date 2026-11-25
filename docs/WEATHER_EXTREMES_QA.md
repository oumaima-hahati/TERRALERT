# TERRALERT — Weather and Extreme-Temperature QA

## Scope
11 study areas in Tanger-Assilah, 2001–2025.

Data source: NASA POWER temperature and meteorological
variables, combined with CHIRPS v3 precipitation.

## Results
- Structural weather and event QA: 23/23 passed.
- Heatwave consistency checks: 3/3 passed.
- Cold-wave consistency checks: 3/3 passed.
- Total automated checks: 29/29 passed.
- Historical heatwave episodes: 1,025 commune-level episodes.
- Historical cold-wave episodes: 1,200 commune-level episodes.

## Spatial independence
Only three distinct daily temperature series were identified:

Group 1:
Al Manzla, Bni Makada, Dar Chaoui,
Hjar Ennhal, Laaouama, Sebt Azzinate.

Group 2:
Aquouass Briech, Gueznaia.

Group 3:
Mghogha, Medina, Souani.

These identical series limit spatial independence.
The commune-level event totals must not be interpreted
as counts of independent meteorological events.

## Methodology
Heatwaves: monthly 90th percentile of daily maximum
temperature, exceeded for at least 3 consecutive days.

Cold waves: monthly 10th percentile of daily minimum
temperature, below threshold for at least 3 consecutive days.

These definitions are research baselines, not official
Moroccan warning thresholds.

## Limitations
- No independent station-based validation completed.
- Monthly thresholds may create month-boundary artifacts.
- Historical thresholds use the same period being evaluated.
- Coarse meteorological inputs limit local discrimination.
- Automated consistency QA does not establish forecast skill.

## Conclusion
Internal structural and event-consistency QA: PASSED.

Independent meteorological validation: PENDING.

Status: INTERNAL RESEARCH QA COMPLETED.
