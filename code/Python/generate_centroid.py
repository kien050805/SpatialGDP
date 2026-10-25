"""Generate geographic centroids for Vietnam's prepared administrative boundaries."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BOUNDARIES_DIR = PROJECT_ROOT / "data" / "shp_boundaries"
OUTPUT_DIR = PROJECT_ROOT / "data" / "centroid"
CENTROID_CRS = "EPSG:6933"
OUTPUT_CRS = "EPSG:4326"


def add_centroid_coordinates(boundaries: gpd.GeoDataFrame) -> pd.DataFrame:
    if boundaries.crs is None:
        raise ValueError("A boundary file is missing its coordinate reference system.")
    if "name" not in boundaries.columns:
        raise ValueError("A boundary file is missing the required 'name' column.")
    if boundaries.geometry.isna().any() or boundaries.geometry.is_empty.any():
        raise ValueError("A boundary file contains empty geometries.")

    projected = boundaries.to_crs(CENTROID_CRS)
    centroids = projected.geometry.centroid
    geographic = gpd.GeoSeries(centroids, crs=CENTROID_CRS).to_crs(OUTPUT_CRS)
    result = boundaries.drop(columns="geometry").copy()
    result["latitude"] = geographic.y
    result["longitude"] = geographic.x
    return result


def generate_level0() -> Path:
    path = BOUNDARIES_DIR / "level0" / "vnm_level0.shp"
    boundaries = gpd.read_file(path)
    centroids = add_centroid_coordinates(boundaries)
    centroids.insert(0, "level", 0)
    return write_centroids(centroids, "level0_centroids.csv")


def generate_level1() -> Path:
    path = BOUNDARIES_DIR / "level1" / "vnm_level1.shp"
    boundaries = gpd.read_file(path)
    centroids = add_centroid_coordinates(boundaries)
    centroids.insert(0, "level", 1)
    return write_centroids(centroids, "level1_centroids.csv")


def generate_level2() -> Path:
    shapefiles = sorted((BOUNDARIES_DIR / "level2").glob("*/*.shp"))
    if not shapefiles:
        raise FileNotFoundError(
            f"No level-2 shapefiles found under {BOUNDARIES_DIR / 'level2'}"
        )

    level1 = gpd.read_file(BOUNDARIES_DIR / "level1" / "vnm_level1.shp")
    if level1.crs is None or "name" not in level1.columns:
        raise ValueError("The level-1 boundary file must have a CRS and 'name' column.")
    province_names = level1["name"].dropna().astype(str)
    province_by_slug = {slug(name): name for name in province_names}
    if len(province_by_slug) != len(province_names):
        raise ValueError("Level-1 boundary names have ambiguous directory slugs.")

    province_centroids = []
    for path in shapefiles:
        province_slug = path.parent.name
        if province_slug not in province_by_slug:
            raise ValueError(
                f"Cannot match level-2 directory {province_slug!r} to a level-1 name."
            )
        boundaries = gpd.read_file(path)
        if boundaries.crs is None or "name" not in boundaries.columns:
            raise ValueError(
                f"Level-2 boundary file must have a CRS and 'name' column: {path}"
            )
        if boundaries.crs != level1.crs:
            boundaries = boundaries.to_crs(level1.crs)
        boundaries["province"] = province_by_slug[province_slug]
        province_centroids.append(add_centroid_coordinates(boundaries))

    centroids = pd.concat(province_centroids, ignore_index=True)
    if centroids.duplicated(["province", "name"]).any():
        raise ValueError("Level-2 boundaries contain duplicate units within a province.")
    centroids.insert(0, "level", 2)
    return write_centroids(centroids, "level2_centroids.csv")


def slug(name: str) -> str:
    name = name.replace("Đ", "D").replace("đ", "d")
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def write_centroids(centroids: pd.DataFrame, filename: str) -> Path:
    output_path = OUTPUT_DIR / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    centroids.to_csv(output_path, index=False, encoding="utf-8")
    print(f"Wrote {len(centroids)} centroids to {output_path.resolve()}")
    return output_path


def main() -> None:
    generate_level0()
    generate_level1()
    generate_level2()


if __name__ == "__main__":
    main()