"""
Wrangling all shp files for consistency and usability. This includes:
- Preparing level-0 (country) boundaries
- Preparing level-1 (province) boundaries
- Preparing level-2 (district) boundaries

This script only apply for the data provided in the repository.
Author: Kien Le
AI disclosure: This code was generated with the assistance of AI. The author has reviewed and edited the code to ensure its accuracy and functionality.
Last Update: 2026-18-10
"""
from pathlib import Path
import re
import unicodedata

import geopandas as gpd
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ADMIN0_SOURCE = PROJECT_ROOT / "data" / "vnm_admin_boundaries" / "vnm_admin0.shp"
ADMIN0_SOURCE_ALTERNATE = (
    PROJECT_ROOT / "data" / "_vnm_admin_boundaries" / "vnm_admin0.shp"
)
LEVEL0_OUTPUT = (
    PROJECT_ROOT / "data" / "shp_boundaries" / "level0" / "vnm_level0.shp"
)
ADMIN1_SOURCE = PROJECT_ROOT / "data" / "_vnm_admin_boundaries" / "vnm_admin1.shp"
PROVINCES_SOURCE = PROJECT_ROOT / "data" / "_vnm_indicators" / "vnm_provinces.csv"
LEVEL1_OUTPUT = (
    PROJECT_ROOT / "data" / "shp_boundaries" / "level1" / "vnm_level1.shp"
)
DISTRICT_BOUNDARIES = PROJECT_ROOT / "data" / "vnm_district_boundaries"
DISTRICT_BOUNDARIES_ALTERNATE = PROJECT_ROOT / "data" / "_vnm_district_boundaries"
LEVEL2_OUTPUT_DIR = PROJECT_ROOT / "data" / "shp_boundaries" / "level2"


def province_slug(province: str) -> str:
	normalized = province.replace("Đ", "D").replace("đ", "d")
	normalized = unicodedata.normalize("NFKD", normalized)
	ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
	return re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")


