"""Merge provincial GRDP per capita, population, and VIIRS radiance by year."""

from __future__ import annotations

import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INDICATORS_DIR = PROJECT_ROOT / "data" / "_vnm_indicators"
OUTPUT_DIR = PROJECT_ROOT / "data" / "training_data"
GRDP_PATH = INDICATORS_DIR / "vnm_GRDPpc.csv"
POPULATION_PATH = INDICATORS_DIR / "vnm_population.csv"
RADIANCE_DIR = PROJECT_ROOT / "data" / "average_radiance" / "level1"
OUTPUT_PATH = OUTPUT_DIR / "vnm_regression_dataset.csv"
OUTPUT_COLUMNS = (
    "province",
    "year",
    "grdp_per_capita",
    "population",
    "mean_radiance",
    "pixel_count",
)


def read_wide_indicator(path: Path) -> tuple[list[str], dict[str, dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or "province" not in reader.fieldnames:
            raise ValueError(f"Missing 'province' column in {path}")
        years = [column for column in reader.fieldnames if column != "province"]
        if not years or any(not year.isdigit() for year in years):
            raise ValueError(f"Expected year columns in {path}")

        rows: dict[str, dict[str, str]] = {}
        for row in reader:
            province = (row.get("province") or "").strip()
            if not province or province in rows:
                raise ValueError(f"Empty or duplicate province in {path}: {province!r}")
            if any(not (row.get(year) or "").strip() for year in years):
                raise ValueError(f"Missing indicator value for {province} in {path}")
            rows[province] = {year: row[year].strip() for year in years}

    return years, rows


def read_radiance(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        expected_columns = {"name", "mean_radiance", "pixel_count"}
        if not reader.fieldnames or not expected_columns.issubset(reader.fieldnames):
            raise ValueError(f"Missing required radiance columns in {path}")

        rows: dict[str, dict[str, str]] = {}
        for row in reader:
            province = (row.get("name") or "").strip()
            mean_radiance = (row.get("mean_radiance") or "").strip()
            pixel_count = (row.get("pixel_count") or "").strip()
            if not province or province in rows:
                raise ValueError(f"Empty or duplicate province in {path}: {province!r}")
            if not mean_radiance or not pixel_count:
                raise ValueError(f"Missing radiance value for {province} in {path}")
            rows[province] = {
                "mean_radiance": mean_radiance,
                "pixel_count": pixel_count,
            }
    return rows


def main() -> None:
    grdp_years, grdp = read_wide_indicator(GRDP_PATH)
    population_years, population = read_wide_indicator(POPULATION_PATH)
    if grdp_years != population_years:
        raise ValueError(
            "GRDP and population year columns do not match: "
            f"{grdp_years} vs {population_years}"
        )
    if set(grdp) != set(population):
        raise ValueError("GRDP and population province names do not match")

    years = sorted(grdp_years, key=int)
    radiance_by_year: dict[str, dict[str, dict[str, str]]] = {}
    for year in years:
        radiance_path = RADIANCE_DIR / year / f"vnm_{year}_average_radiance.csv"
        if not radiance_path.is_file():
            raise FileNotFoundError(f"Radiance file not found: {radiance_path}")
        radiance = read_radiance(radiance_path)
        if set(radiance) != set(grdp):
            raise ValueError(
                f"Province names in {radiance_path} do not match indicator files"
            )
        radiance_by_year[year] = radiance

    records = []
    for province in grdp:
        for year in years:
            records.append(
                {
                    "province": province,
                    "year": year,
                    "grdp_per_capita": grdp[province][year],
                    "population": population[province][year],
                    **radiance_by_year[year][province],
                }
            )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(records)
    print(f"Wrote {len(records)} province-year observations to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
