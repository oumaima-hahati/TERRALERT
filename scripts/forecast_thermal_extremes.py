#!/usr/bin/env python3
"""Provisional thermal-event forecast from TERRALERT Open-Meteo daily data.

Uses historical monthly commune-specific P90/P10 thresholds and >=3 *complete*
consecutive UTC calendar days. Not an independently trained ML model, calibrated
alert, or a prediction of human impacts. Provider daily Tmax/Tmin require historical
bias evaluation and skill validation before operational use.
"""
import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEAT = ROOT / 'data/heatwaves/processed/heatwave_monthly_thresholds_2001_2025.csv'
COLD = ROOT / 'data/coldwaves/processed/coldwave_monthly_thresholds_2001_2025.csv'
INPUT_DIR = ROOT / 'data/weather/forecasts/open_meteo'
OUTPUT_DIR = ROOT / 'data/weather/forecasts/thermal_extremes'


def load_thresholds(path, key):
    result = {}
    with open(path, newline='', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            identifier = (r['commune'].strip(), int(r['month']))
            value = float(r[key])
            if identifier in result or not math.isfinite(value) or not 1 <= identifier[1] <= 12:
                raise ValueError(f'Invalid/duplicate threshold: {identifier}')
            result[identifier] = value
    return result


def parse_timestamp(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError(f'Forecast time has no timezone: {value}')
    if dt.utcoffset() != timedelta(0):
        raise ValueError(f'Expected UTC forecast time: {value}')
    if dt.minute or dt.second or dt.microsecond:
        raise ValueError(f'Expected exact hourly time: {value}')
    return dt.astimezone(timezone.utc)


def evaluate(hourly_path, heat_path=HEAT, cold_path=COLD):
    heat = load_thresholds(heat_path, 'threshold_p90_c')
    cold = load_thresholds(cold_path, 'threshold_p10_c')
    by_day = defaultdict(dict)
    sources = set()
    retrievals = set()
    with open(hourly_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        needed = {'commune', 'forecast_time_utc', 'temperature_c', 'retrieved_at_utc', 'source'}
        if not needed.issubset(reader.fieldnames or []):
            raise ValueError(f'Missing forecast fields: {needed - set(reader.fieldnames or [])}')
        for r in reader:
            commune = r['commune'].strip()
            dt = parse_timestamp(r['forecast_time_utc'])
            value = float(r['temperature_c'])
            if not math.isfinite(value) or not -100 <= value <= 70:
                raise ValueError(f'Invalid temperature for {commune} at {dt}: {value}')
            day_key = (commune, dt.date())
            if dt.hour in by_day[day_key]:
                raise ValueError(f'Duplicate commune-hour: {commune} {dt}')
            by_day[day_key][dt.hour] = value
            sources.add(r['source'])
            retrievals.add(r['retrieved_at_utc'])
    if not by_day:
        raise ValueError('Empty forecast CSV')
    if len(sources) != 1 or len(retrievals) != 1:
        raise ValueError('Mixed forecast providers or retrieval runs')
    communes = sorted({k[0] for k in by_day})
    if len(communes) != 11:
        raise ValueError(f'Expected 11 communes; got {len(communes)}')
    if {x[0] for x in heat} != set(communes) or {x[0] for x in cold} != set(communes):
        raise ValueError('Threshold commune names differ from forecast')
    if any((c, m) not in heat or (c, m) not in cold for c in communes for m in range(1, 13)):
        raise ValueError('Historical thresholds must cover all 12 months per commune')

    daily = []
    for (commune, date), hours in sorted(by_day.items()):
        # Exclude incomplete UTC dates; never turn missing data into false negatives.
        if set(hours) != set(range(24)):
            continue
        tmax, tmin = max(hours.values()), min(hours.values())
        p90, p10 = heat[(commune, date.month)], cold[(commune, date.month)]
        daily.append({
            'commune': commune, 'forecast_date_utc': date.isoformat(),
            'tmax_hourly_proxy_c': round(tmax, 3), 'tmin_hourly_proxy_c': round(tmin, 3),
            'heat_threshold_p90_c': p90, 'cold_threshold_p10_c': p10,
            'above_heat_threshold': tmax > p90, 'below_cold_threshold': tmin < p10,
            'complete_hours': 24, 'status': 'PROVISIONAL_RESEARCH'
        })
    events = []
    # Only report an event once at least three forecast days confirm the full run.
    for commune in communes:
        rows = [r for r in daily if r['commune'] == commune]
        for hazard, flag in [('heatwave', 'above_heat_threshold'), ('coldwave', 'below_cold_threshold')]:
            segment = []
            for r in rows + [None]:
                contiguous = (r is not None and segment and
                              datetime.fromisoformat(r['forecast_date_utc']).date() -
                              datetime.fromisoformat(segment[-1]['forecast_date_utc']).date() == timedelta(days=1))
                if r is not None and r[flag] and (not segment or contiguous):
                    segment.append(r)
                    continue
                if len(segment) >= 3:
                    events.append({
                        'commune': commune, 'hazard': hazard,
                        'start_date_utc': segment[0]['forecast_date_utc'],
                        'end_date_utc': segment[-1]['forecast_date_utc'],
                        'duration_days': len(segment),
                        'status': 'PROVISIONAL_RESEARCH'
                    })
                segment = [r] if r is not None and r[flag] else []
    return {
        'metadata': {
            'source': next(iter(sources)), 'retrieved_at_utc': next(iter(retrievals)),
            'hourly_file': str(hourly_path), 'communes': len(communes),
            'complete_commune_days': len(daily),
            'date_convention': 'UTC', 'consecutive_days_required': 3,
            'heat_rule': 'hourly_sample_max > historical monthly P90 Tmax',
            'cold_rule': 'hourly_sample_min < historical monthly P10 Tmin',
            'interpretation': 'Research-only potential thermal events; not issued alerts',
            'limitations': [
                'Hourly 2m temperature extrema are not guaranteed true daily Tmax/Tmin',
                'UTC calendar-day boundaries may differ from local civil-day boundaries',
                'Four forecast days limit ability to observe three full consecutive days',
                'No forecast skill evaluation or local calibration yet',
            ],
        }, 'daily': daily, 'events': events
    }



def classify_forecast_lead_time(events, retrieved_at_utc, required_days=3):
    """Annotate event windows with prospective lead time (UTC dates only).

    The retrieval calendar day may have partly elapsed, so only dates strictly
    later than the retrieval date count as fully future forecast days.
    An event including today is not proof it had already begun.
    """
    retrieved = datetime.fromisoformat(retrieved_at_utc.replace('Z', '+00:00'))
    if retrieved.tzinfo is None or retrieved.utcoffset() != timedelta(0):
        raise ValueError('retrieved_at_utc must be timezone-aware UTC')
    retrieved = retrieved.astimezone(timezone.utc)
    today = retrieved.date()
    for event in events:
        start = datetime.strptime(event['start_date_utc'], '%Y-%m-%d').date()
        end = datetime.strptime(event['end_date_utc'], '%Y-%m-%d').date()
        first_future = max(start, today + timedelta(days=1))
        future_days = max(0, (end - first_future).days + 1)
        includes_current = start <= today <= end
        if start > today:
            assessment = 'UPCOMING_FULLY_FUTURE'
        elif future_days >= required_days:
            assessment = 'CURRENT_DAY_INCLUDED_FUTURE_RUN_CONFIRMED'
        elif future_days:
            assessment = 'CURRENT_DAY_DEPENDENT_INSUFFICIENT_FUTURE_DAYS'
        else:
            assessment = 'NO_FULLY_FUTURE_DAYS'
        event.update({
            'forecast_issued_at_utc': retrieved.isoformat(),
            'current_day_included': includes_current,
            'fully_future_consecutive_days': future_days,
            'prospective_three_day_run': future_days >= required_days,
            'prospective_event_start_date_utc': first_future.isoformat() if future_days >= required_days else None,
            'prospective_assessment': assessment,
            'interpretation': 'Potential forecast threshold run; onset and actual occurrence unverified',
        })
    return events


def evaluate_daily(daily_path, heat_path=HEAT, cold_path=COLD):
    """Evaluate provider daily Tmax/Tmin; preserve evaluate() for legacy hourly QA."""
    heat = load_thresholds(heat_path, 'threshold_p90_c')
    cold = load_thresholds(cold_path, 'threshold_p10_c')
    seen = set()
    rows = []
    sources = set()
    retrievals = set()
    with open(daily_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        needed = {'commune', 'forecast_date_utc', 'temperature_max_c', 'temperature_min_c', 'retrieved_at_utc', 'source'}
        if not needed.issubset(reader.fieldnames or []):
            raise ValueError(f'Missing daily forecast fields: {needed - set(reader.fieldnames or [])}')
        for r in reader:
            commune = r['commune'].strip()
            day = datetime.strptime(r['forecast_date_utc'], '%Y-%m-%d').date()
            key = (commune, day)
            if key in seen:
                raise ValueError(f'Duplicate commune-day: {key}')
            seen.add(key)
            tmax, tmin = float(r['temperature_max_c']), float(r['temperature_min_c'])
            if not all(math.isfinite(t) and -100 <= t <= 70 for t in (tmax, tmin)) or tmin > tmax:
                raise ValueError(f'Invalid extrema: {key}')
            p90, p10 = heat.get((commune, day.month)), cold.get((commune, day.month))
            if p90 is None or p10 is None:
                raise ValueError(f'Missing thresholds for {key}')
            rows.append({
                'commune': commune, 'forecast_date_utc': day.isoformat(),
                'tmax_daily_forecast_c': tmax, 'tmin_daily_forecast_c': tmin,
                'heat_threshold_p90_c': p90, 'cold_threshold_p10_c': p10,
                'above_heat_threshold': tmax > p90, 'below_cold_threshold': tmin < p10,
                'status': 'PROVISIONAL_RESEARCH',
            })
            sources.add(r['source'])
            retrievals.add(r['retrieved_at_utc'])
    if len(sources) != 1 or len(retrievals) != 1 or not rows:
        raise ValueError('Empty or mixed forecast runs')
    communes = sorted({r['commune'] for r in rows})
    if len(communes) != 11:
        raise ValueError(f'Expected 11 communes; got {len(communes)}')
    if {k[0] for k in heat} != set(communes) or {k[0] for k in cold} != set(communes):
        raise ValueError('Threshold commune names differ from forecast')
    if any((c, m) not in heat or (c, m) not in cold for c in communes for m in range(1, 13)):
        raise ValueError('Thresholds must cover 12 months for each commune')
    rows.sort(key=lambda r: (r['commune'], r['forecast_date_utc']))
    events = []
    for commune in communes:
        cr = [r for r in rows if r['commune'] == commune]
        for hazard, flag in [('heatwave', 'above_heat_threshold'), ('coldwave', 'below_cold_threshold')]:
            segment = []
            for r in cr + [None]:
                contiguous = (r is not None and segment and
                              (datetime.fromisoformat(r['forecast_date_utc']).date() -
                               datetime.fromisoformat(segment[-1]['forecast_date_utc']).date()).days == 1)
                if r is not None and r[flag] and (not segment or contiguous):
                    segment.append(r)
                    continue
                if len(segment) >= 3:
                    events.append({
                        'commune': commune, 'hazard': hazard,
                        'start_date_utc': segment[0]['forecast_date_utc'],
                        'end_date_utc': segment[-1]['forecast_date_utc'],
                        'duration_days': len(segment), 'status': 'PROVISIONAL_RESEARCH',
                    })
                segment = [r] if r is not None and r[flag] else []
    classify_forecast_lead_time(events, next(iter(retrievals)))
    return {'metadata': {
        'source': next(iter(sources)), 'retrieved_at_utc': next(iter(retrievals)),
        'daily_file': str(daily_path), 'communes': len(communes),
        'commune_days': len(rows), 'date_convention': 'UTC',
        'consecutive_days_required': 3,
        'lead_time_convention': 'Only UTC dates strictly after forecast retrieval date are fully future',
        'heat_rule': 'Open-Meteo daily Tmax > NASA POWER historical monthly P90 Tmax',
        'cold_rule': 'Open-Meteo daily Tmin < NASA POWER historical monthly P10 Tmin',
        'interpretation': 'Research-only potential thermal events; not issued alerts',
        'limitations': [
            'NASA POWER baseline has only three unique historical temperature series for 11 communes',
            'Provider temperature bias between Open-Meteo and NASA POWER is not yet calibrated',
            'Retrieval-day extrema may refer to hours already elapsed; event onset is unverified',
            'Four forecast days limit consecutive-day assessment',
            'No forecast skill evaluation against observations yet',
        ],
    }, 'daily': rows, 'events': events}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--daily', type=Path, help='Exact daily_forecast_*.csv input (default latest)')
    group.add_argument('--hourly', type=Path, help='Legacy research-only hourly proxy mode')
    parser.add_argument('--heat-thresholds', type=Path, default=HEAT)
    parser.add_argument('--cold-thresholds', type=Path, default=COLD)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.hourly:
        source = args.hourly
        result = evaluate(source, args.heat_thresholds, args.cold_thresholds)
        run_id = source.stem.removeprefix('forecast_')
        mode = 'LEGACY HOURLY PROXY'
    else:
        candidates = sorted(INPUT_DIR.glob('daily_forecast_*.csv'))
        source = args.daily or (candidates[-1] if candidates else None)
        if source is None:
            parser.error('No daily forecast CSV found. Re-run scripts/download_wildfire_forecasts.py.')
        result = evaluate_daily(source, args.heat_thresholds, args.cold_thresholds)
        run_id = source.stem.removeprefix('daily_forecast_')
        mode = 'PROVIDER DAILY EXTREMA'
    output = args.output or OUTPUT_DIR / f'thermal_extremes_{run_id}.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print('TERRALERT THERMAL FORECAST (RESEARCH ONLY):', mode)
    print('Input:', source)
    print('Commune-days:', len(result['daily']))
    print('Potential events:', len(result['events']))
    for event in result['events']:
        print(event['commune'], event['hazard'], event['start_date_utc'], event['end_date_utc'],
              event.get('prospective_assessment', 'LEGACY_HOURLY_MODE'),
              'future_days=', event.get('fully_future_consecutive_days', 'N/A'))
    print('Saved:', output)


if __name__ == '__main__':
    main()
