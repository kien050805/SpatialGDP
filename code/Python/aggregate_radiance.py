"""Calculate mean VIIRS radiance for administrative levels 0, 1, and 2."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PIXELS_DIR = PROJECT_ROOT / "data" / "viirs_pixel_radiance"
DEFAULT_BOUNDARIES_DIR = PROJECT_ROOT / "data" / "shp_boundaries"
DEFAULT_PROVINCES = PROJECT_ROOT / "data" / "_vnm_indicators" / "vnm_provinces.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "average_radiance"
PIXEL_FILE_SUFFIX = "_pixel_radiance.csv"


def name_slug(name: str) -> str:
    normalized = name.replace("Đ", "D").replace("đ", "d")
    normalized = unicodedata.normalize("NFKD", normalized)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")


def province_file_stems(provinces: list[str]) -> list[tuple[str, str]]:
    province_rows = []
    provinces_by_slug = {}
    for province in provinces:
        province_slug = name_slug(province)
        if not province_slug or province_slug in provinces_by_slug:
            other = provinces_by_slug.get(province_slug)
            raise ValueError(
                f"Province names produce an invalid or duplicate file stem: "
                f"{other!r} and {province!r}"
            )
        provinces_by_slug[province_slug] = province
        province_rows.append((province, province_slug))
    return province_rows


def unique_level2_slugs(names: list[str]) -> list[str]:
    slugs = [name_slug(name) for name in names]
    counts = {slug: slugs.count(slug) for slug in set(slugs)}
    unique_slugs = [
        (
            f"{slug}_{hashlib.sha1(name.encode('utf-8')).hexdigest()[:8]}"
            if counts[slug] > 1
            else slug
        )
        for name, slug in zip(names, slugs)
    ]
    if len(unique_slugs) != len(set(unique_slugs)):
        raise ValueError("Level-2 names do not produce unique pixel CSV filenames.")
    return unique_slugs


def read_provinces(provinces_path: Path) -> list[str]:
    provinces = pd.read_csv(provinces_path, encoding="utf-8-sig")
    if "province" not in provinces.columns:
        raise ValueError(
            f"Province file is missing the 'province' column: {provinces_path}"
        )
    names = provinces["province"].dropna().astype(str).str.strip()
    names = names[names.ne("")]
    if names.empty or names.duplicated().any():
        raise ValueError(
            f"Province file must contain unique, non-empty names: {provinces_path}"
        )
    return names.tolist()


def mean_radiance(pixels_path: Path) -> tuple[float, int]:
    pixels = pd.read_csv(
        pixels_path,
        usecols=("longitude", "latitude", "radiance"),
    )
    pixels = pixels.replace([np.inf, -np.inf], np.nan).dropna(
        subset=("longitude", "latitude", "radiance")
    )
    return (
        float(pixels["radiance"].mean()) if not pixels.empty else float("nan"),
        len(pixels),
    )


def average_record(name: str, pixels_path: Path) -> dict[str, object]:
    radiance, pixel_count = mean_radiance(pixels_path)
    return {
        "name": name,
        "mean_radiance": radiance,
        "pixel_count": pixel_count,
    }


def write_average_csv(records: list[dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records, columns=("name", "mean_radiance", "pixel_count")).to_csv(
        output_path, index=False, na_rep=""
    )
    print(f"Wrote {len(records)} rows to {output_path.resolve()}")


def available_years(pixels_dir: Path) -> list[str]:
    level0_dir = pixels_dir / "level0"
    if not level0_dir.is_dir():
        raise FileNotFoundError(f"Level-0 pixel directory not found: {level0_dir}")
    years = sorted(
        path.name
        for path in level0_dir.iterdir()
        if path.is_dir()
        and (path / f"vnm_{path.name}{PIXEL_FILE_SUFFIX}").is_file()
    )
    if not years:
        raise FileNotFoundError(f"No yearly level-0 pixel CSVs found in {level0_dir}")
    return years


def generate_level0_averages(
    years: list[str] | None = None,
    pixels_dir: Path = DEFAULT_PIXELS_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> None:
    if years is None:
        years = available_years(pixels_dir)
    for year in years:
        pixels_path = pixels_dir / "level0" / year / f"vnm_{year}{PIXEL_FILE_SUFFIX}"
        output_path = (
            output_dir / "level0" / year / f"vnm_{year}_average_radiance.csv"
        )
        write_average_csv([average_record("Vietnam", pixels_path)], output_path)


def generate_level1_averages(
    years: list[str] | None = None,
    pixels_dir: Path = DEFAULT_PIXELS_DIR,
    provinces: list[str] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> None:
    if years is None:
        years = available_years(pixels_dir)
    if provinces is None:
        provinces = read_provinces(DEFAULT_PROVINCES)
    province_rows = province_file_stems(provinces)
    for year in years:
        records = []
        for province, province_slug in province_rows:
            pixels_path = (
                pixels_dir
                / "level1"
                / year
                / f"{province_slug}_{year}{PIXEL_FILE_SUFFIX}"
            )
            records.append(average_record(province, pixels_path))

        output_path = (
            output_dir / "level1" / year / f"vnm_{year}_average_radiance.csv"
        )
        write_average_csv(records, output_path)


def generate_level2_averages(
    years: list[str] | None = None,
    pixels_dir: Path = DEFAULT_PIXELS_DIR,
    boundaries_dir: Path = DEFAULT_BOUNDARIES_DIR,
    provinces: list[str] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> None:
    if years is None:
        years = available_years(pixels_dir)
    if provinces is None:
        provinces = read_provinces(DEFAULT_PROVINCES)
    for province, province_slug in province_file_stems(provinces):
        boundary_path = (
            boundaries_dir / "level2" / province_slug / f"{province_slug}.shp"
        )
        if not boundary_path.is_file():
            raise FileNotFoundError(
                f"Level-2 boundary file not found: {boundary_path}"
            )
        boundaries = gpd.read_file(boundary_path)
        if "name" not in boundaries.columns:
            raise ValueError(
                f"Level-2 boundary is missing the 'name' field: {boundary_path}"
            )
        unit_names = (
            boundaries["name"].dropna().astype(str).str.strip().unique().tolist()
        )
        unit_names = [name for name in unit_names if name]
        unit_slugs = unique_level2_slugs(unit_names)

        for year in years:
            records = []
            for unit_name, unit_slug in zip(unit_names, unit_slugs):
                pixels_path = (
                    pixels_dir
                    / "level2"
                    / province_slug
                    / year
                    / f"{unit_slug}_{year}{PIXEL_FILE_SUFFIX}"
                )
                if not pixels_path.is_file():
                    raise FileNotFoundError(
                        f"Level-2 pixel CSV not found: {pixels_path}"
                    )
                records.append(average_record(unit_name, pixels_path))

            output_path = (
                output_dir
                / "level2"
                / province_slug
                / year
                / f"{province_slug}_{year}_average_radiance.csv"
            )
            write_average_csv(records, output_path)


def main() -> None:
    generate_level0_averages()
    generate_level1_averages()
    generate_level2_averages()


if __name__ == "__main__":
    main()
