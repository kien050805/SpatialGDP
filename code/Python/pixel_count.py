"""Count 2025 VIIRS pixels by commune, province, and nationally."""

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_YEAR = "2025"
DEFAULT_PIXELS_DIR = (
    PROJECT_ROOT / "data" / "viirs_pixel_radiance_province" / DEFAULT_YEAR
)
DEFAULT_BOUNDARIES_DIR = PROJECT_ROOT / "data" / "vnm_district_boundaries"
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "data" / "pixel_count" / f"vietnam_{DEFAULT_YEAR}_pixel_counts.csv"
)
def count_pixels_by_area(
    pixels_dir: Path, boundaries_dir: Path, output_path: Path, year: str
) -> pd.DataFrame:
    pixel_file_suffix = f"_viirs_{year}_pixel_radiance.csv"
    pixel_files = sorted(pixels_dir.glob(f"*{pixel_file_suffix}"))
    if not pixel_files:
        raise FileNotFoundError(f"No {year} province pixel CSVs found in {pixels_dir}")

    pixel_parts = []
    boundary_parts = []
    for pixels_path in pixel_files:
        province_slug = pixels_path.name.removesuffix(pixel_file_suffix)
        boundary_path = boundaries_dir / province_slug / f"{province_slug}.shp"
        if not boundary_path.is_file():
            raise FileNotFoundError(f"Missing province boundary file: {boundary_path}")

        pixels = pd.read_csv(
            pixels_path,
            usecols=("raster_row", "raster_col", "longitude", "latitude"),
        )
        if pixels.empty:
            raise ValueError(f"Pixel CSV is empty: {pixels_path}")
        if pixels.duplicated(["longitude", "latitude"]).any():
            raise ValueError(f"Duplicate pixel centers in {pixels_path}")
        pixels["source_province_slug"] = province_slug
        pixel_parts.append(pixels)

        boundaries = gpd.read_file(boundary_path)
        required_fields = ("ma_xa", "ten_xa", "loai", "ten_tinh")
        missing_fields = [field for field in required_fields if field not in boundaries]
        if missing_fields:
            raise ValueError(f"{boundary_path} is missing fields: {missing_fields}")
        if boundaries.crs is None:
            raise ValueError(f"Boundary file has no CRS: {boundary_path}")
        boundary_parts.append(boundaries.to_crs("EPSG:4326")[list(required_fields) + ["geometry"]])

    pixels = pd.concat(pixel_parts, ignore_index=True)
    duplicate_ids = pixels.duplicated(["longitude", "latitude"], keep=False)
    duplicate_id_count = pixels.loc[
        duplicate_ids, ["longitude", "latitude"]
    ].drop_duplicates().shape[0]
    pixels = pixels.drop_duplicates(["longitude", "latitude"])

    boundaries = gpd.GeoDataFrame(
        pd.concat(boundary_parts, ignore_index=True),
        geometry="geometry",
        crs="EPSG:4326",
    ).reset_index(drop=True)
    points = gpd.GeoDataFrame(
        pixels[["longitude", "latitude"]],
        geometry=gpd.points_from_xy(pixels["longitude"], pixels["latitude"]),
        crs="EPSG:4326",
    )
    assignments = gpd.sjoin(
        points,
        boundaries[["ma_xa", "ten_xa", "loai", "ten_tinh", "geometry"]],
        how="left",
        predicate="within",
    )
    unassigned = assignments["index_right"].isna()
    if unassigned.any():
        raise ValueError(
            f"{int(unassigned.sum())} unique pixels did not fall within a commune polygon. "
            "Check boundary coverage and CRS."
        )

    overlap_count = assignments.duplicated(["longitude", "latitude"], keep=False).sum()
    if overlap_count:
        areas = boundaries.to_crs("EPSG:6933").geometry.area.rename("polygon_area")
        assignments = assignments.join(areas, on="index_right")
        assignments = assignments.sort_values(
            ["longitude", "latitude", "polygon_area", "ma_xa"],
            kind="stable",
        ).drop_duplicates(["longitude", "latitude"])
    counts = assignments.groupby("index_right").size().rename("pixel_count")
    commune_counts = boundaries[
        ["ma_xa", "ten_xa", "loai", "ten_tinh"]
    ].join(counts)
    commune_counts["pixel_count"] = commune_counts["pixel_count"].fillna(0).astype("int64")
    commune_counts = commune_counts.rename(
        columns={"ma_xa": "unit_code", "ten_xa": "unit_name", "loai": "unit_type", "ten_tinh": "province"}
    )
    commune_counts.insert(0, "administrative_level", "commune")
    commune_counts["year"] = year
    commune_counts["unit_name"] = commune_counts["unit_name"].astype(str)
    commune_counts["unit_code"] = commune_counts["unit_code"].astype(str)
    commune_counts = commune_counts[
        [
            "year",
            "administrative_level",
            "province",
            "unit_code",
            "unit_name",
            "unit_type",
            "pixel_count",
        ]
    ]
    province_counts = (
        commune_counts.groupby("province", as_index=False)["pixel_count"]
        .sum()
        .assign(
            year=year,
            administrative_level="province",
            unit_code="",
            unit_name="",
            unit_type="",
        )
    )[
        [
            "year",
            "administrative_level",
            "province",
            "unit_code",
            "unit_name",
            "unit_type",
            "pixel_count",
        ]
    ]
    national_count = int(province_counts["pixel_count"].sum())
    national = pd.DataFrame(
        [
            {
                "year": year,
                "administrative_level": "national",
                "province": "Vietnam",
                "unit_code": "",
                "unit_name": "",
                "unit_type": "",
                "pixel_count": national_count,
            }
        ]
    )

    result = pd.concat([commune_counts, province_counts, national], ignore_index=True)
    result = result.sort_values(
        ["administrative_level", "province", "unit_code"], kind="stable"
    ).reset_index(drop=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    print(f"Wrote {len(result):,} rows to {output_path.resolve()}")
    print(
        f"Counted {len(commune_counts):,} commune rows across "
        f"{len(province_counts):,} provinces; national total: {national_count:,} pixels."
    )
    if duplicate_id_count:
        print(f"Deduplicated {duplicate_id_count:,} repeated pixel centers across province CSVs.")
    if overlap_count:
        print(f"Resolved {overlap_count:,} overlapping commune matches using smallest polygon.")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Count VIIRS pixels by commune, province, and nationally."
    )
    parser.add_argument("--year", default=DEFAULT_YEAR)
    parser.add_argument("--pixels-dir", type=Path, default=DEFAULT_PIXELS_DIR)
    parser.add_argument("--boundaries-dir", type=Path, default=DEFAULT_BOUNDARIES_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    count_pixels_by_area(args.pixels_dir, args.boundaries_dir, args.output, args.year)


if __name__ == "__main__":
    main()