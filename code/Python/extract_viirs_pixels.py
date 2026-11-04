"""
Extract valid VIIRS pixels inside a formatted boundary shapefile.
Author: Kien Le
AI disclosure: This code was generated with the assistance of AI. 
The author has reviewed and edited the code to ensure its accuracy and functionality.
Last Update: 2026-11-02
"""
from __future__ import annotations

import csv
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.warp import transform


def extract_pixels(
    raster_path: Path,
    boundary_path: Path,
    output_path: Path,
    province_name: str | None = None,
) -> int:
    """
    Extract valid raster pixels within specified administrative boundaries and save their spatial coordinates and radiance values to a CSV file.

    The function reads the administrative boundary data and optionally selects a specific province by name.
    It then reprojects the selected geometries to match the raster coordinate reference system and masks the raster to extract pixels within the boundaries.
    Invalid pixels, including masked values and non-finite values, are excluded.
    For each valid pixel, the function calculates its geographic coordinates (longitude and latitude) and retrieves its original raster row and column indices.

    The extracted data are saved to a CSV file containing raster indices, geographic coordinates, and radiance values.
    The output directory is created automatically if it does not exist.

    Args:
        raster_path (Path): Path to the input raster file.
        boundary_path (Path): Path to the administrative boundary file.
        output_path (Path): Path to the output CSV file.
        province_name (str | None): Name of the province to extract.
            If None, pixels within all administrative boundaries are extracted.
            Defaults to None.

    Returns:
        int: Number of valid raster pixels extracted.

    """
    boundaries = gpd.read_file(boundary_path)
    if province_name is None:
        geometries = boundaries.geometry
    else:
        province_mask = boundaries["name"].str.strip() == province_name
        geometries = boundaries.loc[province_mask].geometry

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(raster_path) as source:
        geometries = geometries.to_crs(source.crs)
        clipped, clipped_transform = mask(
            source,
            geometries,
            indexes=1,
            crop=True,
            filled=False,
        )

        values = clipped.data
        valid = ~np.ma.getmaskarray(clipped) & np.isfinite(values)
        rows, columns = np.nonzero(valid)
        radiance = values[rows, columns]
        pixel_x, pixel_y = rasterio.transform.xy(
            clipped_transform, rows, columns, offset="center"
        )
        longitude, latitude = transform(
            source.crs, "EPSG:4326", pixel_x, pixel_y
        )
        row_offset, column_offset = source.index(
            clipped_transform.c, clipped_transform.f
        )

    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(("raster_row", "raster_col", "longitude", "latitude", "radiance"))
        writer.writerows(
            (
                int(row_offset + row),
                int(column_offset + column),
                lon,
                lat,
                value.item() if hasattr(value, "item") else value,
            )
            for row, column, lon, lat, value in zip(
                rows, columns, longitude, latitude, radiance
            )
        )

    return len(rows)

def main() -> None:
    return

if __name__ == "__main__":
    main()