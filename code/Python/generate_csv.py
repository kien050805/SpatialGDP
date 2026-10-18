"""Generate Vietnam-wide VIIRS pixel CSVs for every available raster."""

from __future__ import annotations

import re
from pathlib import Path

import geopandas as gpd

import extract_viirs_pixels
from shp_wrangling import province_slug


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def existing_path(primary: Path, alternate: Path) -> Path:
    if primary.exists():
        return primary
    if alternate.exists():
        return alternate
    return primary


DEFAULT_RASTER_DIR = existing_path(
    PROJECT_ROOT / "data" / "viirs_raw",
    PROJECT_ROOT / "data" / "_viirs_raw",
)
DEFAULT_BOUNDARY = PROJECT_ROOT / "data" / "shp_boundaries" / "level0" / "vnm_level0.shp"
DEFAULT_PROVINCE_BOUNDARIES = (
    PROJECT_ROOT / "data" / "shp_boundaries" / "level1" / "vnm_level1.shp"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "viirs_pixel_radiance"
DEFAULT_PROVINCE_OUTPUT_DIR = PROJECT_ROOT / "data" / "viirs_pixel_radiance_province"


def list_rasters(raster_dir: Path) -> list[tuple[Path, str]]:
    if not raster_dir.is_dir():
        raise FileNotFoundError(f"Raster directory not found: {raster_dir}")

    rasters = sorted(
        path
        for path in raster_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".tif"
    )
    if not rasters:
        raise FileNotFoundError(f"No .tif raster files found in {raster_dir}")

    raster_years = []
    seen_years = set()
    for raster_path in rasters:
        match = re.search(r"npp_(\d{4})", raster_path.name, re.IGNORECASE)
        if not match:
            raise ValueError(f"Could not determine the year from raster name: {raster_path}")
        year = match.group(1)
        if year in seen_years:
            raise ValueError(f"Multiple raster files found for {year} in {raster_dir}")
        seen_years.add(year)
        raster_years.append((raster_path, year))
    return raster_years


def generate_pixel_csvs(
    raster_dir: Path = DEFAULT_RASTER_DIR,
    boundary_path: Path = DEFAULT_BOUNDARY,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> None:
    if not boundary_path.is_file():
        raise FileNotFoundError(f"Boundary file not found: {boundary_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    for raster_path, year in list_rasters(raster_dir):
        output_path = output_dir / f"vnm_{year}_pixel_radiance.csv"
        pixel_count = extract_viirs_pixels.extract_pixels(
            raster_path, boundary_path, output_path
        )
        print(f"{year}: wrote {pixel_count:,} pixels to {output_path.resolve()}")


def generate_province_pixel_csvs(
    raster_dir: Path = DEFAULT_RASTER_DIR,
    boundaries_path: Path = DEFAULT_PROVINCE_BOUNDARIES,
    output_dir: Path = DEFAULT_PROVINCE_OUTPUT_DIR,
) -> None:
    if not boundaries_path.is_file():
        raise FileNotFoundError(f"Province boundary file not found: {boundaries_path}")

    boundaries = gpd.read_file(boundaries_path)
    if boundaries.crs is None:
        raise ValueError(f"Province boundary file has no CRS: {boundaries_path}")
    province_name_field = "name"
    if province_name_field not in boundaries:
        raise ValueError(
            f"Province boundary file is missing {province_name_field!r}: "
            f"{boundaries_path}"
        )

    province_rows = []
    seen_slugs = set()
    for province in (
        boundaries[province_name_field]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
    ):
        if not province:
            continue
        slug = province_slug(province)
        if not slug:
            raise ValueError(
                f"Province name cannot be converted to a file name: {province!r}"
            )
        if slug in seen_slugs:
            raise ValueError(f"Province names produce a duplicate file stem: {slug}")
        seen_slugs.add(slug)
        province_rows.append((province, slug))

    if not province_rows:
        raise ValueError(f"No province names found in {boundaries_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    for raster_path, year in list_rasters(raster_dir):
        year_output_dir = output_dir / year
        for province, slug in province_rows:
            output_path = year_output_dir / f"{slug}_viirs_{year}_pixel_radiance.csv"
            pixel_count = extract_viirs_pixels.extract_pixels(
                raster_path,
                boundaries_path,
                output_path,
                province_name=province,
            )
            print(
                f"{province} ({year}): wrote {pixel_count:,} pixels to "
                f"{output_path.resolve()}"
            )


def main() -> None:
    generate_pixel_csvs()
    generate_province_pixel_csvs()


if __name__ == "__main__":
    main()