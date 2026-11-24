"""Validate daily labels and native grids; report all masked values."""

from datetime import date, timedelta
from math import isclose

import numpy as np
from rasterio.transform import array_bounds

from .read import BBox, DayRaster, WGS84, validate_bbox


def validate_series(days: list[DayRaster], start: date, end: date, bbox: BBox) -> dict:
    validate_bbox(bbox)
    expected = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    if not days or [day.day for day in days] != expected:
        raise ValueError("Expected exactly one raster per requested day, in date order")
    first = days[0]
    reference_mask = np.ma.getmaskarray(first.values)
    daily = []
    for day in days:
        if (day.crs != WGS84 or day.values.shape != first.values.shape
                or not day.transform.almost_equals(first.transform, precision=1e-9)
                or day.transform.b or day.transform.d
                or not isclose(day.transform.a, 0.05, abs_tol=1e-9)
                or not isclose(day.transform.e, -0.05, abs_tol=1e-9)):
            raise ValueError(f"Inconsistent or invalid CHIRPS grid on {day.day}")
        bounds = array_bounds(*day.values.shape, day.transform)
        west, south, east, north = bbox
        tolerance = 1e-9
        if (bounds[0] > west + tolerance or bounds[1] > south + tolerance
                or bounds[2] < east - tolerance or bounds[3] < north - tolerance):
            raise ValueError(f"Subset does not cover the requested bounding box on {day.day}")
        valid = day.values.compressed()
        if not valid.size:
            raise ValueError(f"All cells masked on {day.day}")
        if not np.all(np.isfinite(valid)) or np.any(valid < 0):
            raise ValueError(f"Nonfinite or negative unmasked precipitation on {day.day}")
        mask = np.ma.getmaskarray(day.values)
        daily.append({
            "date": day.day.isoformat(),
            "missing_cells": int(mask.sum()),
            "valid_cells": int(valid.size),
            "missing_fraction": float(mask.mean()),
            "mask_changes_from_first_day": int(np.count_nonzero(mask != reference_mask)),
            "min_mm": float(valid.min()),
            "max_mm": float(valid.max()),
        })
    return {
        "dimensions": {"width": first.values.shape[1], "height": first.values.shape[0]},
        "resolution_degrees": [first.transform.a, -first.transform.e],
        "crs": first.crs.to_string(),
        "units": first.units,
        "actual_bounds": list(array_bounds(*first.values.shape, first.transform)),
        "consistent_grid": True,
        "daily": daily,
    }
