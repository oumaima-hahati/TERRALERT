from dataclasses import replace
from datetime import date, timedelta
from email.message import Message
from io import BytesIO
from urllib.error import HTTPError
from urllib.request import Request

import numpy as np
import pytest
import rasterio
from affine import Affine
from rasterio.transform import from_origin

from gis.chirps import download
from gis.chirps.read import DayRaster, SingleRaster, WGS84, read_day
from gis.chirps.save import save_day
from gis.chirps.validate import validate_series

START = date(2024, 1, 1)
END = date(2024, 1, 7)
BBOX = (-5.95, 35.60, -5.80, 35.75)
GRID = from_origin(-5.95, 35.75, 0.05, 0.05)


@pytest.fixture
def series():
    return [
        DayRaster(START + timedelta(days=i),
                  np.ma.array([[0, i, 2], [1, -9999, 3], [0, 4, 0]],
                              mask=[[0, 0, 0], [0, 1, 0], [0, 0, 0]], dtype="float32"),
                  WGS84, GRID, -9999, BBOX)
        for i in range(7)
    ]


def test_valid_series_and_nodata(series):
    report = validate_series(series, START, END, BBOX)
    assert report["dimensions"] == {"width": 3, "height": 3}
    assert report["consistent_grid"]
    assert [day["missing_cells"] for day in report["daily"]] == [1] * 7
    assert [day["min_mm"] for day in report["daily"]] == [0] * 7


@pytest.mark.parametrize("mode", ["missing", "duplicate", "out_of_order"])
def test_invalid_date_sequence(series, mode):
    if mode == "missing":
        series.pop()
    elif mode == "duplicate":
        series[1] = series[0]
    else:
        series.reverse()
    with pytest.raises(ValueError, match="date order"):
        validate_series(series, START, END, BBOX)


def test_shifted_grid(series):
    series[1] = replace(series[1], transform=GRID @ Affine.translation(1, 0))
    with pytest.raises(ValueError, match="grid"):
        validate_series(series, START, END, BBOX)


@pytest.mark.parametrize("bbox, message", [
    ((-5.80, 35.60, -5.95, 35.75), "west south east north"),
    ((-4, 35.60, -3, 35.75), "does not cover"),
])
def test_invalid_bbox(series, bbox, message):
    with pytest.raises(ValueError, match=message):
        validate_series(series, START, END, bbox)


@pytest.mark.parametrize("value", [-0.5, np.nan])
def test_invalid_unmasked_values(series, value):
    series[0].values[0, 0] = value
    with pytest.raises(ValueError, match="Nonfinite or negative"):
        validate_series(series, START, END, BBOX)


def test_all_missing(series):
    series[0].values.mask[:] = True
    with pytest.raises(ValueError, match="All cells masked"):
        validate_series(series, START, END, BBOX)


def test_round_trip_crop_preserves_native_grid(tmp_path, series):
    path = tmp_path / "sample.tif"
    assert len(save_day(path, series[0])) == 64
    day = read_day(path, START, (-5.90, 35.65, -5.80, 35.75))
    assert day.values.shape == (2, 2)
    assert day.transform.almost_equals(GRID @ Affine.translation(1, 0))
    assert day.values.mask.tolist() == [[False, False], [True, False]]
    with rasterio.open(path) as dataset:
        assert dataset.units == ("mm",)


class Response(BytesIO):
    def __init__(self, source, status):
        super().__init__(b"X" * download.BLOCK_SIZE)
        self.status = status
        self.url = source.url
        self.headers = Message()
        self.headers["Content-Range"] = f"bytes 0-{download.BLOCK_SIZE - 1}/{source.size_bytes}"
        self.headers["Content-Length"] = str(download.BLOCK_SIZE)

    def geturl(self):
        return self.url


@pytest.mark.parametrize("status", [200, 206])
def test_range_only_and_cache(monkeypatch, status):
    source = download.Source(START, "https://example.test/day.tif", 200_000, None)
    budget = download.TransferBudget(download.BLOCK_SIZE)

    def request(req, timeout):
        assert req.get_header("Range") == "bytes=0-65535"
        return Response(source, status)

    monkeypatch.setattr(download, "_request", request)
    with download.RangeReader(source, budget) as reader:
        if status == 200:
            with pytest.raises(OSError, match="exact byte range"):
                reader.read(1)
            assert budget.used == 0
            with pytest.raises(OSError, match="exact byte range"):
                reader.read(1)
        else:
            assert reader.read(4) == b"XXXX"
            reader.seek(0)
            assert reader.read(1) == b"X"
            reader.seek(download.BLOCK_SIZE)
            with pytest.raises(ValueError, match="budget"):
                reader.read(1)
            assert budget.used == download.BLOCK_SIZE


