$ErrorActionPreference = 'Stop'
$psql = 'C:\Program Files\PostgreSQL\18\bin\psql.exe'
$ogr = 'C:\Program Files\QGIS 3.44.9\bin\ogr2ogr.exe'
$gpkg = 'C:\Users\Yasfa\OneDrive\Documents\terralert\1_Data_collection\Clean\Floods\GIS_indicators_20261122_180750\commune_indicators_landcover.gpkg'
if (!(Test-Path $gpkg)) { throw 'Source GeoPackage missing.' }
$secure = Read-Host 'Enter your local PostgreSQL postgres password (hidden)' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    $conn = 'host=localhost port=5432 dbname=TERRALERT user=postgres'
    $check = & $psql -X -w -h localhost -U postgres -d TERRALERT -Atqc "SELECT (postgis_version() IS NOT NULL)::int || ',' || (to_regclass('public.flood_commune_indicators_raw') IS NULL)::int || ',' || (to_regclass('public.flood_commune_indicators') IS NULL)::int" 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Database login failed: $check" }
    if (($check | Select-Object -Last 1) -ne '1,1,1') { throw "Import stopped: PostGIS unavailable or one of the target tables already exists. Result: $check" }
    Write-Host 'Importing original attributes and polygons into a separate staging table...'
    & $ogr -f PostgreSQL "PG:$conn" $gpkg commune_indicators_landcover -nln public.flood_commune_indicators_raw -lco GEOMETRY_NAME=geom -lco FID=gid -nlt PROMOTE_TO_MULTI
    if ($LASTEXITCODE -ne 0) { throw 'ogr2ogr import failed. No existing table was overwritten.' }
    $sql = @'
BEGIN;
CREATE TABLE public.flood_commune_indicators AS
SELECT gid AS id,
       "ISO" AS commune_code,
       nom_fr AS commune_name,
       nom_ar AS commune_name_ar,
       area_km2 AS area,
       elev_mean AS avg_elevation,
       elev_min AS min_elevation,
       elev_max AS max_elevation,
       slope_mean AS avg_slope,
       slope_min AS min_slope,
       slope_max AS max_slope,
       river_km AS river_length,
       drain_km_km2 AS drainage_density,
       pop_total AS population,
       pop_km2 AS population_density,
       urban_pct AS urban_coverage,
       forest_pct AS tree_coverage,
       veget_pct AS vegetation_coverage,
       geom
FROM public.flood_commune_indicators_raw;
ALTER TABLE public.flood_commune_indicators ADD PRIMARY KEY (id);
CREATE INDEX idx_flood_communes_geom ON public.flood_commune_indicators USING GIST (geom);
CREATE INDEX idx_flood_communes_name ON public.flood_commune_indicators (commune_name);
CREATE INDEX idx_flood_communes_code ON public.flood_commune_indicators (commune_code);
COMMENT ON COLUMN public.flood_commune_indicators.area IS 'Square kilometres (km2)';
COMMENT ON COLUMN public.flood_commune_indicators.avg_elevation IS 'Metres above DEM vertical reference';
COMMENT ON COLUMN public.flood_commune_indicators.avg_slope IS 'Degrees';
COMMENT ON COLUMN public.flood_commune_indicators.river_length IS 'Kilometres';
COMMENT ON COLUMN public.flood_commune_indicators.drainage_density IS 'River kilometres per square kilometre (km/km2)';
COMMENT ON COLUMN public.flood_commune_indicators.population_density IS 'People per square kilometre';
COMMENT ON COLUMN public.flood_commune_indicators.urban_coverage IS 'Percent of classified land-cover pixels';
COMMENT ON COLUMN public.flood_commune_indicators.tree_coverage IS 'Percent of classified land-cover pixels';
COMMENT ON COLUMN public.flood_commune_indicators.vegetation_coverage IS 'Percent of classified land-cover pixels';
ANALYZE public.flood_commune_indicators;
COMMIT;
'@
    & $psql -X -w -v ON_ERROR_STOP=1 -h localhost -U postgres -d TERRALERT -c $sql
    if ($LASTEXITCODE -ne 0) { throw 'Clean table or indexes failed; staging table remains available.' }
    Write-Host '=== VALIDATION ==='
    & $psql -X -w -v ON_ERROR_STOP=1 -h localhost -U postgres -d TERRALERT -c 'SELECT COUNT(*) AS communes, COUNT(DISTINCT commune_code) AS distinct_codes, COUNT(*) FILTER (WHERE ST_SRID(geom)=26191) AS epsg_26191, COUNT(*) FILTER (WHERE ST_IsValid(geom)) AS valid_geometries FROM public.flood_commune_indicators;'
    & $psql -X -w -v ON_ERROR_STOP=1 -h localhost -U postgres -d TERRALERT -c "SELECT indexname FROM pg_indexes WHERE schemaname='public' AND tablename='flood_commune_indicators' ORDER BY indexname;"
    & $psql -X -w -v ON_ERROR_STOP=1 -h localhost -U postgres -d TERRALERT -c "EXPLAIN (ANALYZE, BUFFERS) SELECT commune_name FROM public.flood_commune_indicators WHERE commune_name='Souani';"
    Write-Host 'Done. Source GeoPackage unchanged. Both original and clean tables preserved.'
} finally {
    $env:PGPASSWORD = $null
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}
