"""
Extract NPP-VIIRS radiance pixels to CSV.
Author: Kien Le
AI disclosure: This code was generated with the assistance of AI. The author has reviewed and edited the code to ensure its accuracy and functionality.
Last Update: 2026-30-09

Input: NPP-VIIRS raster file (.tif) and shapefiles (.shp) for admin level 0 or 1.
Output: CSV files containing pixel coordinates and radiance values for each province.
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
    boundaries = gpd.read_file(boundary_path)
    if province_name is not None:
        province_name_field = (
            "name" if "name" in boundaries.columns else "adm1_name"
        )
        if province_name_field not in boundaries:
            raise ValueError(
                f"Boundary file is missing province-name field "
                f"'name' or 'adm1_name': {boundary_path}"
            )
        province_names = boundaries[province_name_field].astype(str).str.strip()
        boundaries = boundaries.loc[province_names.eq(province_name)]
        if boundaries.empty:
            raise ValueError(
                f"Province {province_name!r} not found in boundary file: "
                f"{boundary_path}"
            )

    if boundaries.crs is None:
        raise ValueError(f"Boundary file has no CRS: {boundary_path}")

    geometries = boundaries.geometry
    geometries = geometries[geometries.notna() & ~geometries.is_empty]
    if geometries.empty:
        raise ValueError(f"Boundary file contains no usable geometries: {boundary_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(raster_path) as source:
        if source.crs is None:
            raise ValueError(f"Raster has no CRS: {raster_path}")

        vietnam = boundaries.loc[geometries.index].to_crs(source.crs)
        clipped, clipped_transform = mask(
            source,
            vietnam.geometry,
            indexes=1,
            crop=True,
            filled=False,
        )

        valid = ~np.ma.getmaskarray(clipped)
        values = np.asarray(clipped.data)
        if np.issubdtype(values.dtype, np.floating):
            valid &= np.isfinite(values)

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
        output_path = output_path.resolve()
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