def test_window_through_gdal_opener(tmp_path, monkeypatch, series):
    path = tmp_path / "sample.tif"
    save_day(path, series[0])
    payload = path.read_bytes() + bytes(4096)
    source = download.Source(START, "https://example.test/sample.tif", len(payload), None)
    budget = download.TransferBudget(4096)
    monkeypatch.setattr(download, "BLOCK_SIZE", 128)

    def request(req, timeout):
        left, right = map(int, req.get_header("Range").removeprefix("bytes=").split("-"))
        response = Response(source, 206)
        response.headers.replace_header("Content-Range", f"bytes {left}-{right}/{len(payload)}")
        response.headers.replace_header("Content-Length", str(right - left + 1))
        response.seek(0)
        response.truncate(0)
        response.write(payload[left:right + 1])
        response.seek(0)
        return response

    monkeypatch.setattr(download, "_request", request)
    with download.RangeReader(source, budget) as reader:
        day = read_day(path.name, START, BBOX, opener=SingleRaster(path.name, reader))
    assert np.ma.allequal(day.values, series[0].values)
    assert np.array_equal(day.values.mask, series[0].values.mask)
    assert 0 < budget.used < len(payload)



def test_provider_throttle_stops_requests(monkeypatch):
    waits = []
    times = iter([3.0, 4.0])
    calls = []
    monkeypatch.setattr(download, "_last_request_started", 2.75)
    monkeypatch.setattr(download, "monotonic", lambda: next(times))
    monkeypatch.setattr(download, "sleep", waits.append)

    def rate_limited(request, timeout):
        calls.append(request)
        raise HTTPError(request.full_url, 429, "rate limited", {"Retry-After": "120"}, BytesIO())

    monkeypatch.setattr(download, "urlopen", rate_limited)
    with pytest.raises(OSError, match="HTTP 429.*Retry-After: 120"):
        download._request(Request("https://example.test"), timeout=3)
    assert waits == [pytest.approx(0.85)]
    assert len(calls) == 1


