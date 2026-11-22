# TERRALERT data collection priorities

22 November 2026 · Deliverable 1

## Tangier scope

Tangier, Morocco, exclusively. The exact approved project geometry and analysis CRS remain unverified. The register assesses dataset requirements for Tangier. Martil-area assets are listed as exclusions in the gap analysis.

| Status | Count |
| --- | --- |
| AVAILABLE_VERIFIED | 0 |
| AVAILABLE_UNVERIFIED | 4 |
| PARTIAL | 1 |
| MISSING | 29 |
| BLOCKED | 2 |
| UNKNOWN | 1 |

## Implementation sequence

1. Obtain the approved, versioned Tangier boundary and its documented analysis CRS.
2. Check the coverage and suitability of existing assets against the approved boundary, then resolve gaps in priority order using the acceptance criteria below.

## Collection and validation register

| ID | Dataset | Priority | Status | Source | Dependencies | Expected output | Acceptance criteria | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AOI | Approved Tangier boundary and analysis CRS | P0 | UNKNOWN | Project GIS handoff | Approved Tangier polygon, official identifiers where applicable, and documented analysis CRS | Approved Tangier polygon and CRS decision | Obtain the approved Tangier geometry or documented selection, with version, codes where applicable, analysis CRS and geometry QA. | S1,S2,S3,S17 |
| ADM | Raw administrative polygons and backup shapefiles | P0 | AVAILABLE_UNVERIFIED | Project administrative GeoPackages and backup shapefiles | AOI for subset selection | QA-approved Tangier subset from compatible source layers | Confirm that the source and administrative level match the approved Tangier definition. Check feature coverage, CRS, geometry validity, codes and license. | S1,S2,S5,S17 |
| IDS | Tangier administrative identifier crosswalk | P0 | MISSING | Approved boundary handoff and official identifiers | AOI, ADM | Tangier identifier crosswalk where applicable | Use the approved Tangier geometry and official codes. Require one-to-one joins where applicable and document unmatched records. | S2,S4,S5,S15,S17 |
| VRT | Prepared DEM mosaic | P0 | BLOCKED | Existing VRT and referenced DEM tiles | DEM, AOI | Portable mosaic covering approved Tangier boundary | Confirm Tangier coverage first, then validate portability, elevation units and zero-value handling if the mosaic is suitable. | S2,S6,S17 |
| CHP | CHIRPS daily precipitation | P0 | MISSING | UCSB Climate Hazards Center | AOI for production clip; bounded provider sample can be specified now | Versioned daily rainfall subset and manifest | Record version/stream, timestamp/day definition, units and masks; check gaps, nonnegative values, cells per commune and station agreement | S1,S2,S8 |
| ERA | ERA5-Land historical hourly weather | P0 | MISSING | Copernicus CDS / ECMWF | AOI for production clip; bounded provider sample can be specified now | Versioned hourly weather subset and manifest | Check UTC/local-day convention, K to °C, RH from dew point, m/s winds, precipitation accumulation/reset, coastal mask and day completeness | S1,S2,S9,S16 |
| POP | Tangier population and households | P1 | MISSING | HCP RGPH for approved Tangier reporting units | AOI, IDS | Tangier population and household table | Match census geography and official codes to the approved Tangier boundary, with year, counts and usage terms documented. | S2,S4,S15,S17 |
| DEM | Elevation source tiles | P1 | AVAILABLE_UNVERIFIED | Existing raw DEM tiles, subject to coverage check | AOI for coverage verification | Validated Tangier elevation source manifest | Compare tile footprints with the approved Tangier polygon before reuse. Check coverage, resolution, source, vertical datum and coastal NoData. | S1,S2,S6,S17 |
| SLO | Slope layer | P1 | MISSING | Derive from validated DEM | VRT, AOI | Slope GeoTIFF | Confirm degree or percent units, metric grid and azimuth/edge handling; reproduce from DEM | S1,S2,S6 |
| RIV | Rivers and drainage network | P1 | MISSING | Existing project data, basin agency or OSM waterways | AOI | Clean network GeoPackage | Validate network connectivity, stream orders, coverage and distance CRS | S1,S2 |
| LC | Tangier land cover and fuels proxy | P1 | MISSING | Tangier land-cover handoff or previously identified catalogue | AOI | Tangier land-cover raster and legend | Require documented Tangier coverage, classification year, legend, NoData and source license. | S1,S2,S5,S17 |
| FLO | Historical Tangier flood events and inundation masks | P1 | AVAILABLE_UNVERIFIED | Existing event raster pending geographic check; Tangier event records | AOI | Dated Tangier event catalogue and verified masks | Check against the approved Tangier polygon and verify date, pixel semantics and source before using the sample. | S1,S2,S7,S17 |
| STA | Independent local weather stations | P1 | MISSING | Morocco meteorological service or authorized station operator | Station inventory, observation access, and usage terms | Station catalogue and observations | Obtain station IDs, siting/elevation, record periods, relocations, observation time, units and permitted use | S1,S2 |
| WX | Harmonized commune weather series | P1 | MISSING | Derive from CHP, ERA and approved AOI | AOI, IDS, CHP, ERA; STA for external comparison | QC-flagged commune weather table | Unique commune-time keys, explicit quality flags, provenance, documented weighting and coverage, no invented fine-scale detail | S1,S2,S8,S9 |
| BASE | Seasonal weather and temperature baselines | P1 | MISSING | Derive from validated WX | WX | Versioned seasonal baseline table | Freeze baseline period and quantile/window conventions; handle leap days, sample counts and train-only fitting | S1,S2 |
| FRN | Rain forecast and 24/72-hour totals | P1 | MISSING | Open-Meteo selected forecast model | AOI, Open-Meteo connection | Forecast rain and totals | Preserve initialization/valid time and model; verify totals from correct hour windows, latest run and missing hours | S1,S2,S10 |
| FTM | Temperature, humidity and wind forecasts | P1 | MISSING | Open-Meteo selected forecast model | AOI, Open-Meteo connection | Time-stamped forecast weather table | Validate local-day Tmax and Tmin, RH bounds, wind units, model, horizon and stale-data rules | S1,S2,S10 |
| THH | Local heatwave thresholds and event rules | P1 | MISSING | Local meteorological guidance and validated baseline | BASE, FTM, VAL | Versioned heatwave rules | Record local-day Tmax definition, seasonal threshold, consecutive days and historical backtest | S1,S2 |
| THC | Local cold-wave thresholds and event rules | P1 | MISSING | Local meteorological guidance and validated baseline | BASE, FTM, VAL, DEM for elevation interpretation | Versioned cold-wave rules | Record local-day Tmin definition, elevation screening, consecutive days and historical backtest | S1,S2 |
| FIR | FIRMS VIIRS archive and monitoring feed | P1 | MISSING | NASA FIRMS standard archive / near-real-time feed | AOI, archive availability, and documented feed access | QC archive and feed test | Retain timestamp UTC, sensor, confidence, FRP, version and latency; validate dedup, join and distinction from confirmed incidents | S1,S2,S11 |
| IND | Commune spatial indicators | P1 | MISSING | Derive from approved boundaries and validated GIS layers | AOI, IDS, validated layers | Commune indicator table | Verify 11 rows, units, method/version, SQL/data round-trip and nulls | S1,S2 |
| RISK | Validated per-commune hazard outputs | P1 | MISSING | Versioned hazard model outputs | IND, WX, hazard-specific inputs and validation | Versioned risk tables | Include commune/time, risk class and version, validation evidence and uncertainty; reject stale runs | S1,S2,S3 |
| PROV | Dataset provenance and GeoAI evidence corpus | P1 | PARTIAL | Project documentation and primary provider records | Source metadata, licenses, and upstream processing lineage | Source and lineage registers | Record product version, date, license, transformation, validation and public citation for each released layer | S1,S2,S13 |
| ANOM | Temperature/rainfall anomalies and ML feature table | P1 | MISSING | Derive from WX and BASE | WX, BASE | Feature table with generation metadata | Keep explicit reference period, lag/rolling features, RH/wind and season; prevent train/test leakage | S1,S2 |
| VAL | Independent event checks and time-held-out evaluation set | P1 | MISSING | Station/event records and chronological holdout from QC history | WX, STA, FLO, FIE; define chronology before training | Frozen evaluation manifest | Freeze split before fitting; use extreme events and ordinary periods; report simple-rule comparison and uncertainty | S1,S2 |
| VUL | Age, disability or other vulnerability indicators | P2 | MISSING | HCP census commune tables or authorized local statistics | IDS, POP | Commune vulnerability table | Confirm indicator definitions, denominators, census year and disclosure constraints | S1,S2,S4,S15 |
| BAS | Tangier-relevant watershed polygon | P2 | MISSING | Tangier watershed data from the project or basin authority | AOI | Validated Tangier watershed layer where needed | Verify catchment relevance to the approved Tangier boundary, hydrological connectivity, outlet and source. | S1,S5,S17 |
| URB | Built-up footprint | P2 | MISSING | Existing project data or verified built-up land-cover class | LC, AOI | Built-up raster or polygons | Check definition, year, masks and pilot coverage; document derivation | S1,S2,S5 |
| INF | Roads and critical infrastructure | P2 | MISSING | Existing handoff or OSM/official data | AOI | Tagged infrastructure GeoPackage | Check class coverage, attribution, coordinate validity and duplicates | S1,S2 |
| FIE | Confirmed wildfire incidents/perimeters | P2 | MISSING | Forestry authority, civil protection or documented perimeter catalogue | Incident provider | Independent incident catalogue | Require unique incident IDs, independent dates/perimeters and coverage limitations | S1,S2 |
| FWI | Fire weather inputs and FWI output | P2 | BLOCKED | Derive from WX plus operational forecast where needed | WX, FTM | Weather inputs and FWI time series | Validate local-noon temperature/RH/wind and preceding rain, initialization/warm-up and reference results | S1,S2 |
| S2A | Sentinel-2 L2A reflectance and masks | P2 | MISSING | Copernicus Data Space | AOI | Scene manifest and masked reflectance | Verify scene IDs, acquisition dates, AOI overlap, scale/offset and cloud/shadow or invalid pixel masks | S1,S2,S12 |
| NDV | NDVI vegetation time series | P2 | MISSING | Derive from S2A red and NIR reflectance | S2A | Masked NDVI time series | Check cloud/shadow mask, aligned grid, index range and minimum clear observations | S1,S2,S12 |
| LOG | Refresh and QA run records | P2 | MISSING | Pipeline and MLflow outputs | Published pipeline outputs | Refresh and QA run logs | Record source version, run time, coverage, validation outcome and last successful refresh | S1,S2,S3 |
| NBR | NBR and dNBR burn metrics | P3 | MISSING | Derive from S2A NIR/SWIR pre/post scenes | S2A, FIE | Paired NBR/dNBR rasters | Match grids and dates, mask invalid pixels, document sign and validate against incident perimeters | S1,S2,S12 |
| SOIL | Tangier soil properties by depth | P3 | MISSING | Tangier soil product if needed for optional flood work | AOI | Optional validated Tangier depth stack | Require Tangier coverage and check product version, depth, units and nodata. | S1,S14,S17 |
| GEO | Geology polygons and reference images | P3 | AVAILABLE_UNVERIFIED | Existing geology ZIP and reference images | AOI | Optional geology layer with verified Tangier coverage | Check archive contents, CRS, actual Tangier overlap and legend before using. | S1,S14,S17 |

