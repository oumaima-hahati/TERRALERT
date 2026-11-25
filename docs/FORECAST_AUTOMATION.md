# TERRALERT — Automated Forecast Pipeline

## Purpose

Automate provisional wildfire FWI forecasts for the 11 TERRALERT
study areas in Tanger–Assilah.

The pipeline:

1. Downloads Open-Meteo hourly forecasts.
2. Prepares recent and forecast FWI weather inputs.
3. Calculates provisional wildfire FWI.
4. Generates forecast GIS layers.
5. Validates outputs and records execution logs.

## Execution

Run manually:

    .venv/bin/python scripts/run_automated_forecast.py

The automatic schedule is 07:00 daily using a systemd user timer.

## Monitoring

Check the timer:

    systemctl --user list-timers terralert-forecast.timer

Check execution history:

    journalctl --user -u terralert-forecast.service -n 50 --no-pager

Execution reports are stored in:

    logs/forecast/

## Required inputs

- data/weather/locations/commune_coordinates.csv
- ~/Downloads/communes_11_fixed.gpkg
- Python virtual environment and dependencies
- Internet access to Open-Meteo

## Deployment

Reusable systemd unit files are in deploy/systemd/.

The templates assume the repository is installed at
~/Desktop/TERRALERT. Adjust the paths for other computers.

Copy the service and timer files to:

    ~/.config/systemd/user/

Then run:

    systemctl --user daemon-reload
    systemctl --user enable --now terralert-forecast.timer

If permitted, enable execution after logout:

    sudo loginctl enable-linger "$USER"

The computer must remain powered on and awake.

## Failure monitoring

The OnFailure systemd handler records local failure notifications.

These notifications are not emails, SMS messages or public alerts.

## Scientific limitations

FWI forecasts are provisional research outputs.

The hourly forecast downloader and operational FWI preparation
currently make separate Open-Meteo requests. Therefore, the
workflow does not use a single immutable weather snapshot.

Independent scientific validation and operational alert
authorization remain pending.

Public alerts are disabled.
