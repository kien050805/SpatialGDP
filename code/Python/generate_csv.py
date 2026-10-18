"""Generate Vietnam-wide VIIRS pixel CSVs for every available raster."""

import re
from pathlib import Path

import extract_viirs_pixels


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
DEFAULT_BOUNDARY = existing_path(
    PROJECT_ROOT / "data" / "vnm_admin_boundaries" / "vnm_admin0.shp",
    PROJECT_ROOT / "data" / "_vnm_admin_boundaries" / "vnm_admin0.shp",
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "viirs_pixel_radiance"


def generate_pixel_csvs(
    raster_dir: Path = DEFAULT_RASTER_DIR,
    boundary_path: Path = DEFAULT_BOUNDARY,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> None:
    if not raster_dir.is_dir():
        raise FileNotFoundError(f"Raster directory not found: {raster_dir}")
    if not boundary_path.is_file():
        raise FileNotFoundError(f"Boundary file not found: {boundary_path}")

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

    output_dir.mkdir(parents=True, exist_ok=True)
    for raster_path, year in raster_years:
        output_path = output_dir / f"vnm_{year}_pixel_radiance.csv"
        pixel_count = extract_viirs_pixels.extract_pixels(
            raster_path, boundary_path, output_path
        )
        print(f"{year}: wrote {pixel_count:,} pixels to {output_path.resolve()}")


def main() -> None:
    generate_pixel_csvs()


if __name__ == "__main__":
    main()