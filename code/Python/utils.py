

def province_slug(province: str) -> str:
	normalized = province.replace("Đ", "D").replace("đ", "d")
	normalized = unicodedata.normalize("NFKD", normalized)
	ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
	return re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")


def main()-> None:


if __name__ == "__main__":
    main()