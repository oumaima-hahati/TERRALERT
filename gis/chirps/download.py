"""Plan and execute bounded HTTP range reads from the CHIRPS archive."""

from dataclasses import dataclass
from datetime import date, timedelta
from io import RawIOBase
from time import monotonic, sleep
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ARCHIVE = "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/rnl"
MAX_BYTES = 100_000_000
BLOCK_SIZE = 65_536
_last_request_started: float | None = None


def _request(request: Request, timeout: int):
    """Space requests across HEAD and range GET calls in this process."""
    global _last_request_started
    if _last_request_started is not None:
        delay = 1.1 - (monotonic() - _last_request_started)
        if delay > 0:
            sleep(delay)
    _last_request_started = monotonic()
    request.add_header("User-Agent", "TERRALERT-CHIRPS-sample/1.0")
    try:
        return urlopen(request, timeout=timeout)
    except HTTPError as error:
        if error.code == 429:
            retry_after = error.headers.get("Retry-After") if error.headers else None
            error.close()
            guidance = f"Retry-After: {retry_after}" if retry_after else "No Retry-After header supplied."
            raise OSError(f"UCSB returned HTTP 429. {guidance}") from error
        error.close()
        raise


@dataclass(frozen=True)
class Source:
    day: date
    url: str
    size_bytes: int
    revision: tuple[str, str] | None


@dataclass
class TransferBudget:
    limit: int = MAX_BYTES
    used: int = 0

    def require(self, size: int) -> None:
        if size < 0 or self.used + size > self.limit:
            raise ValueError("Download would exceed the remaining transfer budget")


def plan(start: date, end: date) -> list[Source]:
    count = (end - start).days + 1
    if not 1 <= count <= 7:
        raise ValueError("This sample supports one through seven consecutive dates")
    sources = []
    for index in range(count):
        day = start + timedelta(days=index)
        url = f"{ARCHIVE}/{day:%Y}/chirps-v3.0.rnl.{day:%Y.%m.%d}.tif"
        with _request(Request(url, method="HEAD"), timeout=20) as response:
            if response.status != 200 or response.geturl() != url:
                raise ValueError(f"Unexpected HEAD response for {url}")
            if response.headers.get_content_type() not in {"image/tiff", "image/geotiff"}:
                raise ValueError(f"Expected a TIFF at {url}")
            if response.headers.get("Accept-Ranges", "").lower() != "bytes":
                raise ValueError(f"Server does not advertise byte ranges for {url}")
            size = int(response.headers.get("Content-Length", "0"))
            if size <= 0:
                raise ValueError(f"Missing or invalid Content-Length for {url}")
            etag = response.headers.get("ETag", "")
            modified = response.headers.get("Last-Modified")
            revision = ("ETag", etag) if etag and not etag.startswith("W/") else (
                ("Last-Modified", modified) if modified else None
            )
            sources.append(Source(day, url, size, revision))
    return sources


class RangeReader(RawIOBase):
    """Seekable, block-cached input for GDAL's Python file opener."""

    def __init__(self, source: Source, budget: TransferBudget):
        super().__init__()
        self.source = source
        self.budget = budget
        self.position = 0
        self.blocks: dict[int, bytes] = {}
        self.error: Exception | None = None
        self.fetched = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        base = {0: 0, 1: self.position, 2: self.source.size_bytes}[whence]
        if base + offset < 0:
            raise ValueError("Negative file position")
        self.position = base + offset
        return self.position

    def _fetch(self, start):
        end = min(start + BLOCK_SIZE, self.source.size_bytes) - 1
        size = end - start + 1
        if self.fetched + size >= self.source.size_bytes:
            raise IOError("Window read would require the complete source raster")
        self.budget.require(size)
        headers = {"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"}
        if self.source.revision:
            headers["If-Range"] = self.source.revision[1]
        request = Request(self.source.url, headers=headers)
        with _request(request, timeout=30) as response:
            expected = f"bytes {start}-{end}/{self.source.size_bytes}"
            if (response.status != 206 or response.geturl() != self.source.url
                    or response.headers.get("Content-Range") != expected
                    or response.headers.get("Content-Length") != str(size)
                    or response.headers.get("Content-Encoding", "identity") != "identity"):
                raise IOError(f"Server did not honor the exact byte range for {self.source.url}")
            if self.source.revision:
                field, value = self.source.revision
                if response.headers.get(field) != value:
                    raise IOError(f"Source revision changed for {self.source.url}")
            payload = bytearray()
            while len(payload) < size:
                chunk = response.read(min(16_384, size - len(payload)))
                if not chunk:
                    raise IOError(f"Truncated range for {self.source.url}")
                self.budget.used += len(chunk)
                payload.extend(chunk)
        self.fetched += size
        return bytes(payload)

    def read(self, size=-1):
        if self.error is not None:
            raise self.error
        remaining = max(0, self.source.size_bytes - self.position)
        size = remaining if size is None or size < 0 else min(size, remaining)
        result = bytearray()
        try:
            while len(result) < size:
                start = self.position // BLOCK_SIZE * BLOCK_SIZE
                if start not in self.blocks:
                    self.blocks[start] = self._fetch(start)
                offset = self.position - start
                chunk = self.blocks[start][offset:offset + size - len(result)]
                result.extend(chunk)
                self.position += len(chunk)
        except Exception as error:
            self.error = error
            raise
        return bytes(result)

    def readinto(self, buffer):
        data = self.read(len(buffer))
        buffer[:len(data)] = data
        return len(data)
