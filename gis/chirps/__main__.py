"""Preview or acquire a bounded CHIRPS v3.0 Final daily rnl sample."""

import argparse
from datetime import date, datetime, timezone
import fcntl
from hashlib import file_digest
import json
from math import isfinite
import os
from pathlib import Path
import signal
import subprocess
import sys

from .download import MAX_BYTES, RangeReader, TransferBudget, plan
from .read import SingleRaster, read_day, validate_bbox
from .resume import load_cache, requested_days
from .save import save_day, save_manifest
from .validate import validate_series

PROVISIONAL_BBOX = (-5.95, 35.60, -5.65, 35.85)
DATE_CONVENTION = "UTC calendar-day label from CHIRPS daily disaggregation"


def acquire(sources, bbox, output: Path, budget: TransferBudget, *, dates=None,
            cached=None) -> dict:
    if cached is None:
        output.mkdir(parents=True, exist_ok=False)
        cached = []
    dates = dates if dates is not None else [source.day for source in sources]
    manifest = {
        "start": dates[0].isoformat(),
        "end": dates[-1].isoformat(),
        "product": "CHIRPS v3.0 Final daily rnl",
        "source_documentation": "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/readme.txt",
        "date_convention": DATE_CONVENTION,
        "requested_bounds_wgs84_wsen": list(bbox),
        "coverage_scope": "Provisional test box; no approved Tangier boundary used",
        "acquisition_mode": "HTTP ranges; raw inputs are extracted native-grid windows",
        "limit_bytes": budget.limit,
        "planned_full_file_upper_bound_bytes": sum(s.size_bytes for s in sources),
        "previous_body_bytes_transferred": budget.used,
        "sources": [dict(entry) for entry, _ in cached],
        "status": "running",
    }
    days = [day for _, day in cached]
    manifest_path = output / "manifest.json"

    def checkpoint():
        manifest["body_bytes_transferred"] = budget.used
        manifest["remaining_dates"] = [day.isoformat() for day in dates[len(days):]]
        save_manifest(manifest_path, manifest)

    checkpoint()
    try:
        for source in sources:
            before = budget.used
            entry = {
                "date": source.day.isoformat(),
                "url": source.url,
                "full_size_bytes": source.size_bytes,
                "revision": dict([source.revision]) if source.revision else {},
                "started_at_utc": datetime.now(timezone.utc).isoformat(),
            }
            manifest["sources"].append(entry)
            try:
                # The opener reads through our HTTP adapter, so all raster body
                # bytes use the same cap and full-file responses are rejected.
                with RangeReader(source, budget) as reader:
                    filename = Path(source.url).name

                    try:
                        day = read_day(filename, source.day, bbox,
                                       opener=SingleRaster(filename, reader))
                    except Exception:
                        if reader.error:
                            raise reader.error
                        raise
                    if reader.error:
                        raise reader.error
                validate_series([*days, day], dates[0], day.day, bbox)
                entry["acquired_at_utc"] = datetime.now(timezone.utc).isoformat()
                entry["source_bounds"] = day.source_bounds
                entry["source_nodata"] = (str(day.nodata) if day.nodata is not None
                                          and not isfinite(day.nodata) else day.nodata)
                entry["units"] = day.units
                raw = Path("raw") / Path(source.url).name
                entry["raw_subset_sha256"] = save_day(output / raw, day)
                entry["raw_subset"] = raw.as_posix()
                days.append(day)
            finally:
                entry["body_bytes_transferred"] = budget.used - before
            checkpoint()
        manifest["validation"] = validate_series(days, dates[0], dates[-1], bbox)
        for day, entry in zip(days, manifest["sources"]):
            processed = Path("processed") / f"precipitation-{day.day}.tif"
            destination = output / processed
            if destination.exists():
                with destination.open("rb") as content:
                    digest = file_digest(content, "sha256").hexdigest()
                if digest != entry["raw_subset_sha256"]:
                    raise ValueError(f"Unexpected existing processed raster for {day.day}")
                entry["processed_sha256"] = digest
            else:
                entry["processed_sha256"] = save_day(destination, day)
            entry["processed"] = processed.as_posix()
        manifest["status"] = "passed"
    except Exception as error:
        manifest["status"] = "failed"
        manifest["error"] = str(error)
        raise
    finally:
        checkpoint()
    return manifest


