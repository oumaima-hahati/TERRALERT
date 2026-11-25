#!/usr/bin/env python3
"""TERRALERT provisional wildfire forecast automation."""

import csv
import os
import json
import math
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs" / "forecast"
LOG_DIR.mkdir(parents=True, exist_ok=True)

started = datetime.now(timezone.utc)
execution_id = started.strftime("%Y%m%dT%H%M%S%fZ")

log_path = LOG_DIR / f"forecast_run_{execution_id}.log"
status_path = LOG_DIR / f"forecast_run_{execution_id}.json"

steps = [
    (
        "Download hourly forecasts",
        "scripts/download_wildfire_forecasts.py",
        "data/weather/forecasts/open_meteo",
        "forecast_*.csv",
    ),
    (
        "Prepare operational FWI inputs",
        "scripts/prepare_operational_fwi_weather.py",
        "data/weather/forecasts/fwi_inputs",
        "fwi_weather_*.csv",
    ),
    (
        "Calculate provisional FWI",
        "scripts/calculate_operational_wildfire_fwi.py",
        "data/wildfires/forecasts",
        "fwi_forecast_*.csv",
    ),
    (
        "Generate forecast GIS",
        "scripts/create_wildfire_forecast_gis.py",
        "data/wildfires/gis",
        "wildfire_forecast_*.gpkg",
    ),
]

completed = []
outputs = {}
status = "FAILED"
error = None


def log(message):
    print(message, flush=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(message + "\n")


def run_step(number, name, script, folder, pattern, env_overrides=None):
    directory = ROOT / folder
    before = set(directory.glob(pattern)) if directory.exists() else set()

    log(f"\n[{number}/4] {name}")

    environment = os.environ.copy()
    environment.update(env_overrides or {})

    result = subprocess.run(
        [sys.executable, str(ROOT / script)],
        env=environment,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=900,
    )

    with log_path.open("a", encoding="utf-8") as f:
        f.write(result.stdout)
        f.write(result.stderr)

    if result.returncode != 0:
        log(result.stdout[-2000:])
        log(result.stderr[-2000:])
        raise RuntimeError(
            f"{name} failed with exit code {result.returncode}"
        )

    after = set(directory.glob(pattern))
    created = sorted(after - before)

    if len(created) != 1:
        raise RuntimeError(
            f"{name}: expected exactly one new output, "
            f"found {len(created)}"
        )

    output = created[0]

    if output.stat().st_size == 0:
        raise RuntimeError(f"Empty output: {output}")

    log(f"SUCCESS: {output.relative_to(ROOT)}")
    completed.append(name)
    outputs[name] = str(output.relative_to(ROOT))
    return output


try:
    log("=== TERRALERT AUTOMATED FORECAST ===")
    log(f"Execution ID: {execution_id}")
    log("Public alerts: DISABLED")
    log("Status: PROVISIONAL_RESEARCH")

    paths = []

    for index, step in enumerate(steps, 1):
        environment = {}

        if index == 3:
            environment["TERRALERT_FWI_WEATHER_FILE"] = str(
                paths[1].resolve()
            )
        elif index == 4:
            environment["TERRALERT_FWI_FORECAST_FILE"] = str(
                paths[2].resolve()
            )

        paths.append(run_step(
            index, *step, env_overrides=environment
        ))

        # Prevent the FWI calculator and GIS builder
        # from silently using an earlier run.
        if index == 2:
            fwi_input = paths[1]
            run_id = fwi_input.stem.removeprefix("fwi_weather_")

        if index == 3:
            expected = f"fwi_forecast_{run_id}.csv"
            if paths[2].name != expected:
                raise RuntimeError(
                    "FWI output does not match current input run"
                )

        if index == 4:
            expected = f"wildfire_forecast_{run_id}.gpkg"
            if paths[3].name != expected:
                raise RuntimeError(
                    "GIS output does not match current FWI run"
                )

    forecast_csv = paths[2]

    with forecast_csv.open(
        encoding="utf-8", newline=""
    ) as f:
        records = list(csv.DictReader(f))

    communes = {r["commune"] for r in records}
    dates = {r["date"] for r in records}
    pairs = {(r["commune"], r["date"]) for r in records}

    if not (
        len(records) == 33
        and len(communes) == 11
        and len(dates) == 3
        and len(pairs) == 33
    ):
        raise ValueError("Incomplete 72-hour forecast coverage")

    if any(
        r["model_status"] != "PROVISIONAL_RESEARCH"
        for r in records
    ):
        raise ValueError("Unexpected model status")

    if any(
        not math.isfinite(float(r["fwi"]))
        or float(r["fwi"]) < 0
        for r in records
    ):
        raise ValueError("Invalid forecast FWI values")

    # Validate the GeoPackage's feature count.
    import sqlite3

    with sqlite3.connect(paths[3]) as conn:
        table_row = conn.execute("""
            SELECT table_name
            FROM gpkg_contents
            WHERE data_type = 'features'
        """).fetchone()

        if table_row is None:
            raise ValueError("No GIS feature layer found")

        table_name = table_row[0].replace('"', '""')
        feature_count = conn.execute(
            f'SELECT COUNT(*) FROM "{table_name}"'
        ).fetchone()[0]

        integrity = conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

    if feature_count != 33 or integrity != "ok":
        raise ValueError("GIS output validation failed")

    status = "SUCCESS"

    log("\n=== FINAL VALIDATION ===")
    log(f"Communes: {len(communes)}")
    log(f"Forecast dates: {len(dates)}")
    log(f"FWI records: {len(records)}")
    log(f"GIS features: {feature_count}")
    log(f"Database integrity: {integrity}")
    log("Public alerts generated: NO")
    log("\nSUCCESS: Automated forecast pipeline completed!")

except Exception as exc:
    error = str(exc)
    log("\n=== PIPELINE FAILED ===")
    log(error)
    log(traceback.format_exc())

finally:
    finished = datetime.now(timezone.utc)

    report = {
        "execution_id": execution_id,
        "started_at_utc": started.isoformat(),
        "finished_at_utc": finished.isoformat(),
        "status": status,
        "completed_steps": completed,
        "outputs": outputs,
        "error": error,
        "public_alerts_enabled": False,
        "model_status": "PROVISIONAL_RESEARCH",
    }

    status_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    log(f"\nRun status: {status}")
    log(f"Status file: {status_path.relative_to(ROOT)}")

if status != "SUCCESS":
    sys.exit(1)
