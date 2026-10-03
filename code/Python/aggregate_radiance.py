"""Compute mean 2025 VIIRS radiance for each current Hanoi commune or ward."""

import argparse
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PIXELS = (
	PROJECT_ROOT
	/ "data"
	/ "viirs_pixel_radiance_province"
	/ "2025"
	/ "ha_noi_viirs_2025_pixel_radiance.csv"
)
DEFAULT_BOUNDARIES = (
	PROJECT_ROOT / "data" / "vnm_district_boundaries" / "ha_noi" / "ha_noi.shp"
)
DEFAULT_OUTPUT = (
	PROJECT_ROOT
	/ "data"
	/ "viiirs_regional_radiance_district"
	/ "2025"
	/ "ha_noi_2025_mean_radiance_by_commune.csv"
)


def aggregate_radiance(
	pixels_path: Path, boundaries_path: Path, output_path: Path
) -> pd.DataFrame:
	pixels = pd.read_csv(
		pixels_path,
		usecols=("longitude", "latitude", "radiance"),
	)
	pixels = pixels.replace([np.inf, -np.inf], np.nan).dropna(
		subset=("longitude", "latitude", "radiance")
	)
	if pixels.empty:
		raise ValueError(f"CSV contains no valid pixels: {pixels_path}")

	boundaries = gpd.read_file(boundaries_path)
	if boundaries.crs is None:
		raise ValueError(f"Boundary file has no CRS: {boundaries_path}")
	required_fields = ("ma_xa", "ten_xa", "loai")
	missing_fields = [field for field in required_fields if field not in boundaries]
	if missing_fields:
		raise ValueError(f"Boundary file is missing fields: {missing_fields}")

	boundaries = boundaries.reset_index(drop=True)
	boundary_crs = boundaries.crs
	points = gpd.GeoDataFrame(
		pixels,
		geometry=gpd.points_from_xy(pixels["longitude"], pixels["latitude"]),
		crs="EPSG:4326",
	).to_crs(boundary_crs)

	assignments = gpd.sjoin(
		points[["radiance", "geometry"]],
		boundaries[["geometry"]],
		how="inner",
		predicate="within",
	)
	summary = assignments.groupby("index_right")["radiance"].agg(
		mean_radiance="mean",
		pixel_count="count",
	)
	result = boundaries.loc[:, required_fields].join(summary)
	result["pixel_count"] = result["pixel_count"].fillna(0).astype("int64")
	result = result.sort_values("ma_xa").reset_index(drop=True)

	output_path.parent.mkdir(parents=True, exist_ok=True)
	result.to_csv(output_path, index=False, na_rep="")
	print(f"Wrote {len(result)} commune/ward rows to {output_path.resolve()}")
	print(f"Assigned pixels: {int(result['pixel_count'].sum()):,}")
	return result


def main() -> None:
	parser = argparse.ArgumentParser(
		description=(
			"Compute mean 2025 VIIRS radiance for each current Hanoi commune or ward."
		)
	)
	parser.add_argument("--pixels", type=Path, default=DEFAULT_PIXELS)
	parser.add_argument("--boundaries", type=Path, default=DEFAULT_BOUNDARIES)
	parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
	args = parser.parse_args()
	aggregate_radiance(args.pixels, args.boundaries, args.output)


if __name__ == "__main__":
	main()
