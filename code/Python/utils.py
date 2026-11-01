
import re
import unicodedata
import hashlib

def name_slug(name: str) -> str:
    normalized = name.replace("Đ", "D").replace("đ", "d")
    normalized = unicodedata.normalize("NFKD", normalized)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")

def slug(name: str) -> str:
    name = name.replace("Đ", "D").replace("đ", "d")
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")

def unique_level2_slugs(names: list[str]) -> list[str]:
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

def main():
    return

if __name__ == "__main__":
    main()