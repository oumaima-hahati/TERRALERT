# TERRALERT data gap analysis

22 November 2026 · Deliverable 1

## Executive summary

Tangier, Morocco, exclusively. The exact approved project geometry and analysis CRS remain unverified. The repository’s older Tangier–Assilah description does not establish the approved Tangier boundary. The local API expects `data/communes.geojson`, which is absent. The raw regional and commune resources do not document an approved Tangier subset. EPSG:4326 and EPSG:32630 remain observed file CRSs only.

The inventory retains 37 records and 74 source files, including excluded assets for traceability. Statuses assess availability for Tangier. Zero records are verified for their intended Tangier use.

| Status | Count |
| --- | --- |
| AVAILABLE_VERIFIED | 0 |
| AVAILABLE_UNVERIFIED | 4 |
| PARTIAL | 1 |
| MISSING | 29 |
| BLOCKED | 2 |
| UNKNOWN | 1 |

## Geographic relevance of existing assets

| Relevance | Assets | Evidence and limits |
| --- | --- | --- |
| Potential Tangier reuse | Raw administrative GeoPackages and backup shapefiles (ADM) | The commune GPKG is a broad EPSG:4326 source with 1,541 features and one duplicate ISO (`MA-03-131-0101`). The approved Tangier subset, correct administrative level, geometry and licensing still require confirmation. |
| Outside scope | Demographics CSV and earlier commune joins (POP, IDS), Martil watershed (BAS), Oued Martil land-cover TIFF (LC), and Martil soil tiles (SOIL) | The CSV describes Tétouan and M’diq-Fnideq, and the 11 historical rows are retained only to document exclusion. The watershed is Martil-area material. The land-cover and soil classifications follow their documented filenames; actual extents were unread. |
| Tangier coverage still unverified | DEM source tiles and mosaic (DEM, VRT), 2002 flood raster (FLO), and Rif geology materials (GEO) | The mosaic has a declared 12.5 m EPSG:32630 grid and machine-specific source paths. The flood raster is EPSG:32630 at 250 m, with unknown exact event date and class meanings. The geology archive and exact footprints remain unverified. |

## Remaining Tangier gaps

The approved boundary and its CRS are the immediate dependency. A Tangier identifier crosswalk, census inputs, land cover, and catchment data are absent from the inspected resources. CHIRPS, ERA5-Land, stations, forecasts, and other previously recorded gaps remain open for Tangier.

## Audit limits

The audit draws on the local repository and inspected shared project resources. The original inventory workbook remains inaccessible after Drive’s earlier HTTP 403. Large raster footprints, geometry topology and intersection with the approved Tangier area remain unverified.

## Complete gap register

The collection plan expands each record with its source, dependencies, output and acceptance tests.

