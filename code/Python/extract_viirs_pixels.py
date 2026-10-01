"""
Extract valid NPP-VIIRS radiance pixels within Vietnam to CSV.
Author: Kien Le
AI disclosure: This code was generated with the assistance of AI. The author has reviewed and edited the code to ensure its accuracy and functionality.
Last Update: 2026-30-09
"""

import argparse
import csv
from pathlib import Path
import re
import unicodedata

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.warp import transform


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RASTER = (
    PROJECT_ROOT
    / "data"
    / "VNL_npp_2025_global_vcmslcfg_v2_c202604011200.average_masked.dat.tif"
)
DEFAULT_BOUNDARIES_DIR = PROJECT_ROOT / "data" / "vnm_district_boundaries"
DEFAULT_POPULATION = PROJECT_ROOT / "data" / "vnm_population.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "viirs_pixel_radiance_province"
DEFAULT_YEAR = "2025"


def province_slug(province: str) -> str:
    normalized = province.replace("Đ", "D").replace("đ", "d")
    normalized = unicodedata.normalize("NFKD", normalized)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")


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


def extract_all_provinces(
    raster_path: Path,
    boundaries_dir: Path,
    population_path: Path,
    output_dir: Path,
    year: str,
) -> None:
    if not raster_path.is_file():
        raise FileNotFoundError(f"Raster file not found: {raster_path}")
    if not population_path.is_file():
        raise FileNotFoundError(f"Population file not found: {population_path}")

    with population_path.open(newline="", encoding="utf-8-sig") as population_file:
        reader = csv.DictReader(population_file)
        if not reader.fieldnames or "Provincies" not in reader.fieldnames:
            raise ValueError(f"Expected a 'Provincies' column in {population_path}")
        provinces = [row["Provincies"].strip() for row in reader if row["Provincies"]]

    province_files = []
    seen_slugs = set()
    for province in provinces:
        slug = province_slug(province)
        if slug in seen_slugs:
            raise ValueError(f"Province names produce a duplicate file stem: {slug}")
        seen_slugs.add(slug)
        boundary_path = boundaries_dir / slug / f"{slug}.shp"
        if not boundary_path.is_file():
            raise FileNotFoundError(
                f"Missing standardized shapefile for {province}: {boundary_path}"
            )
        output_path = output_dir / year / f"{slug}_viirs_{year}_pixel_radiance.csv"
        province_files.append((province, boundary_path, output_path))

    if not province_files:
        raise ValueError(f"No provinces found in {population_path}")

    for province, boundary_path, output_path in province_files:
        pixel_count = extract_pixels(raster_path, boundary_path, output_path)
        print(f"{province}: wrote {pixel_count:,} pixels to {output_path.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract 2025 VIIRS radiance pixels for all Vietnamese provinces."
    )
    parser.add_argument("--raster", type=Path, default=DEFAULT_RASTER)
    parser.add_argument("--boundaries-dir", type=Path, default=DEFAULT_BOUNDARIES_DIR)
    parser.add_argument("--population", type=Path, default=DEFAULT_POPULATION)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--year", default=DEFAULT_YEAR)
    args = parser.parse_args()

    extract_all_provinces(
        args.raster,
        args.boundaries_dir,
        args.population,
        args.output_dir,
        args.year,
    )


if __name__ == "__main__":
    main()