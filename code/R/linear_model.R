setwd("../../")

library(ggplot2)

training_data <- read.csv("data/training_data/vnm_regression_dataset.csv")
train_data <- subset(training_data, year >= 2020 & year <= 2024)
test_data <- subset(training_data, year == 2025)
model <- lm(grdp_per_capita ~ mean_radiance, data = train_data)
predictions <- predict(model, newdata = test_data)
rmse <- sqrt(mean((test_data$grdp_per_capita - predictions)^2))

dir.create("code/R/model", recursive = TRUE, showWarnings = FALSE)
saveRDS(model, "code/R/model/linear_model.rds")

print(summary(model))
cat(sprintf("2025 holdout RMSE (GRDP per capita): %.4f\n", rmse))


library(ggplot2)

# Plot training data, fitted model, and 2025 actual observations
p <- ggplot() +
  # Actual training observations
  geom_point(
    data = train_data,
    aes(x = mean_radiance, y = grdp_per_capita, color = "Training data"),
    size = 2,
    alpha = 0.7
  ) +
  # Regression line fitted on 2020–2024 data
  geom_smooth(
    data = train_data,
    aes(x = mean_radiance, y = grdp_per_capita),
    method = "lm",
    formula = y ~ x,
    se = TRUE,
    color = "blue",
    linewidth = 1
  ) +
  # Actual 2025 observations
  geom_point(
    data = test_data,
    aes(x = mean_radiance, y = grdp_per_capita, color = "2025 actual"),
    size = 3,
    shape = 16
  ) +
  # Predicted 2025 observations
  geom_point(
    data = test_data,
    aes(x = mean_radiance, y = predictions, color = "2025 predicted"),
    size = 3,
    shape = 4,
    stroke = 1.2
  ) +
  scale_color_manual(
    name = "Observation",
    values = c(
      "Training data" = "gray50",
      "2025 actual" = "red",
      "2025 predicted" = "darkgreen"
    )
  ) +
  labs(
    title = "Linear Regression: GRDP per Capita vs. Nighttime Radiance",
    subtitle = "Model trained on 2020–2024; evaluated on 2025",
    x = "Mean nighttime radiance (nW/cm²/sr)",
    y = "GRDP per capita",
    caption = "Blue line: fitted regression; shaded area: 95% confidence interval"
  ) +
  theme_minimal(base_size = 12) +
  theme(legend.position = "bottom")

print(p)
)
