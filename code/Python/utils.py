"""
Utility functions for the project.
Author: Kien Le
AI disclosure: This code was generated with the assistance of AI. The author has reviewed and edited the code to ensure its accuracy and functionality.
Last Update: 2026-10-18   
"""
import re
import unicodedata


def province_slug(province: str) -> str:
	normalized = province.replace("Đ", "D").replace("đ", "d")
	normalized = unicodedata.normalize("NFKD", normalized)
	ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
	return re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")


def main()-> None:
	continue

if __name__ == "__main__":
    main()