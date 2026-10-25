# Data Folder

Extracted yearly VIIRS pixel CSV files are stored in `viirs_pixel_radiance/`.
Average radiance CSVs, with the same administrative-level and year structure,
are stored in `average_radiance/`.
Level-1 pixels are stored under `viirs_pixel_radiance/level1/<year>/`, and
level-2 pixels under `viirs_pixel_radiance/level2/<province_slug>/<year>/`.
Boundary shapefiles are stored in `vnm_admin_boundaries.shp/` and `vnm_district_boundaries/`
Prepared Vietnam boundaries are stored in `shp_boundaries/`:
`level0/vnm_level0.shp` for the national boundary and
`level1/vnm_level1.shp` for provincial boundaries. Level-2 boundaries are
organized by province/city under `shp_boundaries/level2/<province_slug>/`.
Reference documents are in `ref/`.


VIIRS Nighttime Light: https://eogdata.mines.edu/products/vnl/

* Working on Annual VNL V2. Because it is derived from Monthly DNB. The procedure is described in VNL_v22_readme_20230707.pptx


VNM Boundaries: https://data.humdata.org/dataset/cod-ab-vnm
Lowest level boundaries: https://gis.vn/don-vi-hanh-chinh-viet-nam

* The `vnm_admin0` file contains the national geometry; `vnm_admin1` contains provincial geometry.

* Curly apostrophes in source shapefile and level-2 population names have been
  replaced with straight apostrophes.

Vietnam National Statistics Office: 
* https://www.nso.gov.vn/en/statistical-data/#: All Statistical data
* https://www.nso.gov.vn/en/national-accounts/ : National level statistical data
* Why there is not GRDP by province? https://www.nso.gov.vn/en/other-news/2019/11/since-2017-localities-not-to-self-calculate-grdp/



* Here is where we retrieve the GDP of Vietnam, in addition to population by region, GRDP per capita.


* Note: Resolution No. 202/2025/QH15, dated June 12, 2025, reduced the total number of provincial-level administrative units nationwide to 34 provinces and centrally governed municipalities, consisting of 28 provinces and 6 centrally governed cities.

For provinces level:
Ex: Nien Giam Thong Ke Hanoi, Table 15 is population from 2020-2025

https://thuvienphapluat.vn/cong-van/Bo-may-hanh-chinh/Cong-van-2896-BNV-CQDP-2025-cung-cap-thong-tin-danh-muc-du-kien-don-vi-hanh-chinh-cap-xa-moi-658752.aspx#


The raw data are stored in `_`.

## Prediction dataset

Run `python code/Python/prepare_training_dataset.py` from the repository root
to generate two files under `data/training_data/`:

- `prediction_dataset.csv` contains level-2 units for 2025 only. It keeps
  `name` and includes `level_1`, `year`, `population`, `total_area`,
  `mean_radiance`, and `pixel_count`. Population and area come from
  `vnm_level2_population.csv`; radiance comes from the level-2 2025 radiance
  files. It does not include GRDP per capita or an administrative-level
  indicator.
- Level-2 names are matched using Unicode-normalized, case-insensitive exact
  names. Apostrophes in the source names use the straight form.
  Accent-stripped slugs are used only for file/directory names, never to decide
  whether two administrative units are the same. Unmatched names are printed
  for review rather than being merged based on a potentially colliding slug.
  This matching rule applies only to level 2; level-1 matching is unchanged.
- `vnm_regression_dataset.csv` contains level-1 province-year observations for
  2020–2025, including GRDP per capita, population, total area, mean radiance,
  and pixel count. Total area is sourced from `vnm_landUse.csv`.

## Region maps

`python code/Python/plot_regions.py` plots the default level-2 predicted GRDP
per-capita values from `data/predicted_data/level2_grdp_pc_predictions.csv`
using the prepared boundaries in `data/shp_boundaries/`. Figures are saved to
`figures/` by default.

Level-2 predictions are calibrated so that, for each province, the sum of
`predicted_grdp_per_capita * population` equals the province's 2025 GRDP per
capita times its province-level population from `vnm_population.csv`. The
province population is stored in thousands in that source and is converted to
people for the constraint. The generated prediction CSV includes this total in
`province_population_2025`.

Use `--level 1` or `--level 2` to choose provincial or district/commune
boundaries, `--metric <column>` to select a numeric CSV column (for example,
`population`), and `--csv <path>` to select another dataset. `--year <year>`
filters a dataset with multiple years. If the input column names are not
recognized automatically, use `--name-column` and, for level 2, `--province-column`.
Use `--province <name>` to plot a single province's level-2 units (for example,
`--province "Ho Chi Minh City"`). Use `--output <path>` to choose a different
output file.
