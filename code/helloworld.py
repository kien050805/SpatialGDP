import geopandas as gpd

vietnam = gpd.read_file(
    "data/vnm_admin_boundaries.shp/vnm_admin1.shp"
)

print(vietnam.head())
print(vietnam.columns)
print(vietnam)
print(vietnam.crs)

## Example of WMS request to match EOG grid 
# This example demonstrates how to construct a WMS request that asks for output GeoTIF images  
# that matches EOG grid definition @ 15 asec 
 
# Define area of interest 
# Gaya Bihar, India 
# Size: 31(W) x 31(H) 
# Upper Left point: 24.85N, 84.94E 
# width = 31 
# height = 31 
# ullat = 24.858 
# ullon = 84.941 
# px_sz = (15/3600)  # 15 arc second 
 
# # Snap to EOG grid 
# ullat = round(ullat/px_sz,0)*px_sz  # 24.858333333333334  
# ullon = round(ullon/px_sz,0)*px_sz  # 84.94166666666666 
 
# # Calculate Lower right corner 
# lrlat = ullat - (height-1)*px_sz  # 24.73333333333334 
# lrlon = ullon + (width-1)*px_sz   # 85.06666666666666 
 
# # Expand edges by 0.5 pixel 
# maxx = lrlon + 1/2*px_sz  # 85.06875 
# maxy = ullat + 1/2*px_sz  # 24.86041666666667 
# minx = ullon - 1/2*px_sz  # 84.93958333333333 
# miny = lrlat - 1/2*px_sz  # 24.73125 
 
# # Define request parameters 
# ## Layers available: 

# ##   VIIRS_NPP_DNB_DAILY 

# ##   VIIRS_NPP_CLD_DAILY 

# ##   VIIRS_NPP_DNB_MONTHLY 

# ##   VIIRS_NPP_CFCVG_MONTHLY 

# ## Format available: 

# ##   PNG 

# ##   RAW_GTIFF 

# ## Date format: 

# ##   DAILY: yyyymmdd 

# ##   MONTHLY: yyyymm01 
# params = { 
#             'layers': 'VIIRS_NPP_DNB_Monthly', 
#             'service': 'wms', 
#             'version': '1.0.0', 
#             'request': 'getmap', 
#             'srs': 'epsg:4326', 
#             'format': 'raw_gtiff', 
#             'time': '20200801', 
#             'width': str(width), 
#             'height': str(height), 
#             'bbox': ','.join([str(i) for i in [minx, miny, maxx, maxy]]) 
#          } 
 

# # Construct request URL 
# uri = 'https://eogmap.mines.edu/nighttime_light/annual/v22/2025?'  
# param_str = '&'.join([i+'='+params[i] for i in list(params)]) 
# url = uri+param_str 
 

# # Submit Request & Save Image 
# import requests 
# import shutil 
 
# img_path='./dnb_monthly_202008.tif' 
# r = requests.request("GET", url, headers = {}, data={}) 
# if r.status_code ==200: 
#     with open(img_path, 'wb') as f: 
#         f.write(r.content) 

# import requests
# import gzip
# import shutil

# url = (
#     "https://eogdata.mines.edu/nighttime_light/annual/v22/2025/"
#     "VNL_npp_2025_global_vcmslcfg_v2_c202604011200.average_masked.dat.tif.gz"
# )

# gz_file = "VNL_2025.tif.gz"
# tif_file = "VNL_2025.tif"

# # Your authenticated EOG session may need cookies/authentication here
# response = requests.get(url)

# print(response.status_code)
# print(response.headers.get("Content-Type"))

# if response.ok:
#     with open(gz_file, "wb") as f:
#         f.write(response.content)

#     # Decompress
#     with gzip.open(gz_file, "rb") as f_in:
#         with open(tif_file, "wb") as f_out:
#             shutil.copyfileobj(f_in, f_out)

#     print(f"Saved: {tif_file}")
# else:
#     print(response.text[:500])