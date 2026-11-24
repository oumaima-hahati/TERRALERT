#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

DB_NAME="${1:-terralert}"

if [[ ! "$DB_NAME" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
    echo "Invalid database name."
    exit 1
fi

command -v ogr2ogr >/dev/null || {
    echo "Install GDAL: sudo apt install gdal-bin"
    exit 1
}

sql() {
    docker compose exec -T db psql \
        -v ON_ERROR_STOP=1 \
        -U terralert -d "$DB_NAME" "$@"
}

sql -c "CREATE EXTENSION IF NOT EXISTS postgis;"

existing=$(sql -Atc "
SELECT COUNT(*)
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN (
    'communes',
    'rivers',
    'flood_commune_indicators_raw',
    'flood_commune_indicators'
);")

if [ "$existing" != "0" ]; then
    echo "Target tables already exist. Import cancelled."
    exit 1
fi

read -rsp "PostGIS password: " PGPASSWORD
export PGPASSWORD
echo
trap 'unset PGPASSWORD' EXIT

CONN="PG:host=127.0.0.1 port=5433 dbname=$DB_NAME user=terralert"

DATA="database/postgis/data"

echo "Importing official communes..."
ogr2ogr -f PostgreSQL "$CONN" \
    "$DATA/communes_26191.gpkg" \
    -nln public.communes \
    -lco GEOMETRY_NAME=geom \
    -lco SPATIAL_INDEX=GIST

echo "Importing official rivers..."
ogr2ogr -f PostgreSQL "$CONN" \
    "$DATA/rivers_11_communes.gpkg" \
    -nln public.rivers \
    -lco GEOMETRY_NAME=geom \
    -lco SPATIAL_INDEX=GIST

echo "Importing flood indicators..."
ogr2ogr -f PostgreSQL "$CONN" \
    "$DATA/commune_indicators_landcover.gpkg" \
    -nln public.flood_commune_indicators_raw \
    -lco GEOMETRY_NAME=geom \
    -lco FID=gid \
    -lco SPATIAL_INDEX=GIST \
    -nlt PROMOTE_TO_MULTI

sql <<'SQL'
BEGIN;

ALTER TABLE public.communes
ALTER COLUMN iso SET NOT NULL;

ALTER TABLE public.communes
ADD CONSTRAINT communes_iso_unique UNIQUE (iso);

CREATE TABLE public.flood_commune_indicators AS
SELECT
    f.gid AS id,
    c.iso AS commune_code,
    c.nom_fr AS commune_name,
    c.nom_ar AS commune_name_ar,
    f.area_km2 AS area,
    f.elev_mean AS avg_elevation,
    f.elev_min AS min_elevation,
    f.elev_max AS max_elevation,
    f.slope_mean AS avg_slope,
    f.slope_min AS min_slope,
    f.slope_max AS max_slope,
    f.river_km AS river_length,
    f.drain_km_km2 AS drainage_density,
    f.pop_total AS population,
    f.pop_km2 AS population_density,
    f.urban_pct AS urban_coverage,
    f.forest_pct AS tree_coverage,
    f.veget_pct AS vegetation_coverage,
    c.geom
FROM public.flood_commune_indicators_raw f
JOIN public.communes c ON c.iso = f.iso;

ALTER TABLE public.flood_commune_indicators
ADD PRIMARY KEY (id);

ALTER TABLE public.flood_commune_indicators
ALTER COLUMN commune_code SET NOT NULL;

ALTER TABLE public.flood_commune_indicators
ADD CONSTRAINT flood_commune_code_unique
UNIQUE (commune_code);

ALTER TABLE public.flood_commune_indicators
ADD CONSTRAINT fk_flood_commune
FOREIGN KEY (commune_code)
REFERENCES public.communes(iso);

CREATE INDEX idx_flood_communes_geom
ON public.flood_commune_indicators USING GIST (geom);

CREATE INDEX idx_flood_communes_name
ON public.flood_commune_indicators (commune_name);

DO $$
BEGIN
    IF (SELECT COUNT(*) FROM communes) <> 11
    OR (SELECT COUNT(*) FROM rivers) <> 123
    OR (SELECT COUNT(*) FROM flood_commune_indicators_raw) <> 11
    OR (SELECT COUNT(*) FROM flood_commune_indicators) <> 11
    THEN
        RAISE EXCEPTION 'Unexpected feature counts';
    END IF;

    IF EXISTS (
        SELECT geom FROM communes
        UNION ALL
        SELECT geom FROM rivers
        UNION ALL
        SELECT geom FROM flood_commune_indicators_raw
        UNION ALL
        SELECT geom FROM flood_commune_indicators
    ) THEN
        IF EXISTS (
            SELECT 1 FROM (
                SELECT geom FROM communes
                UNION ALL
                SELECT geom FROM rivers
                UNION ALL
                SELECT geom FROM flood_commune_indicators_raw
                UNION ALL
                SELECT geom FROM flood_commune_indicators
            ) g
            WHERE geom IS NULL
               OR ST_IsEmpty(geom)
               OR NOT ST_IsValid(geom)
               OR ST_SRID(geom) <> 26191
        ) THEN
            RAISE EXCEPTION 'Geometry validation failed';
        END IF;
    END IF;
END $$;

ANALYZE public.communes;
ANALYZE public.rivers;
ANALYZE public.flood_commune_indicators;

COMMIT;

SELECT 'communes' AS dataset, COUNT(*) FROM communes
UNION ALL
SELECT 'rivers', COUNT(*) FROM rivers
UNION ALL
SELECT 'flood_indicators', COUNT(*) FROM flood_commune_indicators;
SQL

echo "Applying weather and hazard database migration..."

sql < database/postgis/migrations/001_weather_hazards.sql

echo "TERRALERT database initialized successfully."
