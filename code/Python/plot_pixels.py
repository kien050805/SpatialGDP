"""Plot extracted VIIRS pixel radiance over Vietnam's prepared boundaries."""

from __future__ import annotations

import argparse
import unicodedata
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import PowerNorm

from utils import name_slug


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PIXELS_DIR = PROJECT_ROOT / "data" / "viirs_pixel_radiance"
DEFAULT_BOUNDARIES_DIR = PROJECT_ROOT / "data" / "shp_boundaries"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "figures"
PIXEL_FILE_SUFFIX = "_pixel_radiance.csv"
PIXEL_COLUMNS = ("raster_row", "raster_col", "longitude", "latitude", "radiance")


def name_key(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(unicodedata.normalize("NFC", str(value)).split()).casefold()


def available_years(pixels_dir: Path) -> list[int]:
    level0_dir = pixels_dir / "level0"
    if not level0_dir.is_dir():
        raise FileNotFoundError(f"Level-0 pixel directory not found: {level0_dir}")

    years = []
    for year_dir in level0_dir.iterdir():
        if not year_dir.is_dir():
            continue
        try:
            year = int(year_dir.name)
        except ValueError:
            continue
        if (year_dir / f"vnm_{year}{PIXEL_FILE_SUFFIX}").is_file():
            years.append(year)
    if not years:
        raise FileNotFoundError(f"No yearly level-0 pixel CSVs found in {level0_dir}")
    return sorted(years)


def read_level1_boundaries(boundaries_dir: Path) -> gpd.GeoDataFrame:
    path = boundaries_dir / "level1" / "vnm_level1.shp"
    boundaries = gpd.read_file(path)
    if boundaries.crs is None:
        raise ValueError(f"Boundary file has no CRS: {path}")
    if "name" not in boundaries.columns:
        raise ValueError(f"Boundary file must contain a 'name' column: {path}")
    return boundaries.to_crs("EPSG:4326")


def resolve_province(
    province: str, level1_boundaries: gpd.GeoDataFrame
) -> tuple[str, str]:
    matches = level1_boundaries.loc[
        level1_boundaries["name"].map(name_key) == name_key(province), "name"
    ].dropna()
    if matches.empty:
        available = ", ".join(sorted(level1_boundaries["name"].dropna().astype(str)))
        raise ValueError(
            f"Province {province!r} was not found in the level-1 boundaries. "
            f"Available provinces: {available}"
        )
    province_name = str(matches.iloc[0])
    return province_name, name_slug(province_name)


def read_boundaries(
    level: int, boundaries_dir: Path, province: str | None
) -> gpd.GeoDataFrame:
    if level == 0:
        if province:
            raise ValueError("The --province filter is only supported for level 2.")
        path = boundaries_dir / "level0" / "vnm_level0.shp"
        boundaries = gpd.read_file(path)
        if boundaries.crs is None:
            raise ValueError(f"Boundary file has no CRS: {path}")
        return boundaries.to_crs("EPSG:4326")

    level1 = read_level1_boundaries(boundaries_dir)
    if level == 1:
        if province:
            raise ValueError("The --province filter is only supported for level 2.")
        return level1

    provinces = level1["name"].dropna().astype(str).drop_duplicates().tolist()
    province_slugs = [name_slug(name) for name in provinces]
    if len(set(province_slugs)) != len(province_slugs):
        raise ValueError("Level-1 boundary names have ambiguous directory slugs.")

    selected_province = None
    if province:
        selected_province = resolve_province(province, level1)
        province_names = [selected_province[0]]
    else:
        province_names = provinces

    features = []
    for province_name in province_names:
        province_slug = name_slug(province_name)
        path = (
            boundaries_dir
            / "level2"
            / province_slug
            / f"{province_slug}.shp"
        )
        boundary = gpd.read_file(path)
        if boundary.crs is None:
            raise ValueError(f"Boundary file has no CRS: {path}")
        if "name" not in boundary.columns:
            raise ValueError(f"Boundary file must contain a 'name' column: {path}")
        boundary = boundary.to_crs("EPSG:4326")
        features.append(boundary[["name", "geometry"]])

    if not features:
        raise FileNotFoundError(f"No level-2 boundaries found under {boundaries_dir}")
    return gpd.GeoDataFrame(
        pd.concat(features, ignore_index=True),
        geometry="geometry",
        crs="EPSG:4326",
    )


def pixel_csv_paths(
    pixels_dir: Path, level: int, year: int, boundaries_dir: Path, province: str | None
) -> list[Path]:
    if level in (0, 1):
        return [
            pixels_dir
            / "level0"
            / str(year)
            / f"vnm_{year}{PIXEL_FILE_SUFFIX}"
        ]

    level1 = read_level1_boundaries(boundaries_dir)
    if province:
        province_names = [resolve_province(province, level1)[0]]
    else:
        province_names = (
            level1["name"].dropna().astype(str).drop_duplicates().tolist()
        )

    return [
        pixels_dir
        / "level1"
        / str(year)
        / f"{name_slug(province_name)}_{year}{PIXEL_FILE_SUFFIX}"
        for province_name in province_names
    ]


def read_pixels(paths: list[Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"Pixel-radiance CSV not found: {path}")
        frames.append(pd.read_csv(path, usecols=PIXEL_COLUMNS))
    if not frames:
        raise FileNotFoundError("No pixel-radiance CSVs were selected.")

    pixels = pd.concat(frames, ignore_index=True)
    for column in PIXEL_COLUMNS:
        pixels[column] = pd.to_numeric(pixels[column], errors="coerce")
    pixels = pixels.replace([np.inf, -np.inf], np.nan).dropna(
        subset=PIXEL_COLUMNS
    )
    if pixels.empty:
        raise ValueError("Selected CSV files contain no valid pixels.")
    if not np.equal(
        pixels[["raster_row", "raster_col"]].to_numpy(),
        np.round(pixels[["raster_row", "raster_col"]].to_numpy()),
    ).all():
        raise ValueError("Pixel CSV raster rows and columns must be integers.")

    pixels["raster_row"] = pixels["raster_row"].astype(np.int64)
    pixels["raster_col"] = pixels["raster_col"].astype(np.int64)
    return pixels.drop_duplicates(("raster_row", "raster_col"))


def pixel_step(coordinates: pd.Series) -> float | None:
    coordinate_values = coordinates.to_numpy(dtype=float)
    index_values = coordinates.index.to_numpy(dtype=float)
    index_differences = np.diff(index_values)
    differences = np.abs(np.diff(coordinate_values) / index_differences)
    differences = differences[np.isfinite(differences) & (differences > 0)]
    return float(np.median(differences)) if differences.size else None


def create_figure(
    pixels_dir: Path,
    boundaries_dir: Path,
    output_path: Path,
    level: int,
    year: int,
    province: str | None = None,
) -> None:
    if level not in (0, 1, 2):
        raise ValueError(f"Administrative level must be 0, 1, or 2, not {level}.")
    if province and level != 2:
        raise ValueError("The --province filter is only supported for level 2.")

    boundaries = read_boundaries(level, boundaries_dir, province)
    paths = pixel_csv_paths(pixels_dir, level, year, boundaries_dir, province)
    pixels = read_pixels(paths)

    row_min, row_max = int(pixels["raster_row"].min()), int(pixels["raster_row"].max())
    col_min, col_max = int(pixels["raster_col"].min()), int(pixels["raster_col"].max())
    radiance_grid = np.full(
        (row_max - row_min + 1, col_max - col_min + 1),
        np.nan,
        dtype=np.float32,
    )
    row_indices = pixels["raster_row"].to_numpy() - row_min
    col_indices = pixels["raster_col"].to_numpy() - col_min
    radiance_grid[row_indices, col_indices] = pixels["radiance"].to_numpy(
        dtype=np.float32
    )

    longitude_by_col = pixels.groupby("raster_col")["longitude"].median().sort_index()
    latitude_by_row = pixels.groupby("raster_row")["latitude"].median().sort_index()
    longitude_step = pixel_step(longitude_by_col)
    latitude_step = pixel_step(latitude_by_row)
    if longitude_step is None:
        longitude_step = latitude_step
    if latitude_step is None:
        latitude_step = longitude_step
    if longitude_step is None or latitude_step is None:
        raise ValueError("Cannot determine pixel dimensions from the selected CSVs.")
    extent = (
        float(longitude_by_col.min() - longitude_step / 2),
        float(longitude_by_col.max() + longitude_step / 2),
        float(latitude_by_row.min() - latitude_step / 2),
        float(latitude_by_row.max() + latitude_step / 2),
    )

    positive_radiance = pixels.loc[pixels["radiance"] > 0, "radiance"]
    if positive_radiance.empty:
        raise ValueError("All included pixels have zero radiance; nothing to visualize.")
    upper_limit = float(positive_radiance.quantile(0.995))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(8, 10), layout="constrained")
    figure.set_facecolor("#11100f")
    axis.set_facecolor("#11100f")
    image = axis.imshow(
        radiance_grid,
        extent=extent,
        origin="upper",
        interpolation="nearest",
        cmap="inferno",
        norm=PowerNorm(gamma=0.45, vmin=0, vmax=upper_limit),
        rasterized=True,
    )
    boundaries.boundary.plot(ax=axis, color="#54e0d0", linewidth=0.5)

    subject = province or "Vietnam"
    axis.set_title(
        f"{subject} | NPP-VIIRS Nighttime Radiance | Level {level} | {year}",
        loc="left",
        pad=12,
        color="#f2eee8",
    )
    axis.set_xlabel("Longitude", color="#d8d3cb")
    axis.set_ylabel("Latitude", color="#d8d3cb")
    axis.tick_params(colors="#d8d3cb")
    for spine in axis.spines.values():
        spine.set_color("#5c5750")
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlim(float(boundaries.total_bounds[0]), float(boundaries.total_bounds[2]))
    axis.set_ylim(float(boundaries.total_bounds[1]), float(boundaries.total_bounds[3]))
    colorbar = figure.colorbar(image, ax=axis, fraction=0.045, pad=0.03)
    colorbar.ax.set_facecolor("#11100f")
    colorbar.set_label("Radiance (99.5th percentile stretch)", color="#d8d3cb")
    colorbar.ax.tick_params(colors="#d8d3cb")
    colorbar.outline.set_edgecolor("#5c5750")
    figure.savefig(output_path, dpi=250, facecolor="#11100f")
    plt.close(figure)
    print(f"Saved figure to {output_path.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot extracted VIIRS radiance pixels over prepared boundaries."
    )
    parser.add_argument("--pixels-dir", type=Path, default=DEFAULT_PIXELS_DIR)
    parser.add_argument("--boundaries-dir", type=Path, default=DEFAULT_BOUNDARIES_DIR)
    parser.add_argument("--level", type=int, choices=(0, 1, 2), default=0)
    parser.add_argument("--year", type=int)
    parser.add_argument(
        "--province",
        help="Plot only this province's level-2 units, e.g. 'Quang Ninh'.",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    years = available_years(args.pixels_dir)
    year = args.year if args.year is not None else years[-1]
    if year not in years:
        raise ValueError(
            f"No level-0 pixel CSV found for {year}. Available years: "
            f"{', '.join(map(str, years))}"
        )
    province_prefix = f"{name_slug(args.province)}_" if args.province else ""
    output_path = args.output or (
        DEFAULT_OUTPUT_DIR
        / f"{province_prefix}level{args.level}_viirs_radiance_{year}.png"
    )
    create_figure(
        args.pixels_dir,
        args.boundaries_dir,
        output_path,
        level=args.level,
        year=year,
        province=args.province,
    )


if __name__ == "__main__":
    main()