def prepare_level0_boundary(
    source_path: Path = ADMIN0_SOURCE,
    output_path: Path = LEVEL0_OUTPUT,
) -> Path:
    if not source_path.is_file() and source_path == ADMIN0_SOURCE:
        source_path = ADMIN0_SOURCE_ALTERNATE
    if not source_path.is_file():
        raise FileNotFoundError(f"Admin-0 boundary file not found: {source_path}")

    boundaries = gpd.read_file(source_path)
    name_field = "adm0_name"
    required_fields = {name_field, "area_sqkm"}
    missing_fields = required_fields - set(boundaries.columns)
    if missing_fields:
        raise ValueError(
            f"Admin-0 boundary file is missing required fields "
            f"{sorted(missing_fields)}: {source_path}"
        )
    if boundaries.crs is None:
        raise ValueError(f"Admin-0 boundary file has no CRS: {source_path}")

    geometry_field = boundaries.geometry.name
    level0 = boundaries[[name_field, "area_sqkm", geometry_field]].rename(
        columns={name_field: "name"}
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    level0.to_file(output_path, driver="ESRI Shapefile", index=False)
    print(f"Wrote admin-0 boundary to {output_path.resolve()}")
    return output_path


def province_key(name: str) -> str:
    normalized = name.strip().casefold()
    if normalized.endswith(" city"):
        normalized = normalized[:-5].strip()
    return normalized


def prepare_level1_boundary(
    source_path: Path = ADMIN1_SOURCE,
    provinces_path: Path = PROVINCES_SOURCE,
    output_path: Path = LEVEL1_OUTPUT,
) -> Path:
    if not source_path.is_file():
        raise FileNotFoundError(f"Admin-1 boundary file not found: {source_path}")
    if not provinces_path.is_file():
        raise FileNotFoundError(f"Province labels file not found: {provinces_path}")

    boundaries = gpd.read_file(source_path)
    province_name_field = "adm1_name"
    required_fields = {province_name_field, "area_sqkm"}
    missing_fields = required_fields - set(boundaries.columns)
    if missing_fields:
        raise ValueError(
            f"Admin-1 boundary file is missing required fields "
            f"{sorted(missing_fields)}: {source_path}"
        )
    if boundaries.crs is None:
        raise ValueError(f"Admin-1 boundary file has no CRS: {source_path}")

    provinces = pd.read_csv(provinces_path, encoding="utf-8-sig")
    if "province" not in provinces.columns:
        raise ValueError(
            f"Province labels file is missing the 'province' column: {provinces_path}"
        )
    province_names = provinces["province"].dropna().astype(str).str.strip()
    province_names = province_names[province_names.ne("")]
    if province_names.empty or province_names.duplicated().any():
        raise ValueError(
            f"Province labels must be non-empty and unique: {provinces_path}"
        )

    names_by_key = {}
    for name in province_names:
        key = province_key(name)
        if key in names_by_key:
            raise ValueError(
                f"Province labels are ambiguous after city-name normalization: "
                f"{names_by_key[key]!r} and {name!r}"
            )
        names_by_key[key] = name

    source_names = boundaries[province_name_field].dropna().astype(str).str.strip()
    boundary_indices_by_key = {}
    for index, name in source_names.items():
        key = province_key(name)
        if key in boundary_indices_by_key:
            raise ValueError(
                f"Admin-1 boundary names are ambiguous after normalization: {name!r}"
            )
        boundary_indices_by_key[key] = index

    missing_boundaries = [
        name for key, name in names_by_key.items() if key not in boundary_indices_by_key
    ]
    unmatched_boundaries = [
        source_names.loc[index]
        for key, index in boundary_indices_by_key.items()
        if key not in names_by_key
    ]
    if missing_boundaries or unmatched_boundaries:
        raise ValueError(
            "Province labels and admin-1 boundaries do not match. "
            f"Missing boundaries for: {missing_boundaries}; "
            f"unmatched boundary names: {unmatched_boundaries}"
        )

    ordered_indices = [
        boundary_indices_by_key[province_key(name)] for name in province_names
    ]
    geometry_field = boundaries.geometry.name
    level1 = boundaries.loc[
        ordered_indices, [province_name_field, "area_sqkm", geometry_field]
    ].copy()
    level1["name"] = province_names.to_list()
    level1 = level1[["name", "area_sqkm", geometry_field]]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    level1.to_file(output_path, driver="ESRI Shapefile", index=False)
    print(f"Wrote admin-1 boundary to {output_path.resolve()}")
    return output_path


def prepare_level2_boundary(
    source_dir: Path = DISTRICT_BOUNDARIES,
    provinces_path: Path = PROVINCES_SOURCE,
    output_dir: Path = LEVEL2_OUTPUT_DIR,
) -> list[Path]:
    if not source_dir.is_dir() and source_dir == DISTRICT_BOUNDARIES:
        source_dir = DISTRICT_BOUNDARIES_ALTERNATE
    if not source_dir.is_dir():
        raise FileNotFoundError(f"District boundary directory not found: {source_dir}")
    if not provinces_path.is_file():
        raise FileNotFoundError(f"Province labels file not found: {provinces_path}")

    provinces = pd.read_csv(provinces_path, encoding="utf-8-sig")
    if "province" not in provinces.columns:
        raise ValueError(
            f"Province labels file is missing the 'province' column: {provinces_path}"
        )
    province_names = provinces["province"].dropna().astype(str).str.strip()
    province_names = province_names[province_names.ne("")]
    if province_names.empty or province_names.duplicated().any():
        raise ValueError(
            f"Province labels must be non-empty and unique: {provinces_path}"
        )

    province_directories = {}
    for province in province_names:
        slug = province_slug(province)
        if not slug or slug in province_directories:
            raise ValueError(
                f"Province names produce an invalid or duplicate directory: {province!r}"
            )
        province_directories[slug] = province

    parent_aliases = {"tp_ho_chi_minh": "ho_chi_minh_city"}
    outputs = []
    for slug, province in province_directories.items():
        source_path = source_dir / slug / f"{slug}.shp"
        if not source_path.is_file():
            raise FileNotFoundError(
                f"Missing level-2 boundary for {province}: {source_path}"
            )

        boundaries = gpd.read_file(source_path)
        required_fields = {"ten_xa", "dtich_km2", "ten_tinh"}
        missing_fields = required_fields - set(boundaries.columns)
        if missing_fields:
            raise ValueError(
                f"Level-2 boundary is missing fields {sorted(missing_fields)}: "
                f"{source_path}"
            )
        if boundaries.crs is None:
            raise ValueError(f"Level-2 boundary has no CRS: {source_path}")

        parent_names = (
            boundaries["ten_tinh"].dropna().astype(str).str.strip().unique()
        )
        parent_keys = {
            parent_aliases.get(province_slug(name), province_slug(name))
            for name in parent_names
        }
        if parent_keys != {slug}:
            raise ValueError(
                f"Level-2 parent province does not match {province!r} in "
                f"{source_path}: {parent_names.tolist()}"
            )

        geometry_field = boundaries.geometry.name
        level2 = boundaries[["ten_xa", "dtich_km2", geometry_field]].rename(
            columns={"ten_xa": "name", "dtich_km2": "area_sqkm"}
        )
        output_path = output_dir / slug / f"{slug}.shp"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        level2.to_file(output_path, driver="ESRI Shapefile", index=False)
        outputs.append(output_path)
        print(
            f"Wrote {len(level2)} level-2 boundaries for {province} to "
            f"{output_path.resolve()}"
        )

    return outputs



def main() -> None:
    prepare_level0_boundary()
    prepare_level1_boundary()
    prepare_level2_boundary()


if __name__ == "__main__":
    main()