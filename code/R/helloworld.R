library(dplyr)
library(ggplot2)

setwd("../../")

setwd("data/")

df1 = read.csv("vnm_GRDPpc.csv")
df2 = read.csv("vnm_unemployment.csv")
df3 = read.csv("vnm_population.csv")
df4 = read.csv("vnm_landUse.csv")

setwd("viiirs_average_radiance/")

rad = read.csv("vietnam_2025_mean_radiance_by_province.csv")

df1 = df1 |> select("province", "X2025") |> rename(GRDPpc = X2025)
df2 = df2 |> select("province", "X2025") |> rename(unemployment = X2025)
df3 = df3 |> select("province", "X2025") |> rename (population = X2025)

df <- df1 |>
  full_join(df2, by = "province") |>
  full_join(df3, by = "province") |>
  full_join(df4, by = "province") |>
  full_join(rad, by = "province")


mod = lm(data = df, df$GRDPpc ~ df$mean_radiance)

summary(mod)

mod = lm (data = df, df$GRDPpc ~ df$population +
            df$unemployment +
            df$mean_radiance +
            df$Agricultural.production.land +
            df$Forestry.land +
            df$Homestead.land)

cor(df$population, df$mean_radiance)

summary(mod)

ggplot(data = df, aes(x = df$mean_radiance, y = df$GRDPpc)) +
  geom_point() +
  geom_smooth(method = "lm")


setwd("../")
write.csv(df, "vnm_indicators_2025.csv", row.names = FALSE)

df1 = df1 |> select("province")
write.csv(df, "vnm_provinces.csv", row.names = FALSE)


library(tidyr)
library(dplyr)

gdp_data = read.csv("vnm_level0_gdp.csv")

annual_gdp <- gdp_data %>%
  pivot_longer(
    cols = starts_with("X"),
    names_to = "year",
    values_to = "gdp",
    names_prefix = "X"
  ) %>%
  mutate(year = as.integer(year)) |>
  select("year", "gdp")


write.csv(annual_gdp, "vnm_level0_gdp.csv", row.names = FALSE)

# Named vector for CVXR constraints
annual_grdp_vector <- setNames(
  annual_grdp$total_grdp,
  as.character(annual_grdp$year)
)
