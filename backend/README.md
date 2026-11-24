# TERRALERT Backend API

FastAPI REST API connected to PostgreSQL 17 and PostGIS 3.5.

## 1. Start the backend

From the repository root:

    docker compose up -d db
    cd backend
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

Configure DATABASE_URL in backend/.env using your
local PostgreSQL credentials.

Never commit real credentials.

Start the API:

    uvicorn app.main:app --host 127.0.0.1 --port 8000

Swagger documentation:

    http://localhost:8000/docs

## 2. Core endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /api/health | API health |
| GET | /api/db-health | PostGIS connectivity |
| GET | /api/communes | Official commune boundaries |
| GET | /api/rivers | River network |
| GET | /api/flood/indicators | Territorial flood indicators |

GIS endpoints return GeoJSON in EPSG:4326.

The official GIS datasets contain:
- 11 communes
- 123 river features
- 11 commune-level flood indicator records

## 3. Weather and hazard endpoints

All endpoints are read-only.

### GET /api/weather/history

Historical daily weather observations.

Filters:
- commune_code
- start_date
- end_date
- source
- limit
- offset

Dates use YYYY-MM-DD.

### GET /api/weather/forecasts

Weather forecast records.

Filters:
- commune_code
- start_time
- end_time
- latest_only (default: true)
- limit
- offset

The latest snapshot is selected by commune, source
and model.

Use latest_only=false to retrieve older snapshots.

The endpoint does not automatically exclude past hours.

### GET /api/fires

Satellite thermal detections as GeoJSON points.

Filters:
- commune_code
- start_time
- end_time
- limit
- offset

Thermal detections are not confirmed wildfires.

### GET /api/hazards

Historical and current hazard assessment records.

Filters:
- commune_code
- hazard_type
- assessment_type
- start_time
- end_time
- limit
- offset

### GET /api/hazards/latest

Latest applicable hazard assessments.

Filters:
- commune_code
- hazard_type
- assessment_type (default: current)
- at (default: current UTC time)

Results are selected by commune, hazard, model
and model version.

### GET /api/alerts

Stored hazard alerts.

Filters:
- commune_code
- hazard_type
- status
- limit
- offset

Supported statuses:
- active
- resolved
- expired

Expired active alerts are treated as expired
when returned by the API.

## 4. API conventions

Datetime parameters must include a timezone.
UTC is recommended.

Paginated JSON endpoints return:
- count: number of returned records
- limit
- offset
- data

Count is the page size, not the total database count.

Default limit: 1000 records.
Alerts default limit: 100 records.
Maximum limit: 10000 records.

Spatial endpoints return GeoJSON FeatureCollections.

Invalid parameters return HTTP 422.
Database connection failures can return HTTP 503.

Empty datasets are valid responses.

## 5. Database integration

All commune relationships use communes.iso.

New tables:
- weather_daily
- weather_forecasts
- fire_detections
- hazard_assessments
- hazard_alerts

Schema:

    database/postgis/migrations/001_weather_hazards.sql

For a new database, use the integrated initializer.

For an existing compatible database, apply only
the migration from the repository root:

    docker compose exec -T db psql \
      -U terralert -d terralert \
      -v ON_ERROR_STOP=1 \
      < database/postgis/migrations/001_weather_hazards.sql

Do not rerun the GIS initializer on an existing
operational database.

## 6. Scientific model integration contract

Supported hazards:
- flood
- wildfire
- heatwave
- coldwave

Supported assessment types:
- susceptibility
- historical
- current
- forecast

Proposed normalized risk score: 0 to 100.

Proposed risk levels:
- very_low
- low
- moderate
- high
- very_high

These conventions require agreement with the
scientific model owners.

No scientific thresholds are defined by the API.

Every assessment should include:
- commune_code
- hazard_type
- assessment_type
- model_name
- model_version
- generated_at
- valid_from
- valid_until, when applicable
- validation_status
- indicators and metadata

Validation statuses:
- unvalidated
- provisional
- validated

Missing results must not be interpreted as zero risk.

Alerts are research prototype outputs, not official
civil protection warnings.

## 7. Team integration responsibilities

Amrou:
- GIS and flood indicators
- Flood susceptibility and risk model results
- Sentinel-2 processing

Kawtar:
- Historical weather observations
- Weather forecasts
- Heatwave and cold-wave model results

Oumaima:
- NASA FIRMS ingestion
- Wildfire model results
- Automated collection pipeline validation

Rayane:
- Database schema and API integration
- Frontend integration
- Platform-level testing and deployment

Scientific processing remains with the assigned
model owners.

## 8. Validation performed on 2026-11-24

- 47 runtime API checks passed.
- 5 operational database isolation checks passed.
- Fresh database initialization passed.
- Migration reapplication passed.
- Official GIS record counts preserved.
- Synthetic hazard records tested in an isolated database.
- Open-Meteo returned 168 hourly forecast timestamps.
- NASA FIRMS returned a valid empty detection snapshot.
- Both collection services passed a temporary timer test.

Synthetic test records are not operational observations.

## 9. Current limitations

- Automatic collection currently saves local JSON/CSV files.
- Automatic PostGIS ingestion is not yet implemented.
- Open-Meteo collection currently uses one Tangier location.
- FIRMS collection uses a broad bounding box.
- Exact commune-level FIRMS assignment remains pending.
- Permanent six-hour execution cycles require observation.
- Provider data freshness requires further verification.
- Scientific model calibration and validation remain pending.
- Automatic alert generation is not implemented.
- Dashboard live updates remain pending.
- Production authentication and hosting remain pending.

Local timers depend on the host and systemd user
manager being available.

No credentials, raw downloads or synthetic test
records should be committed.

## 10. Reusable API smoke tests

With the backend running, execute from the repository root:

    python3 backend/tests/api_smoke.py

To test another API instance:

    TERRALERT_API_URL=http://127.0.0.1:8001 \
      python3 backend/tests/api_smoke.py

The suite performs read-only requests and covers all
11 endpoints, pagination, filters and invalid parameters.

All 8 test methods passed on 2026-11-24.

These smoke tests do not replace populated-data integration
tests or scientific model validation.
