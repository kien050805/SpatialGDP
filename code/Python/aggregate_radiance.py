"""Compute mean 2025 VIIRS radiance for each Vietnamese province."""

import argparse
import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PIXELS = (
	PROJECT_ROOT
	/ "data"
	/ "viirs_pixel_radiance"
	/ "vietnam_viirs_2025_pixel_radiance.csv"
)
DEFAULT_BOUNDARIES = (
	PROJECT_ROOT / "data" / "vnm_admin_boundaries.shp" / "vnm_admin1.shp"
)
DEFAULT_POPULATION = PROJECT_ROOT / "data" / "vnm_population.csv"
DEFAULT_OUTPUT = (
	PROJECT_ROOT
	/ "data"
	/ "viiirs_average_radiance"
	/ "vietnam_2025_mean_radiance_by_province.csv"
)


def province_slug(province: str) -> str:
	normalized = province.replace("Đ", "D").replace("đ", "d")
	normalized = unicodedata.normalize("NFKD", normalized)
	ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
	return re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")


def aggregate_radiance(
	pixels_path: Path,
	boundaries_path: Path,
	output_path: Path,
	population_path: Path = DEFAULT_POPULATION,
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
	province_name_field = "adm1_name"
	if province_name_field not in boundaries:
		raise ValueError(
			f"Boundary file is missing province-name field "
			f"{province_name_field!r}: {boundaries_path}"
		)
	population_data = pd.read_csv(population_path, encoding="utf-8-sig")
	if "Provincies" not in population_data:
		raise ValueError(
			f"Population file is missing the 'Provincies' column: {population_path}"
		)
	province_names = (
		population_data["Provincies"]
		.dropna()
		.astype(str)
		.str.strip()
	)
	province_names = province_names[province_names.ne("")]
	if province_names.empty or province_names.duplicated().any():
		raise ValueError(
			f"Population file must contain unique province names: {population_path}"
		)

	population_names_by_slug = {}
	for name in province_names:
		slug = province_slug(name)
		if slug in population_names_by_slug:
			raise ValueError(
				f"Province names normalize to the same value in {population_path}: "
				f"{population_names_by_slug[slug]!r} and {name!r}"
			)
		population_names_by_slug[slug] = name
	admin_names_by_slug = dict(population_names_by_slug)
	for slug, name in population_names_by_slug.items():
		city_slug = f"{slug}_city"
		if city_slug in admin_names_by_slug and admin_names_by_slug[city_slug] != name:
			raise ValueError(
				f"Ambiguous province-name mapping in {population_path}: {name}"
			)
		admin_names_by_slug[city_slug] = name

	boundaries = boundaries.reset_index(drop=True)
	boundaries["province"] = boundaries[province_name_field].map(
		lambda name: admin_names_by_slug.get(province_slug(name))
	)
	unmatched_names = boundaries.loc[
		boundaries["province"].isna(), province_name_field
	].drop_duplicates()
	if not unmatched_names.empty:
		raise ValueError(
			"Province names in boundary file do not match the population file: "
			f"{unmatched_names.tolist()}"
		)
	missing_provinces = set(province_names) - set(boundaries["province"])
	if missing_provinces:
		raise ValueError(
			"Population file provinces are missing from the boundary file: "
			f"{sorted(missing_provinces)}"
		)

	boundary_crs = boundaries.crs
	points = gpd.GeoDataFrame(
		pixels,
		geometry=gpd.points_from_xy(pixels["longitude"], pixels["latitude"]),
		crs="EPSG:4326",
	).to_crs(boundary_crs)

	assignments = gpd.sjoin(
		points[["radiance", "geometry"]],
		boundaries[["province", "geometry"]],
		how="inner",
		predicate="within",
	)
	summary = assignments.groupby("province")["radiance"].agg(
		mean_radiance="mean",
		pixel_count="count",
	)
	provinces = pd.DataFrame({"province": province_names}).set_index("province")
	result = provinces.join(summary).reset_index()
	result["pixel_count"] = result["pixel_count"].fillna(0).astype("int64")

	output_path.parent.mkdir(parents=True, exist_ok=True)
	result.to_csv(output_path, index=False, na_rep="")
	print(f"Wrote {len(result)} province rows to {output_path.resolve()}")
	print(f"Assigned pixels: {int(result['pixel_count'].sum()):,}")
	return result


def main() -> None:
	parser = argparse.ArgumentParser(
		description=(
			"Compute mean 2025 VIIRS radiance for each Vietnamese province."
		)
	)
	parser.add_argument("--pixels", type=Path, default=DEFAULT_PIXELS)
	parser.add_argument("--boundaries", type=Path, default=DEFAULT_BOUNDARIES)
	parser.add_argument("--population", type=Path, default=DEFAULT_POPULATION)
	parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
	args = parser.parse_args()
	aggregate_radiance(
		args.pixels, args.boundaries, args.output, population_path=args.population
	)


if __name__ == "__main__":
	main()
