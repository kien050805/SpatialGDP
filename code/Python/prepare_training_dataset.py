"""Build level-1 regression and 2025 level-2 prediction datasets."""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INDICATORS_DIR = PROJECT_ROOT / "data" / "_vnm_indicators"
OUTPUT_DIR = PROJECT_ROOT / "data" / "training_data"
LEVEL1_POPULATION_PATH = INDICATORS_DIR / "vnm_population.csv"
GRDP_PATH = INDICATORS_DIR / "vnm_GRDPpc.csv"
LEVEL1_AREA_PATH = INDICATORS_DIR / "vnm_landUse.csv"
LEVEL2_POPULATION_PATH = INDICATORS_DIR / "vnm_level2_population.csv"
RADIANCE_DIR = PROJECT_ROOT / "data" / "average_radiance"
PREDICTION_YEAR = "2025"
PREDICTION_PATH = OUTPUT_DIR / "prediction_dataset.csv"
PREDICTION_COLUMNS = (
    "name",
    "level_1",
    "year",
    "population",
    "total_area",
    "mean_radiance",
    "pixel_count",
)
REGRESSION_PATH = OUTPUT_DIR / "vnm_regression_dataset.csv"
REGRESSION_COLUMNS = (
    "province",
    "year",
    "grdp_per_capita",
    "population",
    "total_area",
    "mean_radiance",
    "pixel_count",
)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames:
            raise ValueError(f"Missing CSV header in {path}")
        return reader.fieldnames, list(reader)


def read_wide_indicator(path: Path) -> tuple[list[str], dict[str, dict[str, str]]]:
    columns, source_rows = read_csv(path)
    if "province" not in columns:
        raise ValueError(f"Missing 'province' column in {path}")
    years = [column for column in columns if column != "province"]
    provinces = {
        row["province"].strip(): {year: row[year].strip() for year in years}
        for row in source_rows
    }
    return sorted(years, key=int), provinces


def read_level1_areas(path: Path) -> dict[str, str]:
    columns, rows = read_csv(path)
    area_column = next(column for column in columns if column.lower() == "total area")
    return {row["province"].strip(): row[area_column].strip() for row in rows}


