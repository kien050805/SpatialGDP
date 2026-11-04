"""
Utility functions for the repository, including:
- read_csv: Read a CSV file and return its column names and rows.
- name_slug: Convert a Vietnamese name into a lowercase, ASCII-compatible slug.
- unique_level2_slugs: Generate unique slugs for Level-2 administrative names.
- province_key: Normalize a province or city name into a standardized lookup key.

This script is specifically designed for the data provided in this repository
and may not work correctly with other datasets.

Author: Kien Le
AI Disclosure: This code was generated with AI assistance. The author has
reviewed and edited the code to ensure its accuracy and functionality.
Last Updated: 2026-11-02
"""

from pathlib import Path
import csv
import re
import unicodedata
import hashlib

def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """
    Read a CSV file and return its column names and rows.

    The function opens the CSV file using UTF-8 encoding with BOM support, reads its contents using csv.DictReader, and stores each row as a dictionary mapping column names to their corresponding values.
    If the file does not contain a header, a ValueError is raised.

    Args:
        path (Path): Path to the CSV file.

    Returns:
        tuple[list[str], list[dict[str, str]]]: A tuple containing:
            - A list of column names from the CSV header.
            - A list of dictionaries representing the CSV rows.

    Raises:
        ValueError: If the CSV file does not contain a header.
    """
    with path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames:
            raise ValueError(f"Missing CSV header in {path}")
        return list(reader.fieldnames), list(reader)

def name_slug(name: str) -> str:
    """
    Convert a Vietnamese name into a lowercase, ASCII-compatible slug.

    The function handles Vietnamese special characters by converting them to their corresponding Latin characters.
    It then removes diacritical marks, converts the name to lowercase, and replaces sequences of non-alphanumeri characters with underscores.
    Leading and trailing underscores are removed from the resulting slug.

    Args:
        name (str): Vietnamese name to convert.

    Returns:
        str: Normalized ASCII slug containing lowercase letters, numbers, and underscores.
    """
    normalized = name.replace("Đ", "D").replace("đ", "d")
    normalized = unicodedata.normalize("NFKD", normalized)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")

def unique_level2_slugs(names: list[str]) -> list[str]:
    """
    Generate unique slugs for Level-2 administrative names.

    The function first converts each name into an ASCII-compatible slug using name_slug().
    If multiple names produce the same slug, an 8-character SHA-1 hash of the original Vietnamese name is appended to distinguish them.
    Names with already unique slugs remain unchanged.
    After generating the slugs, the function checks whether all results are unique. 
    If duplicate slugs remain, a ValueError is raised.

    Args:
        names (list[str]): List of Level-2 administrative names in Vietnamese.

    Returns:
        list[str]: List of unique slugs corresponding to the input names, preserving their original order.

    Raises:
        ValueError: If the generated slugs are not unique.
    """
    slugs = [name_slug(name) for name in names]
    counts = {slug: slugs.count(slug) for slug in set(slugs)}
    unique_slugs = [
        (
            f"{slug}_{hashlib.sha1(name.encode('utf-8')).hexdigest()[:8]}"
            if counts[slug] > 1
            else slug
        )
        for name, slug in zip(names, slugs)
    ]
    if len(unique_slugs) != len(set(unique_slugs)):
        raise ValueError("Level-2 names do not produce unique pixel CSV filenames.")
    return unique_slugs

def province_key(name: str) -> str:
    """
    Normalize a province or city name into a standardized lookup key.

    The function removes leading and trailing whitespace, converts the name to lowercase using case folding, and removes the trailing " city" suffix if present.

    Args:
        name (str): Province or city name to normalize.

    Returns:
        str: Normalized name suitable for comparison or lookup.
    """
    normalized = name.strip().casefold()
    if normalized.endswith(" city"):
        normalized = normalized[:-5].strip()
    return normalized

def main():
    return

if __name__ == "__main__":
    main()