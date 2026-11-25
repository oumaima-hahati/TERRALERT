#!/usr/bin/env python3
"""Export SRTM 30m DEM for TERRALERT via Earth Engine."""

import ee

PROJECT = "terralert-research"

ee.Initialize(project=PROJECT)

# Study-area envelope with a margin around the 11 commune points.
# This is a download extent, NOT a substitute for commune boundaries.
region = ee.Geometry.Rectangle(
    [-6.10, 35.45, -5.65, 35.85],
    proj="EPSG:4326",
    geodesic=False
)

dem = (
    ee.Image("USGS/SRTMGL1_003")
    .select("elevation")
    .clip(region)
)

task = ee.batch.Export.image.toDrive(
    image=dem,
    description="TERRALERT_SRTM30_DEM",
    folder="TERRALERT_DEM",
    fileNamePrefix="terralert_srtm30_dem",
    region=region,
    scale=30,
    crs="EPSG:32630",
    maxPixels=1000000000,
    fileFormat="GeoTIFF",
)

task.start()

print("=== TERRALERT DEM EXPORT ===")
print("Dataset: USGS/SRTMGL1_003")
print("Resolution: 30 m")
print("CRS: EPSG:32630")
print("Earth Engine task ID:", task.id)
print("Status:", task.status()["state"])
print("Google Drive folder: TERRALERT_DEM")
print("File prefix: terralert_srtm30_dem")
print("\nSUCCESS: DEM export submitted!")