def write_csv(
    path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def slug(name: str) -> str:
    name = name.replace("Đ", "D").replace("đ", "d")
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def name_key(name: str) -> str:
    return " ".join(unicodedata.normalize("NFC", name).split()).casefold()


def level2_name_key(name: str) -> str:
    return name_key(name).replace("‘", "'").replace("’", "'")


def number_string(value: float) -> str:
    return format(value, ".12g")


def read_radiance(
    path: Path, *, level2: bool = False
) -> dict[str, dict[str, str]]:
    columns, rows = read_csv(path)
    expected = {"name", "mean_radiance", "pixel_count"}
    if not expected.issubset(columns):
        raise ValueError(f"Missing required radiance columns in {path}")
    radiance_by_name = {}
    original_names = {}
    for row in rows:
        name = row["name"].strip()
        key = level2_name_key(name) if level2 else name_key(name)
        if key in radiance_by_name:
            raise ValueError(
                f"Duplicate radiance name after Unicode/whitespace normalization "
                f"in {path}: {original_names[key]!r} and {name!r}"
            )
        radiance_by_name[key] = row
        original_names[key] = name
    return radiance_by_name


def level2_population_by_province(
    path: Path,
) -> dict[str, list[dict[str, str]]]:
    columns, rows = read_csv(path)
    expected = {"name", "level_1", "total_area", "population"}
    if not expected.issubset(columns):
        raise ValueError(f"Missing required population columns in {path}")

    grouped: dict[tuple[str, str], dict[str, object]] = {}
    for row in rows:
        province = row["level_1"].strip()
        name = " ".join(row["name"].split())
        key = (province, level2_name_key(name))
        if key not in grouped:
            grouped[key] = {
                "name": name,
                "total_area": 0.0,
                "population": 0.0,
            }
        grouped[key]["total_area"] += float(row["total_area"])
        grouped[key]["population"] += float(row["population"])

    by_province: dict[str, list[dict[str, str]]] = defaultdict(list)
    for (province, _), row in grouped.items():
        by_province[province].append(
            {
                "name": str(row["name"]),
                "total_area": number_string(float(row["total_area"])),
                "population": number_string(float(row["population"])),
            }
        )
    return by_province


def merge_level2(
    province: str,
    population_rows: list[dict[str, str]],
    radiance_rows: dict[str, dict[str, str]],
) -> tuple[list[dict[str, str]], list[str], list[str]]:
    population_by_name = {
        level2_name_key(row["name"]): row for row in population_rows
    }
    radiance_by_name = dict(radiance_rows)
    matched_names = population_by_name.keys() & radiance_by_name.keys()

    unmatched_population = set(population_by_name) - matched_names
    unmatched_radiance = set(radiance_by_name) - matched_names

    records = []
    for population_key, population_row in population_by_name.items():
        radiance_row = (
            radiance_by_name.get(population_key, {})
            if population_key in matched_names
            else {}
        )
        records.append(
            {
                "name": population_row["name"],
                "level_1": province,
                "population": population_row["population"],
                "total_area": population_row["total_area"],
                "mean_radiance": radiance_row.get("mean_radiance", ""),
                "pixel_count": radiance_row.get("pixel_count", ""),
            }
        )

    for radiance_key, radiance_row in radiance_by_name.items():
        if radiance_key not in matched_names:
            records.append(
                {
                    "name": radiance_row["name"].strip(),
                    "level_1": province,
                    "population": "",
                    "total_area": "",
                    "mean_radiance": radiance_row["mean_radiance"],
                    "pixel_count": radiance_row["pixel_count"],
                }
            )

    return (
        records,
        sorted(population_by_name[key]["name"] for key in unmatched_population),
        sorted(radiance_by_name[key]["name"].strip() for key in unmatched_radiance),
    )


def generate_regression_dataset() -> None:
    years, level1_population = read_wide_indicator(LEVEL1_POPULATION_PATH)
    grdp_years, grdp = read_wide_indicator(GRDP_PATH)
    if years != grdp_years:
        raise ValueError("GRDP and population year columns do not match")
    level1_areas = read_level1_areas(LEVEL1_AREA_PATH)
    records = []

    for year in years:
        level1_radiance = read_radiance(
            RADIANCE_DIR / "level1" / year / f"vnm_{year}_average_radiance.csv"
        )
        for province, year_values in level1_population.items():
            radiance = level1_radiance[name_key(province)]
            records.append(
                {
                    "province": province,
                    "year": year,
                    "grdp_per_capita": grdp[province][year],
                    "population": year_values[year],
                    "total_area": level1_areas[province],
                    "mean_radiance": radiance["mean_radiance"],
                    "pixel_count": radiance["pixel_count"],
                }
            )

    write_csv(REGRESSION_PATH, REGRESSION_COLUMNS, records)
    print(f"Wrote {len(records)} regression observations to {REGRESSION_PATH}")


def generate_prediction_dataset() -> None:
    level2_population = level2_population_by_province(LEVEL2_POPULATION_PATH)
    province_slugs = {}
    provinces_by_slug = {}
    for province in level2_population:
        province_slug = slug(province)
        if not province_slug or province_slug in provinces_by_slug:
            other = provinces_by_slug.get(province_slug)
            raise ValueError(
                f"Province names produce an invalid or duplicate radiance path: "
                f"{other!r} and {province!r}"
            )
        province_slugs[province] = province_slug
        provinces_by_slug[province_slug] = province

    records = []
    unmatched_level2_population: list[tuple[str, str]] = []
    unmatched_level2_radiance: list[tuple[str, str]] = []
    for province, population_rows in level2_population.items():
        province_name_slug = province_slugs[province]
        radiance_path = (
            RADIANCE_DIR
            / "level2"
            / province_name_slug
            / PREDICTION_YEAR
            / f"{province_name_slug}_{PREDICTION_YEAR}_average_radiance.csv"
        )
        radiance_rows = read_radiance(radiance_path, level2=True)
        province_records, unmatched_pop, unmatched_rad = merge_level2(
            province, population_rows, radiance_rows
        )
        unmatched_level2_population.extend((province, name) for name in unmatched_pop)
        unmatched_level2_radiance.extend((province, name) for name in unmatched_rad)
        records.extend(
            {"year": PREDICTION_YEAR, **row} for row in province_records
        )

    write_csv(PREDICTION_PATH, PREDICTION_COLUMNS, records)
    print(
        f"Wrote {len(records)} level-2 prediction observations to {PREDICTION_PATH}"
    )
    if unmatched_level2_population or unmatched_level2_radiance:
        print(
            f"Unmatched level-2 rows for {PREDICTION_YEAR}: "
            f"{len(unmatched_level2_population)} population-only, "
            f"{len(unmatched_level2_radiance)} radiance-only"
        )
        for province, name in unmatched_level2_population:
            print(f"  Population only: {province} / {name}")
        for province, name in unmatched_level2_radiance:
            print(f"  Radiance only: {province} / {name}")


def main() -> None:
    generate_regression_dataset()
    generate_prediction_dataset()


if __name__ == "__main__":
    main()