@pytest.mark.parametrize("failure", ["429", "truncated", "200"])
def test_metadata_range_failure_in_subprocess(tmp_path, failure):
    import subprocess
    import sys
    from textwrap import dedent

    result = subprocess.run(
        [sys.executable, "-X", "faulthandler", "-c", dedent('''
            import json
            import resource
            import socket
            import sys
            from datetime import date
            from email.message import Message
            from io import BytesIO
            from pathlib import Path
            from urllib.error import HTTPError

            import numpy as np
            import rasterio
            from affine import Affine
            from gis.chirps import download
            from gis.chirps.__main__ import acquire

            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

            def offline(*args, **kwargs):
                raise AssertionError("unexpected network request")

            socket.socket.connect = offline
            failure, root = sys.argv[1], Path(sys.argv[2])
            path = root / "source.tif"
            # One row per strip puts the strip offset/count tables across
            # multiple 4 KiB blocks, so call two fails during metadata reads.
            with rasterio.open(
                path, "w", driver="GTiff", width=64, height=2400, count=1,
                dtype="float32", crs="EPSG:4326", nodata=-9999,
                transform=Affine(.05, 0, -7, 0, -.05, 60),
                blockysize=1, compress="deflate",
            ) as dataset:
                dataset.write(np.zeros((2400, 64), dtype="float32"), 1)
            payload = path.read_bytes()
            day = date(2024, 1, 1)
            source = download.Source(day, "https://example.test/source.tif", len(payload), None)
            download.BLOCK_SIZE = 4096
            calls = []

            class Response(BytesIO):
                def geturl(self):
                    return source.url

            def fake_urlopen(request, timeout):
                first, last = map(int, request.get_header("Range")[6:].split("-"))
                calls.append((first, last))
                assert len(calls) <= 2
                if len(calls) == 2 and failure == "429":
                    raise HTTPError(source.url, 429, "rate limited",
                                    {"Retry-After": "120"}, BytesIO())
                body = payload[first:last + 1]
                if len(calls) == 2 and failure == "truncated":
                    body = body[:-5]
                response = Response(body)
                response.status = 200 if len(calls) == 2 and failure == "200" else 206
                response.headers = Message()
                response.headers["Content-Range"] = f"bytes {first}-{last}/{len(payload)}"
                response.headers["Content-Length"] = str(last - first + 1)
                return response

            download.urlopen = fake_urlopen
            download.sleep = lambda _: None
            expected = {
                "429": "HTTP 429. Retry-After: 120",
                "truncated": "Truncated range",
                "200": "did not honor the exact byte range",
            }[failure]
            output = root / "run"
            try:
                acquire([source], (-5.95, 35.60, -5.65, 35.85), output,
                        download.TransferBudget())
            except OSError as error:
                assert expected in str(error), repr(error)
            else:
                raise AssertionError("expected original transport failure")
            assert len(calls) == 2, calls
            report = json.loads((output / "manifest.json").read_text())
            assert report["status"] == "failed" and expected in report["error"], report
            assert report["body_bytes_transferred"] == (8187 if failure == "truncated" else 4096)
            assert not list(output.rglob("*.tif"))
        '''), failure, str(tmp_path)],
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "SystemError" not in result.stderr, result.stderr
    assert "Exception ignored" not in result.stderr, result.stderr


@pytest.fixture
def interrupted_run(tmp_path, monkeypatch, series):
    import json

    from gis.chirps import __main__ as cli

    sources = []
    for raster in series:
        url = (f"{download.ARCHIVE}/{raster.day:%Y}/"
               f"chirps-v3.0.rnl.{raster.day:%Y.%m.%d}.tif")
        sources.append(download.Source(raster.day, url, 200_000, None))

    out = tmp_path / "run"
    original_read = cli.read_day

    def mock_read(filename, day, bbox, *, opener=None):
        if opener is None:
            return original_read(filename, day, bbox)
        index = (day - START).days
        if index == 4:
            raise OSError("simulated HTTP 429")
        opener.reader.budget.used += 100
        return series[index]

    monkeypatch.setattr(cli, "read_day", mock_read)
    with pytest.raises(OSError, match="HTTP 429"):
        cli.acquire(sources, BBOX, out, download.TransferBudget())
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["body_bytes_transferred"] == 400
    assert manifest["remaining_dates"] == ["2024-01-05", "2024-01-06", "2024-01-07"]
    return cli, out, sources


@pytest.mark.parametrize("fail_again", [False, True])
def test_resume_only_missing_dates(interrupted_run, monkeypatch, series, fail_again):
    import json
    import sys

    cli, out, sources = interrupted_run
    cached = {path: path.read_bytes() for path in (out / "raw").glob("*.tif")}
    planned = []
    reads = []

    def fake_plan(start, end):
        planned.append((start, end))
        return sources[4:]

    def fake_read(filename, day, bbox, *, opener):
        reads.append(day)
        if fail_again and day == date(2024, 1, 6):
            raise OSError("simulated HTTP 429")
        opener.reader.budget.used += 100
        return series[(day - START).days]

    monkeypatch.setattr(cli, "plan", fake_plan)
    monkeypatch.setattr(cli, "read_day", fake_read)
    monkeypatch.setattr(sys, "argv", [
        "chirps", "--output", str(out), "--bbox", *map(str, BBOX), "--run", "--resume", "--worker",
    ])
    assert cli.main() == int(fail_again)
    assert planned == [(date(2024, 1, 5), END)]
    assert reads == [source.day for source in sources[4:6 if fail_again else 7]]
    assert all(p.read_bytes() == contents for p, contents in cached.items())
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["body_bytes_transferred"] == (500 if fail_again else 700)
    assert manifest["remaining_dates"] == (["2024-01-06", "2024-01-07"] if fail_again else [])
    assert manifest["status"] == ("failed" if fail_again else "passed")
    assert len(list((out / "processed").glob("*.tif"))) == (0 if fail_again else 7)


def test_resume_rejects_corrupted_cache_before_network(interrupted_run, monkeypatch, capsys):
    import sys

    cli, out, _ = interrupted_run
    manifest = (out / "manifest.json").read_bytes()
    raw = out / "raw/chirps-v3.0.rnl.2024.01.01.tif"
    raw.write_bytes(raw.read_bytes() + b"corruption")

    def no_plan(*args):
        pytest.fail("The resume path attempted a network preflight")

    monkeypatch.setattr(cli, "plan", no_plan)
    monkeypatch.setattr(sys, "argv", [
        "chirps", "--output", str(out), "--bbox", *map(str, BBOX), "--run", "--resume", "--worker",
    ])
    assert cli.main() == 1
    assert "Cached checksum mismatch for 2024-01-01" in capsys.readouterr().err
    assert (out / "manifest.json").read_bytes() == manifest
