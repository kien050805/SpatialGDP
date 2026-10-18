"""Extract valid VIIRS pixels inside a formatted boundary shapefile."""

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
