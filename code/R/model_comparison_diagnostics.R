prepare_model_diagnostics <- function(
    data,
    fitted,
    comparison_fitted = NULL,
    model_name = "Model 1",
    comparison_name = "Model 2",
    feature_columns = c("mean_radiance", "population", "pixel_count")
) {
  # Validate prediction lengths and values.
  if (length(fitted) != nrow(data) || any(!is.finite(fitted))) {
    stop("Primary model predictions must be finite and match the number of observations.")
  }
  
  if (!is.null(comparison_fitted) &&
      (length(comparison_fitted) != nrow(data) ||
       any(!is.finite(comparison_fitted)))) {
    stop("Comparison model predictions must be finite and match the number of observations.")
  }
  
  actual <- data$grdp_per_capita
  
  # Calculate model performance metrics.
  calculate_metrics <- function(actual, predicted) {
    residuals <- actual - predicted
    
    data.frame(
      R_squared = 1 - sum(residuals^2) /
        sum((actual - mean(actual))^2),
      RMSE = sqrt(mean(residuals^2))
    )
  }
  
  model_metrics <- calculate_metrics(actual, fitted)
  model_metrics$Model <- model_name
  
  if (!is.null(comparison_fitted)) {
    comparison_metrics <- calculate_metrics(actual, comparison_fitted)
    comparison_metrics$Model <- comparison_name
    
    metrics <- rbind(model_metrics, comparison_metrics)
  } else {
    metrics <- model_metrics
  }
  
  # Calculate residuals and standardized residuals.
  model_residual <- actual - fitted
  residual_sd <- sd(model_residual)
  
  diagnostics <- data.frame(
    province = data$province,
    year = data$year,
    actual = actual,
    model_fitted = fitted,
    model_residual = model_residual,
    model_standardized_residual =
      model_residual / residual_sd
  )
  
  diagnostics$scale_location <-
    sqrt(abs(diagnostics$model_standardized_residual))
  
  # Add comparison model predictions and residuals when provided.
  if (!is.null(comparison_fitted)) {
    diagnostics$comparison_fitted <- comparison_fitted
    diagnostics$comparison_residual <- actual - comparison_fitted
  }
  
  # Add predictor variables for residual diagnostic plots.
  for (feature in feature_columns) {
    diagnostics[[feature]] <- data[[feature]]
  }
  
  return(list(
    diagnostics = diagnostics,
    metrics = metrics
  ))
}