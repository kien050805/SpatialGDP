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