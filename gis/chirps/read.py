"""Read a geographic subset without changing native rainfall values or grid."""

from dataclasses import dataclass
from datetime import date
from io import RawIOBase
from math import ceil, floor, isclose, isfinite

import numpy as np
import rasterio
from affine import Affine
from rasterio.abc import FileContainer
from rasterio.crs import CRS
from rasterio.windows import Window, from_bounds

WGS84 = CRS.from_epsg(4326)
BBox = tuple[float, float, float, float]


@dataclass(frozen=True)
class DayRaster:
    day: date
    values: np.ma.MaskedArray
    crs: CRS
    transform: Affine
    nodata: float | None
    source_bounds: BBox
    units: str = "mm per labelled day"


class GdalRangeStream(RawIOBase):
    """Translate a latched range failure to EOF at the GDAL callback boundary."""

    def __init__(self, reader):
        super().__init__()
        self.reader = reader

    def readable(self):
        return True

    def seekable(self):
        return True

    def seek(self, offset, whence=0):
        return self.reader.seek(offset, whence)

    def tell(self):
        return self.reader.tell()

    def read(self, size=-1):
        try:
            return self.reader.read(size)
        except Exception as error:
            # RangeReader retains the original error for the Python caller.
            if error is not self.reader.error:
                raise
            return b""

    def readinto(self, buffer):
        data = self.read(len(buffer))
        buffer[:len(data)] = data
        return len(data)


class SingleRaster(FileContainer):
    """Expose one known-size TIFF to GDAL without probing sidecar URLs."""

    def __init__(self, filename, reader):
        self.filename = filename
        self.reader = reader

    def isfile(self, path):
        return path == self.filename

    def isdir(self, path):
        return False

    def ls(self, path):
        return []

    def size(self, path):
        if not self.isfile(path):
            raise FileNotFoundError(path)
        return self.reader.source.size_bytes

    def mtime(self, path):
        return 0

    def rm(self, path):
        raise PermissionError(path)

    def open(self, path, mode="rb"):
        if not self.isfile(path):
            raise FileNotFoundError(path)
        self.reader.seek(0)
        return GdalRangeStream(self.reader)


def validate_bbox(bbox: BBox) -> None:
    west, south, east, north = bbox
    if not (all(map(isfinite, bbox)) and -180 <= west < east <= 180
            and -60 <= south < north <= 60):
        raise ValueError("Expected west south east north within the CHIRPS domain")


def read_day(path, day: date, bbox: BBox, *, opener=None) -> DayRaster:
    validate_bbox(bbox)
    west, south, east, north = bbox
    with rasterio.open(path, opener=opener) as dataset:
        transform = dataset.transform
        if (dataset.driver != "GTiff" or dataset.count != 1 or dataset.crs != WGS84
                or transform.b or transform.d
                or not isclose(transform.a, 0.05, abs_tol=1e-9)
                or not isclose(transform.e, -0.05, abs_tol=1e-9)):
            raise ValueError("Expected a one-band north-up CHIRPS 0.05° WGS 84 TIFF")
        left, bottom, right, top = dataset.bounds
        if west < left or east > right or south < bottom or north > top:
            raise ValueError("Source raster does not cover the requested bounding box")
        window = from_bounds(*bbox, transform=transform)
        # Round grid coordinates before floor/ceil to avoid phantom edge cells.
        x0, y0 = floor(round(window.col_off, 9)), floor(round(window.row_off, 9))
        x1 = ceil(round(window.col_off + window.width, 9))
        y1 = ceil(round(window.row_off + window.height, 9))
        native = Window(x0, y0, x1 - x0, y1 - y0)
        values = dataset.read(1, window=native, masked=True)
        return DayRaster(day, values, dataset.crs, dataset.window_transform(native),
                         dataset.nodata, tuple(dataset.bounds))
