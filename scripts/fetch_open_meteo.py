
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

# Initial test location: Tangier, Morocco
LATITUDE = 35.76
LONGITUDE = -5.83

API_URL = "https://api.open-meteo.com/v1/forecast"

params = {
    "latitude": LATITUDE,
    "longitude": LONGITUDE,
    "hourly": ",".join([
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "wind_speed_10m",
        "wind_direction_10m",
    ]),
    "forecast_days": 7,
    "timezone": "UTC",
}

url = API_URL + "?" + urlencode(params)

print("Connecting to Open-Meteo...")

try:
    with urlopen(url, timeout=30) as response:
        data = json.load(response)

    if "hourly" not in data:
        raise ValueError("Hourly forecast data missing")

    hourly = data["hourly"]
    count = len(hourly["time"])

    output_dir = Path("data/weather/forecasts")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )

    output_file = (
        output_dir / f"open_meteo_tangier_{timestamp}.json"
    )

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    print("Open-Meteo connection successful!")
    print(f"Forecast hours retrieved: {count}")
    print(f"Saved to: {output_file}")

except Exception as error:
    print(f"Open-Meteo request failed: {error}")
    raise SystemExit(1)
