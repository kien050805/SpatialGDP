import csv
from collections import defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
POPULATION_CSV = PROJECT_ROOT / "data" / "_vnm_indicators" / "vnm_level2_population.csv"


def main() -> None:
    population_by_province: dict[str, int] = defaultdict(int)
    with POPULATION_CSV.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        required_columns = {"level_1", "population"}
        if not reader.fieldnames or not required_columns.issubset(reader.fieldnames):
            raise ValueError(
                f"Expected columns {sorted(required_columns)} in {POPULATION_CSV}"
            )
        for row in reader:
            province = row["level_1"].strip()
            if not province:
                raise ValueError(f"Empty province name in {POPULATION_CSV}")
            try:
                population_by_province[province] += int(row["population"])
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid population for {province!r} in {POPULATION_CSV}: "
                    f"{row['population']!r}"
                ) from error

    print("Level-2 population total by province:")
    for province, population in sorted(population_by_province.items()):
        print(f"{province}: {population:,}")
    print(f"National level-2 population total: {sum(population_by_province.values()):,}")


if __name__ == "__main__":
    main()
