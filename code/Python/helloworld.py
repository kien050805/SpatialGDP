from pathlib import Path

import geopandas as gpd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BOUNDARIES_DIR = PROJECT_ROOT / "data" / "vnm_district_boundaries" / "an_giang"
SHAPEFILES = (
	BOUNDARIES_DIR / "an_giang.shp",
)


for shapefile in SHAPEFILES:
	layer = gpd.read_file(shapefile)

	print(f"\n{'=' * 80}\n{shapefile.name}")
	print(f"Features: {len(layer)}")
	print(f"CRS: {layer.crs}")
	print(f"Columns: {list(layer.columns)}")
	print(f"Geometry types: {layer.geometry.geom_type.value_counts().to_dict()}")
	print(f"Bounds: {layer.total_bounds}")
	print("First 5 records:")
	print(layer.drop(columns="geometry").head().to_string(index=False))
