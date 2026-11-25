#!/usr/bin/env python3
"""Record TERRALERT forecast service failures."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOLDER = ROOT / "logs/forecast"
FOLDER.mkdir(parents=True, exist_ok=True)

parser = argparse.ArgumentParser()
parser.add_argument("--test", action="store_true")
args = parser.parse_args()

reports = sorted(FOLDER.glob("forecast_run_*.json"))
latest = None

if reports:
    try:
        latest = json.loads(reports[-1].read_text())
    except (ValueError, OSError):
        pass

now = datetime.now(timezone.utc)

notification = {
    "timestamp_utc": now.isoformat(),
    "type": "TEST" if args.test else "PIPELINE_FAILURE",
    "severity": "INFO" if args.test else "ERROR",
    "message": (
        "Notification test"
        if args.test else "TERRALERT forecast service failed"
    ),
    "latest_pipeline_status": (
        latest.get("status") if latest else "UNKNOWN"
    ),
    "latest_pipeline_error": (
        latest.get("error") if latest else None
    ),
    "latest_execution_id": (
        latest.get("execution_id") if latest else None
    ),
}

filename = (
    "notification_test.json"
    if args.test else "latest_failure_notification.json"
)

destination = FOLDER / filename

destination.write_text(
    json.dumps(notification, indent=2),
    encoding="utf-8"
)

print("=== TERRALERT FORECAST NOTIFICATION ===")
print(json.dumps(notification, indent=2))
print("Saved:", destination)
