#!/usr/bin/env python3
"""Generate research-only wildfire alert candidates from TERRALERT FWI forecasts.

No emails, notifications, API requests, database updates, or public warnings.
"""
import argparse
import csv
import json
import math
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

INPUT_DIR = Path('data/wildfires/forecasts')
OUTPUT_DIR = Path('data/wildfires/alerts')
REQUIRED = {'commune', 'date', 'fwi', 'danger_level', 'quality', 'model_status', 'weather_source', 'forecast_run'}
CANDIDATES = {'High', 'Very High', 'Extreme'}


def level_from_fwi(fwi):
    if fwi < 5.2: return 'Very Low'
    if fwi < 11.2: return 'Low'
    if fwi < 21.3: return 'Moderate'
    if fwi < 38: return 'High'
    if fwi < 50: return 'Very High'
    return 'Extreme'


def assess(rows, generated_at_utc):
    if not rows:
        raise ValueError('Forecast CSV has no records')
    output, keys, runs = [], set(), set()
    for line, row in enumerate(rows, start=2):
        missing = REQUIRED - set(row)
        if missing:
            raise ValueError(f'Row {line}: missing columns {sorted(missing)}')
        commune, day = row['commune'].strip(), row['date'].strip()
        if not commune:
            raise ValueError(f'Row {line}: empty commune')
        date.fromisoformat(day)
        key = (commune, day)
        if key in keys:
            raise ValueError(f'Duplicate commune-date {key}')
        keys.add(key)
        fwi = float(row['fwi'])
        if not math.isfinite(fwi) or fwi < 0:
            raise ValueError(f'Row {line}: invalid FWI')
        computed = level_from_fwi(fwi)
        if row['danger_level'] != computed:
            raise ValueError(f'Row {line}: FWI danger mismatch: {fwi} -> {computed}, CSV says {row["danger_level"]}')
        if row['quality'] != 'provisional' or row['model_status'] != 'PROVISIONAL_RESEARCH':
            raise ValueError(f'Row {line}: unexpected model status/quality')
        run = row['forecast_run'].strip()
        if not run:
            raise ValueError(f'Row {line}: missing forecast_run')
        runs.add(run)
        if computed in CANDIDATES:
            output.append({
                'commune': commune,
                'forecast_date': day,
                'hazard': 'wildfire_fire_weather',
                'fwi': round(fwi, 3),
                'danger_level': computed,
                'candidate_priority': computed.upper().replace(' ', '_'),
                'forecast_run': run,
                'weather_source': row['weather_source'],
                'generated_at_utc': generated_at_utc,
                'status': 'RESEARCH_ONLY_NOT_ISSUED',
                'interpretation': 'Fire-weather danger, not a wildfire ignition forecast',
            })
    if len(runs) != 1:
        raise ValueError(f'Mixed forecast runs: {sorted(runs)}')
    return sorted(output, key=lambda r:(r['forecast_date'],r['commune']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, help='FWI forecast CSV (default: latest by filename)')
    parser.add_argument('--output', type=Path, help='Output JSON path')
    args = parser.parse_args()
    if args.input:
        source = args.input
    else:
        matches = sorted(INPUT_DIR.glob('fwi_forecast_*.csv'))
        if not matches:
            parser.error('No FWI forecast CSV found')
        source = matches[-1]
    with source.open(newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    generated_at = datetime.now(timezone.utc).isoformat()
    candidates = assess(rows, generated_at)
    run_id = rows[0]['forecast_run']
    destination = args.output or OUTPUT_DIR / f'wildfire_alert_candidates_{run_id}.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = {
        'metadata': {
            'source_file': str(source),
            'forecast_run': run_id,
            'generated_at_utc': generated_at,
            'records_evaluated': len(rows),
            'candidate_count': len(candidates),
            'counts_by_level': dict(Counter(r['danger_level'] for r in candidates)),
            'policy': 'High+ FWI creates research-only candidate; no public alerts',
            'status': 'RESEARCH_ONLY_NOT_ISSUED',
        },
        'candidates': candidates,
    }
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('=== TERRALERT WILDFIRE ALERT CANDIDATES (RESEARCH ONLY) ===')
    print('Input:', source)
    print('FWI records evaluated:', len(rows))
    print('High+ candidates:', len(candidates))
    print('Saved:', destination)
    print('Public alerts/notifications issued: NO')


if __name__ == '__main__':
    main()
