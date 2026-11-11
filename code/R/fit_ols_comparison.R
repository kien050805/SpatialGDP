fit_ols_comparison <- function(model_data) {
  # Fit ols model
  fit <- lm.fit(
    x = model_data$X_train,
    y = model_data$y_train
  )
  
  # Generate predictions.
  training_predicted_scaled <- as.vector(
    model_data$X_train %*% fit$coefficients
  )
  
  holdout_predicted_scaled <- as.vector(
    model_data$X_test %*% fit$coefficients
  )
  
  # Construct training predictions.
  training <- data.frame(
    province = model_data$training_data$province,
    year = model_data$training_data$year,
    actual = model_data$y_train_raw,
    predicted = training_predicted_scaled *
      model_data$response_sd + model_data$response_mean,
    actual_scaled = model_data$y_train,
    predicted_scaled = training_predicted_scaled
  )
  
  # Construct holdout predictions.
  holdout <- data.frame(
    province = model_data$holdout_data$province,
    year = model_data$holdout_year,
    actual = model_data$y_test_raw,
    predicted = holdout_predicted_scaled *
      model_data$response_sd + model_data$response_mean,
    actual_scaled = model_data$y_test,
    predicted_scaled = holdout_predicted_scaled
  )
  
  # Calculate residuals.
  training$residual <- training$actual - training$predicted
  training$residual_scaled <-
    training$actual_scaled - training$predicted_scaled
  
  holdout$residual <- holdout$actual - holdout$predicted
  holdout$residual_scaled <-
    holdout$actual_scaled - holdout$predicted_scaled
  
  # Calculate performance metrics on the original response scale.
  calculate_metrics <- function(actual, predicted) {
    list(
      R_squared = 1 - sum((actual - predicted)^2) /
        sum((actual - mean(actual))^2),
      RMSE = sqrt(mean((actual - predicted)^2))
    )
  }
  
  training_metrics <- calculate_metrics(
    training$actual,
    training$predicted
  )
  
  holdout_metrics <- calculate_metrics(
    holdout$actual,
    holdout$predicted
  )
  
  return(list(
    coefficients = fit$coefficients,
    training = training,
    holdout = holdout,
    metrics = list(
      training = training_metrics,
      holdout = holdout_metrics
    )
  ))
}