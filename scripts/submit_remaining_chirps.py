#!/usr/bin/env python3
"""Submit missing TERRALERT CHIRPS annual exports without duplicates."""

import subprocess
import time

import ee

PROJECT = "terralert-research"
ee.Initialize(project=PROJECT)

# Read existing Earth Engine tasks.
tasks = ee.batch.Task.list()
existing = {}

for task in tasks:
    status = task.status()
    description = status.get("description", "")

    prefix = "terralert_chirps_v3_sat_"

    if not description.startswith(prefix):
        continue

    try:
        year = int(description[len(prefix):])
    except ValueError:
        continue

    existing.setdefault(year, []).append(status)

remaining = []

for year in range(2000, 2026):
    statuses = existing.get(year, [])

    if any(
        s.get("state") in (
            "READY", "RUNNING", "COMPLETED"
        )
        for s in statuses
    ):
        print(f"{year}: Already submitted/completed")
        continue

    remaining.append(year)

print("\nYears requiring submission:", remaining)

for year in remaining:
    print(f"\nSubmitting {year}...", flush=True)

    subprocess.run(
        [
            "python",
            "scripts/export_chirps_year.py",
            "--year",
            str(year)
        ],
        check=True
    )

    time.sleep(5)

print("\nAll missing CHIRPS years submitted.")
