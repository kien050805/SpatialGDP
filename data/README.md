# Data Folder

Extracted yearly VIIRS pixel CSV files are stored in `viirs_pixel_radiance/`.
Provincial 2025 VIIRS extracts are stored in `viirs_pixel_radiance_province/2025/`. 
Boundary shapefiles are stored in `vnm_admin_boundaries.shp/` and `vnm_district_boundaries/`
Reference documents are in `ref/`.


VIIRS Nighttime Light: https://eogdata.mines.edu/products/vnl/

* Working on Annual VNL V2. Because it is derived from Monthly DNB. The procedure is described in VNL_v22_readme_20230707.pptx


VNM Boundaries: https://data.humdata.org/dataset/cod-ab-vnm
Lowest level boundaries: https://gis.vn/don-vi-hanh-chinh-viet-nam

* The `vnm_admin0` file contains the national geometry; `vnm_admin1` contains provincial geometry.



Vietnam National Statistics Office: 
* https://www.nso.gov.vn/en/statistical-data/# : All Statistical data
* https://www.nso.gov.vn/en/national-accounts/ : National level statistical data


* Here is where we retrieve the GDP of Vietnam, in addition to population by region, GRDP per capita.


* Note: Resolution No. 202/2025/QH15, dated June 12, 2025, reduced the total number of provincial-level administrative units nationwide to 34 provinces and centrally governed municipalities, consisting of 28 provinces and 6 centrally governed cities.

For provinces level:
Ex: Nien Giam Thong Ke Hanoi, Table 15 is population from 2020-2025