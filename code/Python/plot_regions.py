"""Plot a numeric indicator or prediction on Vietnam's administrative boundaries."""

from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BOUNDARIES_DIR = PROJECT_ROOT / "data" / "shp_boundaries"
DEFAULT_CSV = (
    PROJECT_ROOT / "data" / "predicted_data" / "level2_grdp_pc_predictions.csv"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "figures"
DEFAULT_METRIC = "predicted_grdp_per_capita"
LEVEL1_BOUNDARY = BOUNDARIES_DIR / "level1" / "vnm_level1.shp"
LEVEL2_BOUNDARIES = BOUNDARIES_DIR / "level2"


def name_key(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(unicodedata.normalize("NFC", str(value)).split()).casefold()


def slug(name: str) -> str:
    name = name.replace("Đ", "D").replace("đ", "d")
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def choose_column(
    columns: pd.Index, requested: str | None, candidates: tuple[str, ...], label: str
) -> str:
    if requested:
        if requested not in columns:
            raise ValueError(f"Missing {label} column {requested!r} in the input CSV.")
        return requested
    for candidate in candidates:
        if candidate in columns:
            return candidate
    raise ValueError(
        f"Could not identify the {label} column. Available columns: "
        f"{', '.join(map(str, columns))}. Specify it with the matching option."
    )


def read_level1_boundaries(path: Path) -> gpd.GeoDataFrame:
    boundaries = gpd.read_file(path)
    if boundaries.crs is None:
        raise ValueError(f"Boundary file has no CRS: {path}")
    if "name" not in boundaries.columns:
        raise ValueError(f"Boundary file must contain a 'name' column: {path}")
    return boundaries[["name", "geometry"]].rename(columns={"name": "unit_name"})


def read_level2_boundaries(
    directory: Path, level1_boundaries: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    province_names = level1_boundaries["unit_name"].dropna().astype(str)
    province_by_slug = {slug(name): name for name in province_names}
    if len(province_by_slug) != len(province_names):
        raise ValueError("Level-1 boundary names have ambiguous directory slugs.")
    shapefiles = sorted(directory.glob("*/*.shp"))
    if not shapefiles:
        raise FileNotFoundError(f"No level-2 shapefiles found under {directory}")

    features = []
    for path in shapefiles:
        province_slug = path.parent.name
        if province_slug not in province_by_slug:
            raise ValueError(
                f"Cannot match level-2 boundary directory {province_slug!r} to a "
                "level-1 boundary name."
            )
        boundary = gpd.read_file(path)
        if boundary.crs is None:
            raise ValueError(f"Boundary file has no CRS: {path}")
        if boundary.crs != level1_boundaries.crs:
            boundary = boundary.to_crs(level1_boundaries.crs)
        if "name" not in boundary.columns:
            raise ValueError(f"Boundary file must contain a 'name' column: {path}")
        boundary = boundary[["name", "geometry"]].rename(
            columns={"name": "unit_name"}
        )
        boundary["province_name"] = province_by_slug[province_slug]
        features.append(boundary)

    return gpd.GeoDataFrame(
        pd.concat(features, ignore_index=True),
        geometry="geometry",
        crs=features[0].crs,
    )


def prepare_indicator(
    csv_path: Path,
    metric: str,
    level: int,
    name_column: str | None,
    province_column: str | None,
    year: int | None,
) -> pd.DataFrame:
    indicator = pd.read_csv(csv_path, encoding="utf-8-sig")
    if year is not None:
        if "year" not in indicator.columns:
            raise ValueError(
                f"Cannot filter by year; CSV has no 'year' column: {csv_path}"
            )
        indicator = indicator.loc[
            pd.to_numeric(indicator["year"], errors="coerce") == year
        ].copy()
        if indicator.empty:
            raise ValueError(f"No rows found for year {year} in {csv_path}")
    if metric not in indicator.columns:
        raise ValueError(
            f"Metric {metric!r} is not in {csv_path}. Available columns: "
            f"{', '.join(map(str, indicator.columns))}"
        )

    unit_column = choose_column(
        indicator.columns,
        name_column,
        ("level_1", "province", "name") if level == 1 else ("level_2", "name"),
        "unit name",
    )
    columns = [unit_column, metric]
    if level == 2:
        province_column = choose_column(
            indicator.columns,
            province_column,
            ("level_1", "province"),
            "province",
        )
        columns.append(province_column)

    indicator = indicator[columns].copy()
    indicator["unit_key"] = indicator[unit_column].map(name_key)
    keys = ["unit_key"]
    if level == 2:
        indicator["province_key"] = indicator[province_column].map(name_key)
        keys = ["province_key", "unit_key"]
    if indicator[keys].eq("").any(axis=None):
        raise ValueError(f"CSV contains empty administrative names: {csv_path}")
    if indicator.duplicated(keys).any():
        raise ValueError(
            "Input CSV contains duplicate administrative units for the selected "
            f"level{level}. If it contains multiple years, select one with --year."
        )
    indicator[metric] = pd.to_numeric(indicator[metric], errors="coerce")
    indicator[metric] = indicator[metric].where(np.isfinite(indicator[metric]))
    return indicator[keys + [metric]]


def create_figure(
    csv_path: Path,
    output_path: Path,
    metric: str = DEFAULT_METRIC,
    level: int = 2,
    name_column: str | None = None,
    province_column: str | None = None,
    year: int | None = None,
) -> None:
    if level not in (1, 2):
        raise ValueError(f"Administrative level must be 1 or 2, not {level}.")

    level1 = read_level1_boundaries(LEVEL1_BOUNDARY)
    if level == 1:
        boundaries = level1.copy()
        boundaries["unit_key"] = boundaries["unit_name"].map(name_key)
        keys = ["unit_key"]
    else:
        boundaries = read_level2_boundaries(LEVEL2_BOUNDARIES, level1)
        boundaries["unit_key"] = boundaries["unit_name"].map(name_key)
        boundaries["province_key"] = boundaries["province_name"].map(name_key)
        keys = ["province_key", "unit_key"]

    indicator = prepare_indicator(
        csv_path, metric, level, name_column, province_column, year
    )
    merged = boundaries.merge(indicator, on=keys, how="left", validate="one_to_one")
    missing = merged[metric].isna()
    if missing.all():
        raise ValueError(
            f"No {metric!r} values matched the level-{level} boundaries. "
            "Check the input names and selected columns."
        )

    if not np.isfinite(merged[metric]).any():
        raise ValueError(f"Metric {metric!r} contains no finite numeric values.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(8, 10), layout="constrained")
    merged.plot(
        column=metric,
        ax=axis,
        cmap="viridis",
        edgecolor="none" if level == 2 else "#f3f0e9",
        linewidth=0 if level == 2 else 0.35,
        missing_kwds={"color": "#d9d9d9", "label": "No data"},
        legend=True,
        legend_kwds={"label": metric.replace("_", " ").title(), "shrink": 0.65},
    )
    axis.set_title(
        f"Vietnam | {metric.replace('_', ' ').title()} | Level {level}"
        + (f" | {year}" if year is not None else ""),
        loc="left",
        pad=12,
    )
    axis.set_axis_off()
    axis.set_aspect("equal", adjustable="box")
    figure.savefig(output_path, dpi=250, bbox_inches="tight")
    plt.close(figure)
    print(f"Saved figure to {output_path.resolve()}")
    if missing.any():
        missing_names = merged.loc[missing, "unit_name"].head(10).tolist()
        print(
            f"Note: {int(missing.sum())} boundary units have no {metric} value. "
            f"Examples: {missing_names}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot a metric or estimated prediction on Vietnam's boundaries."
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--metric", default=DEFAULT_METRIC)
    parser.add_argument("--level", type=int, choices=(1, 2), default=2)
    parser.add_argument("--name-column")
    parser.add_argument("--province-column")
    parser.add_argument("--year", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    year_suffix = f"_{args.year}" if args.year is not None else ""
    output_path = args.output or (
        DEFAULT_OUTPUT_DIR
        / f"vietnam_level{args.level}_{args.metric}{year_suffix}.png"
    )
    create_figure(
        args.csv,
        output_path,
        metric=args.metric,
        level=args.level,
        name_column=args.name_column,
        province_column=args.province_column,
        year=args.year,
    )


if __name__ == "__main__":
    main()
