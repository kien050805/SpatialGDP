"""
Plot Vietnam's extracted VIIRS radiance pixels from the CSV.
Author: Kien Le
AI disclosure: This code was generated with the assistance of AI. The author has reviewed and edited the code to ensure its accuracy and functionality.
Last Update: 2021-09-30   
"""

import argparse
from pathlib import Path
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import PowerNorm


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = (
    PROJECT_ROOT
    / "data"
    / "viirs_pixel_radiance"
    / "vietnam_viirs_2021_pixel_radiance.csv"
)
DEFAULT_BOUNDARY = (
    PROJECT_ROOT / "data" / "vnm_admin_boundaries.shp" / "vnm_admin0.shp"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "figures" / "vietnam_viirs_2021_radiance.png"
DEFAULT_ADMIN1_BOUNDARY = (
    PROJECT_ROOT / "data" / "vnm_admin_boundaries.shp" / "vnm_admin1.shp"
)
DEFAULT_PROVINCIAL_OUTPUT = (
    PROJECT_ROOT / "figures" / "vietnam_viirs_2021_provincial_radiance.png"
)


def create_figure(
    csv_path: Path,
    boundary_path: Path,
    output_path: Path,
    title: str = "Vietnam | NPP-VIIRS Nighttime Radiance, 2021",
) -> None:
    pixels = pd.read_csv(
        csv_path,
        usecols=("raster_row", "raster_col", "longitude", "latitude", "radiance"),
    )
    pixels = pixels.replace([np.inf, -np.inf], np.nan).dropna()
    if pixels.empty:
        raise ValueError(f"CSV contains no valid pixels: {csv_path}")

    row_min = int(pixels["raster_row"].min())
    row_max = int(pixels["raster_row"].max())
    col_min = int(pixels["raster_col"].min())
    col_max = int(pixels["raster_col"].max())
    radiance_grid = np.full(
        (row_max - row_min + 1, col_max - col_min + 1), np.nan, dtype=np.float32
    )
    row_indices = pixels["raster_row"].to_numpy(dtype=np.int64) - row_min
    col_indices = pixels["raster_col"].to_numpy(dtype=np.int64) - col_min
    radiance_grid[row_indices, col_indices] = pixels["radiance"].to_numpy(
        dtype=np.float32
    )

    longitude_by_col = pixels.groupby("raster_col")["longitude"].median().sort_index()
    latitude_by_row = pixels.groupby("raster_row")["latitude"].median().sort_index()
    longitude_step = float(longitude_by_col.diff().abs().median())
    latitude_step = float(latitude_by_row.diff().abs().median())
    extent = (
        float(longitude_by_col.iloc[0] - longitude_step / 2),
        float(longitude_by_col.iloc[-1] + longitude_step / 2),
        float(latitude_by_row.min() - latitude_step / 2),
        float(latitude_by_row.max() + latitude_step / 2),
    )

    positive_radiance = pixels.loc[pixels["radiance"] > 0, "radiance"]
    if positive_radiance.empty:
        raise ValueError("All included pixels have zero radiance; nothing to visualize.")
    upper_limit = float(positive_radiance.quantile(0.995))

    boundary = gpd.read_file(boundary_path)
    if boundary.crs is None:
        raise ValueError(f"Boundary file has no CRS: {boundary_path}")
    boundary = boundary.to_crs("EPSG:4326")

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
    boundary.boundary.plot(ax=axis, color="#54e0d0", linewidth=0.7)

    axis.set_title(
        title,
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
    axis.set_xlim(float(boundary.total_bounds[0]), float(boundary.total_bounds[2]))
    axis.set_ylim(float(boundary.total_bounds[1]), float(boundary.total_bounds[3]))
    colorbar = figure.colorbar(image, ax=axis, fraction=0.045, pad=0.03)
    colorbar.ax.set_facecolor("#11100f")
    colorbar.set_label("Radiance (99.5th percentile stretch)", color="#d8d3cb")
    colorbar.ax.tick_params(colors="#d8d3cb")
    colorbar.outline.set_edgecolor("#5c5750")
    figure.savefig(output_path, dpi=250, facecolor="#11100f")
    plt.close(figure)
    print(f"Saved figure to {output_path.resolve()}")


def create_provincial_figure(
    csv_path: Path,
    boundary_path: Path = DEFAULT_ADMIN1_BOUNDARY,
    output_path: Path = DEFAULT_PROVINCIAL_OUTPUT,
) -> None:
    create_figure(
        csv_path,
        boundary_path,
        output_path,
        title="Vietnam | NPP-VIIRS Nighttime Radiance, 2021 | Provincial Borders",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a map of extracted Vietnam VIIRS radiance pixels."
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--boundary", type=Path, default=DEFAULT_BOUNDARY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--admin1-boundary", type=Path, default=DEFAULT_ADMIN1_BOUNDARY)
    parser.add_argument(
        "--provincial-output", type=Path, default=DEFAULT_PROVINCIAL_OUTPUT
    )
    args = parser.parse_args()
    create_figure(args.csv, args.boundary, args.output)
    create_provincial_figure(args.csv, args.admin1_boundary, args.provincial_output)


if __name__ == "__main__":
    main()