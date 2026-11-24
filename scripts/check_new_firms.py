#!/usr/bin/env python3
"""Check new FIRMS detections in a Tangier-area BBOX (not precise commune clipping).

First run establishes a baseline. Later runs output newly seen observations.
No external Python packages required. Keep API key in FIRMS_MAP_KEY.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

BBOX = '-6.25,35.45,-5.55,36.05'  # west,south,east,north
SOURCE = 'VIIRS_NOAA20_NRT'
DAYS = 5
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'wildfires' / 'nrt'
STATE_FILE = OUT / 'seen_firms_ids.json'
REQUIRED = {'latitude', 'longitude', 'acq_date', 'acq_time'}


def read_csv_data(contents):
    reader = csv.DictReader(io.StringIO(contents.lstrip('\ufeff')))
    fields = reader.fieldnames or []
    if not REQUIRED.issubset(fields):
        raise ValueError('Invalid FIRMS CSV response: expected columns are missing')
    rows = list(reader)
    for row in rows:
        if not all(row.get(f) for f in REQUIRED):
            raise ValueError('Invalid FIRMS row: missing coordinate/date/time')
    return fields, rows


def detection_id(row):
    # Distinct satellite products can cover the same event; do not conflate them.
    key = '|'.join([SOURCE, row['latitude'].strip(), row['longitude'].strip(),
                    row['acq_date'].strip(), row['acq_time'].strip(),
                    row.get('satellite', '').strip()])
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


def save_csv(path, fields, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-csv', type=Path,
                        help='Offline test with an existing FIRMS CSV; no API request')
    args = parser.parse_args()
    if args.input_csv:
        content = args.input_csv.read_text(encoding='utf-8-sig')
    else:
        key = os.environ.get('FIRMS_MAP_KEY')
        if not key:
            sys.exit('Error: set FIRMS_MAP_KEY in your terminal first.')
        url = ('https://firms.modaps.eosdis.nasa.gov/api/area/csv/'
               f'{key}/{SOURCE}/{BBOX}/{DAYS}')
        try:
            with urlopen(url, timeout=90) as response:
                content = response.read().decode('utf-8-sig')
        except (HTTPError, URLError, TimeoutError) as exc:
            # Never print the request URL (it contains a secret API key).
            sys.exit(f'FIRMS network request failed ({type(exc).__name__}).')

    try:
        fields, rows = read_csv_data(content)
    except ValueError as exc:
        sys.exit(str(exc))

    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    snapshot = OUT / f'firms_check_{stamp}.csv'
    save_csv(snapshot, fields, rows)

    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text(encoding='utf-8'))
        seen = set(state.get('seen_ids', []))
        first_run = False
    else:
        seen = set()
        first_run = True

    unique_rows = {}
    for row in rows:
        unique_rows.setdefault(detection_id(row), row)

    # Initial run intentionally records a baseline, without reporting preexisting
    # detections as newly discovered. Run again to detect additions.
    novel = [] if first_run else [row for uid, row in unique_rows.items() if uid not in seen]
    if novel:
        save_csv(OUT / f'firms_NEW_{stamp}.csv', fields, novel)

    updated = sorted(seen | set(unique_rows))
    state_tmp = STATE_FILE.with_suffix('.tmp')
    state_tmp.write_text(json.dumps({'seen_ids': updated}, indent=2), encoding='utf-8')
    state_tmp.replace(STATE_FILE)

    print(f'NASA FIRMS check successful: {len(rows)} rows in latest {DAYS}-day window.')
    print(f'Unique detections in response: {len(unique_rows)}')
    print(f'Newly seen detections: {len(novel)}')
    print(f'Raw snapshot: {snapshot}')
    if first_run:
        print('First run: baseline established; no new-detection alert generated.')
    elif novel:
        print(f'New detections saved: {OUT / f"firms_NEW_{stamp}.csv"}')
    print('IMPORTANT: Area is a broad bounding box, not the exact 11 communes.')
    print('Thermal detections do not necessarily indicate confirmed wildfires.')


if __name__ == '__main__':
    main()
