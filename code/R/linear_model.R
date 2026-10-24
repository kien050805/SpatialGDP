setwd("../../")

training_data <- read.csv("data/training_data/regression_dataset.csv")
train_data <- subset(training_data, year >= 2020 & year <= 2024)
test_data <- subset(training_data, year == 2025)
model <- lm(grdp_per_capita ~ mean_radiance, data = train_data)
predictions <- predict(model, newdata = test_data)
rmse <- sqrt(mean((test_data$grdp_per_capita - predictions)^2))

dir.create("code/R/model", recursive = TRUE, showWarnings = FALSE)
saveRDS(model, "code/R/model/linear_model.rds")

print(summary(model))
cat(sprintf("2025 holdout RMSE (GRDP per capita): %.4f\n", rmse))


constrained_lm <- function(y, X, a) {
  y <- as.numeric(y)
  X <- as.matrix(X)
  
  c <- colSums(X)
  beta_ols <- qr.solve(X, y)
  
  # Solve the constrained least-squares problem
  XtX_inv_c <- solve(crossprod(X), c)
  
  beta_hat <- beta_ols -
    XtX_inv_c *
    (sum(c * beta_ols) - a) /
    sum(c * XtX_inv_c)
  
  predictions <- as.vector(X %*% beta_hat)
  
  list(
    coefficients = beta_hat,
    predictions = predictions,
    residuals = y - predictions,
    SSE = sum((y - predictions)^2),
    sum_predictions = sum(predictions)
  )
}

# Prepare data
y <- train_data$grdp_per_capita

X <- model.matrix(
  ~ mean_radiance + population + pixel_count,
  data = train_data
)

# Set the desired sum of predictions
a <- 100000  # Example target: sum of observed y

# Constrained least-squares estimation
c <- colSums(X)

beta_ols <- qr.solve(X, y)

XtX_inv_c <- solve(crossprod(X), c)

beta_hat <- beta_ols -
  XtX_inv_c *
  (sum(c * beta_ols) - a) /
  sum(c * XtX_inv_c)

# Predictions
predictions <- as.vector(X %*% beta_hat)

# Results
print(beta_hat)

cat("SSE:", sum((y - predictions)^2), "\n")
cat("Target sum:", a, "\n")
cat("Predicted sum:", sum(predictions), "\n")

# Compare with ordinary least squares
ols <- lm(
  grdp_per_capita ~ mean_radiance + population + pixel_count,
  data = train_data
)

cat("OLS SSE:", sum(residuals(ols)^2), "\n")
cat("Constrained SSE:", sum((y - predictions)^2), "\n")

# OLS predictions
ols_predictions <- as.vector(predict(ols, newdata = train_data))

# Constrained model predictions
constrained_predictions <- as.vector(X %*% beta_hat)

# Compare SSE
ols_SSE <- sum((y - ols_predictions)^2)
constrained_SSE <- sum((y - constrained_predictions)^2)

cat("OLS SSE:", ols_SSE, "\n")
cat("Constrained SSE:", constrained_SSE, "\n")

# Verify the constraint
cat("Sum of constrained predictions:",
    sum(constrained_predictions), "\n")
cat("Target sum:", a, "\n")

