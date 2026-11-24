# TERRALERT — PostGIS integration

This contribution prepares the flood indicators for 11 communes of Tangier–Assilah for PostgreSQL 18 + PostGIS. It preserves an original source table and creates a smaller application-ready table with a spatial GiST index and lookup indexes.

## Files

- `TERRALERT_import_and_optimize.ps1`: the original local PowerShell importer; prompts for the PostgreSQL password securely, imports with QGIS `ogr2ogr`, builds the optimized table, and executes validation SQL.
- `data/commune_indicators_landcover.gpkg`: source GeoPackage for the importer (11 commune geometries, EPSG:26191).
- `data/commune_indicators_landcover.csv`: tabular snapshot (not used directly by the importer).

## Run on Windows

Requires PostgreSQL 18 with PostGIS enabled in a database named `TERRALERT`, QGIS 3.44.9, and the local PostgreSQL `postgres` user's password. The current script uses absolute paths for PostgreSQL, QGIS, and the source GeoPackage. **Before running it on another PC, edit the first three variables** (`$psql`, `$ogr`, `$gpkg`) to point to your local installation and this folder's `data/commune_indicators_landcover.gpkg`.

Run from PowerShell (in a terminal where local script execution is permitted):

```powershell
.\TERRALERT_import_and_optimize.ps1
```

The script deliberately refuses to run if `public.flood_commune_indicators_raw` or `public.flood_commune_indicators` already exists. **Do not drop production tables just to rerun the script.** It creates:

- `public.flood_commune_indicators_raw`: imported GeoPackage source attributes and geometry
- `public.flood_commune_indicators`: normalized names and selected columns, geometry, primary key, spatial index, name/code indexes

Validation commands at the end check row count, unique codes, CRS (EPSG:26191), geometric validity, indexes, and query performance.

## Quality and limitations

- The prior structural validation for `commune_indicators.gpkg` reported 11 communes, all valid geometries, no empty geometries, and EPSG:26191.
- The **later** `commune_indicators_landcover.csv` has 11 rows and nonempty `urban_pct`, `forest_pct`, and `veget_pct` values, unlike the earlier intermediate validation report. The corresponding classification of land-cover codes still needs independent scientific verification.
- Elevation units and mapped river density must not be interpreted as an independently verified flood probability.
- The database import and SQL validation were **not re-executed as part of this GitHub package preparation**, because the local PostgreSQL connection requires a password.
- GIS input rasters and processing intermediates are intentionally excluded. The GeoPackage and CSV contain geographic indicators, not credentials.

## Collaboration

Submit these files through a dedicated feature branch and pull request into `main`; do not overwrite unrelated team changes. Never commit a real `.env`, database dump with private information, or password.

## Shared Docker setup (Linux)

The integrated TERRALERT database uses PostgreSQL 17
and PostGIS 3.5 through Docker Compose.

### Requirements

- Docker and Docker Compose
- GDAL with PostgreSQL support
- A root .env file containing POSTGRES_PASSWORD

Install GDAL on Ubuntu:

    sudo apt install gdal-bin

Start the database from the repository root:

    docker compose up -d db

Once the database is healthy, initialize it:

    bash database/postgis/init_database.sh

Enter the configured PostgreSQL password when prompted.

### Integrated datasets

- communes: 11 official commune polygons
- rivers: 123 official river features
- flood_commune_indicators_raw: original GIS indicators
- flood_commune_indicators: optimized territorial indicators

All spatial tables use EPSG:26191.
The REST API transforms geometries to EPSG:4326.

Commune relationships use unique ISO codes.
Spatial GiST indexes support geographic queries.

### Available API endpoints

- GET /api/health
- GET /api/db-health
- GET /api/communes
- GET /api/rivers
- GET /api/flood/indicators

### Validation

Initialization was successfully tested on a separate
terralert_test database without modifying the working database.

The initializer refuses to overwrite existing target tables.
If initialization fails midway, inspect the imported tables
before attempting another import.

The flood indicators represent territorial characteristics,
not validated flood-risk predictions.

## Weather and multi-hazard schema

The integrated initializer now automatically applies:

    migrations/001_weather_hazards.sql

This migration creates five additional tables:

| Table | Purpose |
|---|---|
| weather_daily | Historical weather observations |
| weather_forecasts | Weather forecast snapshots |
| fire_detections | Satellite thermal detections |
| hazard_assessments | Scientific model results |
| hazard_alerts | Hazard alert history |

For existing compatible databases, apply only the migration
from the repository root:

    docker compose exec -T db psql \
      -U terralert -d terralert \
      -v ON_ERROR_STOP=1 \
      < database/postgis/migrations/001_weather_hazards.sql

Do not rerun the full GIS initializer on an existing database.

GIS initialization and the hazard migration use separate
transactions. If the migration fails after GIS initialization,
inspect the error and apply the migration separately.

### Validation performed on 2026-11-24

- Complete initialization tested on terralert_init_test.
- Migration reapplication successful.
- Operational database record counts preserved.
- 11 communes, 123 rivers and 11 flood indicator records.
- All five new tables created successfully.
- 47 runtime API checks passed.
- 5 operational database isolation checks passed.
- 8 reusable API smoke-test methods passed.

### Backend documentation and tests

See backend/README.md for endpoint documentation,
integration requirements and current limitations.

With the API running, execute from the repository root:

    python3 backend/tests/api_smoke.py

The schema supports scientific model integration but does
not itself calculate or validate hazard probabilities.

Automatic PostGIS ingestion remains pending.