## Evidence index

| ID | Reference | Location |
| --- | --- | --- |
| S1 | Shared project Drive and traversed folder listings | https://drive.google.com/drive/folders/1ESbJ6vA_-M6patfwNUfFeGfFqD6aJt4_ |
| S2 | Project planning reference | https://docs.google.com/spreadsheets/d/1aVURTUImFViIwdB-XqBvWbGU1tiFegnQvtyDkEhsTaM/edit#gid=0 |
| S3 | Local README and backend | README.md and backend/app/main.py |
| S4 | Demographics CSV | https://drive.google.com/file/d/1gqunbH5X5TfoU8m4dPARZVZ3AX_Oe_LG/view |
| S5 | Territorial layers | https://drive.google.com/drive/folders/1YR0u6S8F4x2YT_ZSpsl4DyyWfCBtqSeo |
| S6 | DEM VRT and source tiles | https://drive.google.com/file/d/1lnWKQpHBL-4dTyMJ77Up5Gn8JeVdu4PM/view |
| S7 | Flood event raster | https://drive.google.com/file/d/1KpTLECjzS3nQcTl0UvQAF0R87aIEOWQ3/view |
| S8 | UCSB CHIRPS catalogue | https://chc.ucsb.edu/data/chirps/ |
| S9 | Copernicus CDS ERA5-Land | https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land |
| S10 | Open-Meteo Forecast API | https://open-meteo.com/en/docs |
| S11 | NASA FIRMS | https://firms.modaps.eosdis.nasa.gov/ |
| S12 | Copernicus Sentinel-2 | https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-2 |
| S13 | Existing DATA_INVENTORY.xlsx | https://drive.google.com/file/d/1rGcW72tPm2r4hnJvFJsSWN1LPs6Jm0-K/view |
| S14 | Geological raw folder | https://drive.google.com/drive/folders/1uQuD5f7FaOPgsKeUWDZX9uy8OhpSf396 |
| S15 | HCP RGPH 2024 official publication index | https://www.hcp.ma/search/rgph/?start_liste=40 |
| S16 | ECMWF ERA5-Land product documentation | https://confluence.ecmwf.int/pages/viewpage.action?pageId=143047110 |
| S17 | User scope correction | TERRALERT conversation |
