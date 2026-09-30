"""
Extract valid NPP-VIIRS radiance pixels within Vietnam to CSV.
Author: Kien Le
AI disclosure: This code was generated with the assistance of AI. The author has reviewed and edited the code to ensure its accuracy and functionality.
Last Update: 2026-30-09
Dependencies: geopandas, numpy, rasterio
This script reads a VIIRS raster file and a shapefile containing Vietnam's administrative boundaries,
extracts the valid radiance pixels that fall within Vietnam, and writes them to a CSV file
with columns for raster row, raster column, longitude, latitude, and radiance value.
Usage:
    python extract_viirs_pixels.py --raster <path_to_raster> --boundary <path_to_boundary_shapefile> --output <path_to_output_csv>
If no arguments are provided, the script will use default paths defined in the code.
"""

import argparse
import csv
from pathlib import Path
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.warp import transform


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RASTER = (
    PROJECT_ROOT
    / "data"
    / "VNL_npp_2025_global_vcmslcfg_v2_c202604011200.average_masked.dat.tif"
)
DEFAULT_BOUNDARY = (
    PROJECT_ROOT / "data" / "vnm_admin_boundaries.shp" / "vnm_admin0.shp"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "vietnam_viirs_2025_pixel_radiance.csv"


def extract_pixels(raster_path: Path, boundary_path: Path, output_path: Path) -> int:
    boundaries = gpd.read_file(boundary_path)
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
    parser = argparse.ArgumentParser(
        description="Extract valid VIIRS radiance pixels within Vietnam to a CSV."
    )
    parser.add_argument("--raster", type=Path, default=DEFAULT_RASTER)
    parser.add_argument("--boundary", type=Path, default=DEFAULT_BOUNDARY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    pixel_count = extract_pixels(args.raster, args.boundary, args.output)
    print(f"Wrote {pixel_count:,} pixels to {args.output.resolve()}")


if __name__ == "__main__":
    main()