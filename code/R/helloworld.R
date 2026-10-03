# Install and load required packages
library(GWmodel)
library(sf)

# 1. Load spatial data 
spatial_data <- st_read("your_spatial_data.shp")

# 2. Convert sf object to Spatial object (GWmodel relies on older sp format internally)
spatial_sp <- as(spatial_data, "Spatial")

# 3. Find the optimal adaptive bandwidth using AICc
# 'adaptive = TRUE' means the bandwidth will be a fixed number of local neighbors
optimal_bw <- bw.gwr(
  formula = dependent_var ~ independent_var1 + independent_var2,
  data = spatial_sp,
  approach = "AICc",
  kernel = "bisquare",
  adaptive = TRUE
)
print(paste("Optimal Bandwidth:", optimal_bw))

# 4. Run the GWR model
gwr_model <- gwr.basic(
  formula = dependent_var ~ independent_var1 + independent_var2,
  data = spatial_sp,
  bw = optimal_bw,
  kernel = "bisquare",
  adaptive = TRUE
)

# 5. Print results summary
print(gwr_model)

# 6. Extract spatial results for mapping (contains local R2 and coefficients)
output_spatial_sf <- st_as_sf(gwr_model$SDF)
