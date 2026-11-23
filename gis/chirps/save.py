"""Persist native-grid inputs, validated subsets and the run manifest."""

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio

from .read import DayRaster


def save_day(path: Path, day: DayRaster) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".partial")
    try:
        with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
            with rasterio.open(
                temp, "w", driver="GTiff", height=day.values.shape[0],
                width=day.values.shape[1], count=1, dtype=day.values.dtype,
                crs=day.crs, transform=day.transform, nodata=day.nodata,
            ) as target:
                target.write(day.values.data, 1)
                target.write_mask(np.where(np.ma.getmaskarray(day.values), 0, 255).astype("uint8"))
                target.set_band_unit(1, "mm")
                target.update_tags(chirps_date=day.day.isoformat(), units=day.units)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)
    with path.open("rb") as content:
        return hashlib.file_digest(content, "sha256").hexdigest()


def save_manifest(path: Path, manifest: dict) -> None:
    temp = path.with_suffix(".partial")
    temp.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temp.replace(path)
