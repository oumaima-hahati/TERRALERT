# CHIRPS daily rainfall sample for Tangier

This pipeline targets 1–7 January 2024 from the [UCSB CHIRPS v3.0 Final daily rnl archive](https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/). The product uses 0.05° cells. Values are millimetres of precipitation per labelled day. Dates follow the UTC convention used to distribute pentad totals among days. Station reporting windows may differ. See the [UCSB daily product notes](https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/readme.txt).

The provisional Tangier test box is `(-5.95, 35.60, -5.65, 35.85)` in WGS 84 (EPSG:4326), ordered west, south, east, north. An approved Tangier boundary and documented analysis CRS are required before production clipping or reporting coverage by commune.

## Validation status

The raw windows for **1–4 January 2024** passed checks for CRS, bounds, grid alignment, resolution, rainfall values, and missingness. The four windows share a 7 × 6 grid at 0.05° spacing. Each has 42 valid cells and zero masked cells.

**5–7 January 2024 are pending.** UCSB returned HTTP 429 on 5 January during the first run and again during resume preflight. Both attempts stopped without retrying. The cumulative transfer was 782,904 raster bytes. Full-series validation and processed outputs remain pending. Live acquisition is paused.

## Install and test

From the repository root, using Python 3.11 or later on Linux or macOS:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r gis/chirps/requirements.txt
python -m pytest -q -p no:cacheprovider
```

## Start a new run

Use these commands when live acquisition resumes. The first previews source sizes. The second acquires the sample in an isolated worker.

```sh
python -m gis.chirps --start 2024-01-01 --end 2024-01-07 --bbox -5.95 35.60 -5.65 35.85
python -m gis.chirps --start 2024-01-01 --end 2024-01-07 --bbox -5.95 35.60 -5.65 35.85 --run
```

The preview issues metadata-only HTTP HEAD requests and lists the seven URLs and full-file sizes. The same checks run before acquisition. The full-file size sum is a conservative preflight upper bound. If it exceeds 100,000,000 bytes, the run stops before raster acquisition. For this test, the reader sends bounded byte ranges, verifies HTTP 206 and exact range headers, and enforces the same cap on total raster response body bytes. A server that ignores ranges or an operation that requires recovering a complete global file causes the run to stop. Counts exclude HTTP headers and transport overhead. The client spaces requests by at least 1.1 seconds. Run one instance at a time and wait for any HTTP 429 limit to clear before rerunning. [UCSB download guidance](https://github.com/chc-ucsb/chc-data-download#downloading-politely)

A new run requires a fresh output directory. Use `--output` to select one. The default lives under the Git-ignored `data/chirps/` directory:

```text
data/chirps/sample-2024-01-01/
  raw/          native-grid windows with original pixel values and masks
  processed/    daily GeoTIFFs written after the series passes validation
  manifest.json source, timing, extent, checksums, transferred bytes and QA
```

Raw files preserve the extracted inputs. They are window GeoTIFFs generated locally, with source URLs and source revision metadata in the manifest. A failed run retains any saved raw windows and records its error and transferred bytes. The QA report counts masked cells and changes relative to the first day. Stable coastal missingness is compatible with a land rainfall product, but attribution to ocean or other causes requires a separate mask check. Negative or nonfinite unmasked values and entirely missing days fail validation.

With an approved Tangier polygon, intersect the native grid cells with the polygon and weight each valid rainfall depth by its intersection area. Record the valid area fraction and any coverage flags with the daily mean in millimetres. Use an area-appropriate projection or geodesic area calculation for the weights. The CHIRPS dates and grid spacing carry through to those summaries.

## Resume an interrupted run

Pass `--resume --run` with the original date range, bounding box, and output directory. The worker checks the cached dates, provenance, file checksums, and raster grid before issuing requests for the remaining dates. Resume uses the original 100 MB cumulative cap, including bytes transferred before the interruption. A checksum or metadata mismatch stops the run. An unmeasured native crash also stops automatic resume because cumulative transfer cannot be verified.

```sh
python -m gis.chirps --start 2024-01-01 --end 2024-01-07 \
  --bbox -5.95 35.60 -5.65 35.85 \
  --output data/chirps/validation-2024-01-01-to-07 --resume --run
```

The manifest checkpoints each validated raw window and records `remaining_dates`. An interrupted resume preserves existing raw windows. Processed outputs are generated once the complete series passes validation.
