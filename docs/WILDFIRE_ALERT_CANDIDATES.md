# TERRALERT: provisional wildfire alert candidates

This module **does not issue public alerts**. It converts validated-format daily FWI forecast CSV rows into research-only candidate records for future API/dashboard integration.

Run from project root with the project virtualenv:

```bash
python -m unittest discover -s tests -p 'test_wildfire_alert_candidates.py' -v
python scripts/generate_wildfire_alert_candidates.py
```

Or specify an input file and output location with `--input` and `--output`.

## Current example policy (not an official warning policy)

FWI `<21.3`: no alert candidate; `21.3–<38`: High candidate; `38–<50`: Very High candidate; `>=50`: Extreme candidate. The scheme follows the existing TERRALERT CSV danger categories and is **not calibrated for Moroccan public warnings**.

The output lives under `data/wildfires/alerts/` and is a generated artifact that should not be committed. Even if there are no candidates, the output JSON contains an empty `candidates` array.

FWI estimates meteorological fire danger, not wildfire ignition probability. Do not use this module to send emails, SMS, push alerts, or public warnings without independent verification and an approved warning policy. Additional work needed: validate FWI inputs, examine regional categories, API/PostGIS integration, schedule and freshness checks, and dashboard labeling.