def run_isolated(options) -> int:
    """Keep crash reporting outside the process that opens the raster."""
    output = options.output
    if output.exists() and not options.resume:
        print(f"CHIRPS stopped: output directory already exists: {output}", file=sys.stderr)
        return 1
    command = [sys.executable, "-X", "faulthandler", "-m", "gis.chirps",
               *sys.argv[1:], "--worker"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, errors="replace")
        if result.stdout:
            print(result.stdout, end="", flush=True)
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr, flush=True)
        if result.returncode == 0:
            return 0
        returncode = result.returncode
        error = (f"Reader subprocess terminated by {signal.Signals(-returncode).name}"
                 if returncode < 0 else f"Reader subprocess exited with code {returncode}")
        diagnostics = result.stderr.strip()
    except OSError as exc:
        returncode, error, diagnostics = None, str(exc), ""

    manifest = output / "manifest.json"
    existing = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else None
    if existing and existing.get("status") == "running":
        existing.update(status="failed", error=error, worker_stderr=diagnostics,
                        worker_returncode=returncode, transfer_unmeasured=True)
        save_manifest(manifest, existing)
        print(f"Failure manifest: {manifest}", file=sys.stderr)
    elif not manifest.exists():
        output.mkdir(parents=True, exist_ok=True)
        save_manifest(manifest, {
            "status": "failed",
            "product": "CHIRPS v3.0 Final daily rnl",
            "start": options.start.isoformat(),
            "end": options.end.isoformat(),
            "requested_bounds_wgs84_wsen": list(options.bbox),
            "coverage_scope": "Provisional test box; no approved Tangier boundary used",
            "limit_bytes": MAX_BYTES,
            "body_bytes_transferred": None,
            "remaining_dates": [day.isoformat() for day in requested_days(options.start, options.end)],
            "worker_returncode": returncode,
            "error": error,
            "worker_stderr": diagnostics,
        })
        print(f"Failure manifest: {manifest}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2024, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2024, 1, 7))
    parser.add_argument("--bbox", type=float, nargs=4, default=PROVISIONAL_BBOX,
                        metavar=("WEST", "SOUTH", "EAST", "NORTH"))
    parser.add_argument("--output", type=Path, default=Path("data/chirps/sample-2024-01-01"))
    parser.add_argument("--run", action="store_true", help="Acquire after a successful preview")
    parser.add_argument("--resume", action="store_true", help="Verify and resume a failed run in --output")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    options = parser.parse_args()
    if options.resume and not options.run:
        parser.error("--resume requires --run")
    if options.run and not options.worker:
        try:
            validate_bbox(tuple(options.bbox))
            if not options.resume:
                return run_isolated(options)
            directory = os.open(options.output, os.O_RDONLY | os.O_DIRECTORY)
            try:
                fcntl.flock(directory, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return run_isolated(options)
            finally:
                os.close(directory)
        except (OSError, ValueError) as error:
            print(f"CHIRPS stopped: {error}", file=sys.stderr)
            return 1
    budget = TransferBudget()
    before = 0
    cached = None
    remaining = []
    try:
        bbox = tuple(options.bbox)
        validate_bbox(bbox)
        dates = requested_days(options.start, options.end)
        if options.resume:
            before, cached = load_cache(options.output, bbox, options.start, options.end)
            budget.used = before
            print(f"Verified cached dates: {len(cached)}; previously transferred: {before:,} B", flush=True)
        remaining = dates[len(cached or []):]
        sources = plan(remaining[0], remaining[-1]) if remaining else []
        for source in sources:
            print(f"{source.day}  {source.size_bytes:>10,d} B  {source.url}", flush=True)
        upper_bound = sum(source.size_bytes for source in sources)
        print(f"Cumulative size upper bound: {before + upper_bound:,} B / {MAX_BYTES:,} B limit", flush=True)
        budget.require(upper_bound)
        if options.run:
            manifest = acquire(sources, bbox, options.output, budget, dates=dates, cached=cached)
            print(f"Validation {manifest['status']}. Manifest: {options.output / 'manifest.json'}")
    except (KeyError, OSError, ValueError, RuntimeError) as error:
        if cached is not None and budget.used == before:
            # In particular, retain verified assets when a resumed HEAD fails.
            path = options.output / "manifest.json"
            failed = json.loads(path.read_text(encoding="utf-8"))
            failed.update(status="failed", error=str(error),
                          start=options.start.isoformat(), end=options.end.isoformat(),
                          remaining_dates=[day.isoformat() for day in remaining])
            save_manifest(path, failed)
        print(f"CHIRPS stopped: {error}", file=sys.stderr)
        return 1
    finally:
        print(f"Raster response body bytes read this attempt: {budget.used - before:,}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
