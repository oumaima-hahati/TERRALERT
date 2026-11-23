"""Verify an interrupted run's native-grid cache before using it."""

from datetime import date, datetime, timedelta
from hashlib import file_digest
import json
from math import isfinite
from pathlib import Path

import rasterio

from .download import ARCHIVE, MAX_BYTES
from .read import read_day
from .validate import validate_series


def requested_days(start, end):
    count = (end - start).days + 1
    if not 1 <= count <= 7:
        raise ValueError("This sample supports one through seven consecutive dates")
    return [start + timedelta(days=i) for i in range(count)]


def load_cache(output: Path, bbox, start, end):
    dates = requested_days(start, end)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    if (manifest.get("status") != "failed"
            or manifest.get("product") != "CHIRPS v3.0 Final daily rnl"
            or manifest.get("requested_bounds_wgs84_wsen") != list(bbox)
            or manifest.get("limit_bytes") != MAX_BYTES
            or manifest.get("transfer_unmeasured")
            or manifest.get("start", start.isoformat()) != start.isoformat()
            or manifest.get("end", end.isoformat()) != end.isoformat()):
        raise ValueError("Resume requires a compatible failed CHIRPS run with measurable transfers")
    used = manifest.get("body_bytes_transferred")
    entries = manifest.get("sources", [])
    recorded = [s["date"] for s in entries]
    if (type(used) is not int or not 0 <= used <= MAX_BYTES
            or recorded != [d.isoformat() for d in dates[:len(recorded)]]):
        raise ValueError("Invalid cached dates or cumulative transfer total")

    verified = []
    for entry in entries:
        if "raw_subset" not in entry:
            if entry is not entries[-1]:
                raise ValueError("Interrupted cache is not a chronological prefix")
            break
        day = date.fromisoformat(entry["date"])
        filename = f"chirps-v3.0.rnl.{day:%Y.%m.%d}.tif"
        relative = Path("raw") / filename
        path = output / relative
        if (entry["raw_subset"] != relative.as_posix()
                or entry["url"] != f"{ARCHIVE}/{day:%Y}/{filename}"
                or entry["units"] != "mm per labelled day"
                or datetime.fromisoformat(entry["acquired_at_utc"]).utcoffset() != timedelta(0)):
            raise ValueError(f"Unexpected cached provenance for {day}")
        with path.open("rb") as content:
            if file_digest(content, "sha256").hexdigest() != entry["raw_subset_sha256"]:
                raise ValueError(f"Cached checksum mismatch for {day}")
        with rasterio.open(path) as dataset:
            transform, shape = dataset.transform, dataset.shape
            nodata = dataset.nodata
            if nodata is not None and not isfinite(nodata):
                nodata = str(nodata)
            if (dataset.tags().get("chirps_date") != day.isoformat()
                    or dataset.tags().get("units") != entry["units"]
                    or dataset.units != ("mm",) or nodata != entry["source_nodata"]):
                raise ValueError(f"Cached raster metadata mismatch for {day}")
        raster = read_day(path, day, bbox)
        if not raster.transform.almost_equals(transform, precision=1e-9) or raster.values.shape != shape:
            raise ValueError(f"Cached raster has an unexpected window for {day}")
        verified.append((entry, raster))

    if verified:
        validate_series([raster for _, raster in verified], start, verified[-1][1].day, bbox)
    cached_paths = {entry["raw_subset"] for entry, _ in verified}
    if {p.relative_to(output).as_posix() for p in (output / "raw").glob("*.tif")} != cached_paths:
        raise ValueError("Unrecorded raw raster present; refusing to overwrite the cache")
    return used, verified
