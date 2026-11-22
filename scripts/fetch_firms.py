
import os
import csv
import io
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

MAP_KEY = os.environ.get("FIRMS_MAP_KEY")

if not MAP_KEY:
    raise SystemExit("FIRMS_MAP_KEY is missing.")

# Approximate Tangier-area bounding box:
# west, south, east, north (longitude, latitude)
BBOX = "-6.25,35.45,-5.55,36.05"

SOURCE = "VIIRS_NOAA20_NRT"
DAYS = 1

url = (
    "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
    f"{MAP_KEY}/{SOURCE}/{BBOX}/{DAYS}"
)

output_dir = Path("data/wildfires/nrt")
output_dir.mkdir(parents=True, exist_ok=True)

print("Connecting to NASA FIRMS...")

try:
    with urlopen(url, timeout=60) as response:
        content = response.read().decode("utf-8-sig")

except (HTTPError, URLError) as error:
    raise SystemExit(f"FIRMS request failed: {error}")

reader = csv.DictReader(io.StringIO(content))
fields = reader.fieldnames or []

if not {"latitude", "longitude", "acq_date"}.issubset(fields):
    raise SystemExit(
        "Unexpected API response. Check your MAP_KEY "
        "and the FIRMS response."
    )

rows = list(reader)

timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

output_file = output_dir / f"firms_noaa20_{timestamp}.csv"
output_file.write_text(content, encoding="utf-8")

print(f"Success! Retrieved {len(rows)} fire detections.")
print(f"Saved to: {output_file}")
print("Note: These are thermal detections, not confirmed wildfires.")