| ID | Dataset | Status | Priority | Finding | Evidence |
| --- | --- | --- | --- | --- | --- |
| AOI | Approved Tangier boundary and analysis CRS | UNKNOWN | P0 | No approved Tangier polygon, linked subset or analysis CRS decision located. The older Tangier–Assilah description does not define the Tangier boundary. | S1,S2,S3,S17 |
| ADM | Raw administrative polygons and backup shapefiles | AVAILABLE_UNVERIFIED | P0 | Potential Tangier reuse as source layers. The raw commune layer contains 1,541 records and a duplicated ISO. No Tangier subset was approved or verified. | S1,S2,S5,S17 |
| IDS | Tangier administrative identifier crosswalk | MISSING | P0 | No Tangier crosswalk located. The earlier mechanical join used Martil-area records and is out of scope. | S2,S4,S5,S15,S17 |
| VRT | Prepared DEM mosaic | BLOCKED | P0 | The VRT requires machine-specific paths. Verify Tangier coverage before considering repair or reuse. | S2,S6,S17 |
| CHP | CHIRPS daily precipitation | MISSING | P0 | No precipitation file found; supplies rainfall history and daily proxies | S1,S2,S8 |
| ERA | ERA5-Land historical hourly weather | MISSING | P0 | No weather file found; acquire t2m, d2m, u10, v10, total precipitation where needed | S1,S2,S9,S16 |
| POP | Tangier population and households | MISSING | P1 | Existing CSV covers Tétouan and M’diq-Fnideq candidate records. It supplies no Tangier population counts. | S2,S4,S15,S17 |
| DEM | Elevation source tiles | AVAILABLE_UNVERIFIED | P1 | Two tiles are listed. Tangier coverage and usable pixel metadata remain unverified. | S1,S2,S6,S17 |
| SLO | Slope layer | MISSING | P1 | No slope asset found | S1,S2,S6 |
| RIV | Rivers and drainage network | MISSING | P1 | Hydrological folder empty; tracks flow and proximity | S1,S2 |
| LC | Tangier land cover and fuels proxy | MISSING | P1 | The existing TIFF is scoped to Oued Martil by filename and folder evidence. Its actual extent is unread. No Tangier land-cover asset located. | S1,S2,S5,S17 |
| FLO | Historical Tangier flood events and inundation masks | AVAILABLE_UNVERIFIED | P1 | The 2002-labelled TIFF has readable pixel and grid metadata. Tangier intersection, date, provenance and class meaning are unverified. | S1,S2,S7,S17 |
| STA | Independent local weather stations | MISSING | P1 | No station observation series found | S1,S2 |
| WX | Harmonized commune weather series | MISSING | P1 | No processed series found; shared input for hazard modules | S1,S2,S8,S9 |
| BASE | Seasonal weather and temperature baselines | MISSING | P1 | No baseline output found; needed for comparability across seasons | S1,S2 |
| FRN | Rain forecast and 24/72-hour totals | MISSING | P1 | No operational feed evidence found | S1,S2,S10 |
| FTM | Temperature, humidity and wind forecasts | MISSING | P1 | No forecast observations or feed test found | S1,S2,S10 |
| THH | Local heatwave thresholds and event rules | MISSING | P1 | No threshold/duration specification found | S1,S2 |
| THC | Local cold-wave thresholds and event rules | MISSING | P1 | No threshold/duration specification found | S1,S2 |
| FIR | FIRMS VIIRS archive and monitoring feed | MISSING | P1 | No archive file or successful feed test was available for validation | S1,S2,S11 |
| IND | Commune spatial indicators | MISSING | P1 | No spatial indicator table found | S1,S2 |
| RISK | Validated per-commune hazard outputs | MISSING | P1 | Risk outputs absent in inspected workspace; needed for grounded chatbot responses | S1,S2,S3 |
| PROV | Dataset provenance and GeoAI evidence corpus | PARTIAL | P1 | Some asset metadata and README exist; original inventory access blocked and per-layer lineage incomplete | S1,S2,S13 |
| ANOM | Temperature/rainfall anomalies and ML feature table | MISSING | P1 | No ML feature or anomaly dataset found | S1,S2 |
| VAL | Independent event checks and time-held-out evaluation set | MISSING | P1 | No validation split or matched events found | S1,S2 |
| VUL | Age, disability or other vulnerability indicators | MISSING | P2 | Existing CSV has no age or disability breakdown; needed for differentiated exposure | S1,S2,S4,S15 |
| BAS | Tangier-relevant watershed polygon | MISSING | P2 | Existing watershed polygon is from the Martil-area material. No Tangier catchment layer located. | S1,S5,S17 |
| URB | Built-up footprint | MISSING | P2 | No dedicated candidate asset found; supports runoff and exposure | S1,S2,S5 |
| INF | Roads and critical infrastructure | MISSING | P2 | No mapped file found; needed for access and exposure | S1,S2 |
| FIE | Confirmed wildfire incidents/perimeters | MISSING | P2 | No historical incident catalogue found. Independent records are needed to validate detections and burned-area products. | S1,S2 |
| FWI | Fire weather inputs and FWI output | BLOCKED | P2 | FWI inputs and computation are blocked. Required Tangier weather inputs were unavailable. The original blocker was unspecified. | S1,S2 |
| S2A | Sentinel-2 L2A reflectance and masks | MISSING | P2 | No scenes found; input for vegetation and burn screening | S1,S2,S12 |
| NDV | NDVI vegetation time series | MISSING | P2 | No vegetation index output found | S1,S2,S12 |
| LOG | Refresh and QA run records | MISSING | P2 | No refresh evidence or lineage logs found | S1,S2,S3 |
| NBR | NBR and dNBR burn metrics | MISSING | P3 | No paired burn-metric output found | S1,S2,S12 |
| SOIL | Tangier soil properties by depth | MISSING | P3 | All 36 listed tiles are Martil-labelled. Their footprints were unread. No Tangier soil stack located. | S1,S14,S17 |
| GEO | Geology polygons and reference images | AVAILABLE_UNVERIFIED | P3 | Rif geology materials are listed. Tangier coverage, spatial data contents and source remain unverified. | S1,S14,S17 |

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
