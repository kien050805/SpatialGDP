prepare_model_setup <- function(
    regression_data,
    training_years = 2020:2024,
    holdout_year = 2025,
    feature_columns = c("mean_radiance", "population", "pixel_count")
) {
  # Split training data and holdout data
  training_data <- regression_data[
    regression_data$year %in% training_years, , drop = FALSE
  ]
  holdout_data <- regression_data[
    regression_data$year == holdout_year, , drop = FALSE
  ]
  
  # Standardize features using training data statistics.
  feature_means <- vapply(training_data[feature_columns], mean, numeric(1))
  feature_sds <- vapply(training_data[feature_columns], sd, numeric(1))
  
  for (feature in feature_columns) {
    scaled_column <- paste0(feature, "_scaled")
    
    training_data[[scaled_column]] <-
      (training_data[[feature]] - feature_means[[feature]]) /
      feature_sds[[feature]]
    
    holdout_data[[scaled_column]] <-
      (holdout_data[[feature]] - feature_means[[feature]]) /
      feature_sds[[feature]]
  }
  
  # Calculate temporal extrapolation weights.
  temporal_weights <-
    rep(1 / length(training_years), length(training_years)) +
    (holdout_year - mean(training_years)) *
    (training_years - mean(training_years)) /
    sum((training_years - mean(training_years))^2)
  
  # Construct year indicator matrices.
  year_columns <- paste0("year_", training_years)
  
  training_year_matrix <- outer(
    training_data$year,
    training_years,
    FUN = "=="
  ) * 1
  
  holdout_year_matrix <- matrix(
    rep(temporal_weights, each = nrow(holdout_data)),
    nrow = nrow(holdout_data)
  )
  
  # Construct design matrices.
  X_train <- cbind(
    training_year_matrix,
    as.matrix(training_data[paste0(feature_columns, "_scaled")])
  )
  
  X_test <- cbind(
    holdout_year_matrix,
    as.matrix(holdout_data[paste0(feature_columns, "_scaled")])
  )
  
  colnames(X_train) <- c(year_columns, paste0(feature_columns, "_scaled"))
  colnames(X_test) <- colnames(X_train)
  
  # Standardize response using training data statistics.
  y_train_raw <- training_data$grdp_per_capita
  y_test_raw <- holdout_data$grdp_per_capita
  
  response_mean <- mean(y_train_raw)
  response_sd <- sd(y_train_raw)
  
  y_train <- (y_train_raw - response_mean) / response_sd
  y_test <- (y_test_raw - response_mean) / response_sd
  
  return(list(
    X_train = X_train,
    y_train = y_train,
    X_test = X_test,
    y_test = y_test,
    
    temporal_weights = temporal_weights,
    
    training_data = training_data,
    holdout_data = holdout_data,
    
    training_years = training_years,
    holdout_year = holdout_year,
    
    y_train_raw = y_train_raw,
    y_test_raw = y_test_raw,
    
    feature_columns = feature_columns,
    feature_means = feature_means,
    feature_sds = feature_sds,
    response_mean = response_mean,
    response_sd = response_sd
  ))
}

prepare_full_model_setup <- function(
    regression_data,
    feature_columns = c("mean_radiance", "population", "pixel_count")
) {
  # Standardize features using all data.
  feature_means <- vapply(regression_data[feature_columns], mean, numeric(1))
  feature_sds <- vapply(regression_data[feature_columns], sd, numeric(1))
  
  scaled_features <- scale(
    regression_data[feature_columns],
    center = feature_means,
    scale = feature_sds
  )
  
  # Construct year indicator matrix.
  years <- sort(unique(regression_data$year))
  
  year_matrix <- outer(
    regression_data$year,
    years,
    FUN = "=="
  ) * 1
  
  # Construct design matrix.
  X <- cbind(year_matrix, scaled_features)
  
  colnames(X) <- c(
    paste0("year_", years),
    paste0(feature_columns, "_scaled")
  )
  
  # Standardize response using all data.
  response_mean <- mean(regression_data$grdp_per_capita)
  response_sd <- sd(regression_data$grdp_per_capita)
  
  y <- (regression_data$grdp_per_capita - response_mean) / response_sd
  
  return(list(
    X = X,
    y = y,
    years = years,
    
    feature_columns = feature_columns,
    feature_means = feature_means,
    feature_sds = feature_sds,
    response_mean = response_mean,
    response_sd = response_sd
  ))
}


prepare_prediction_data <- function(
    prediction_data,
    provincial_grdp_data,
    provincial_population_data,
    feature_columns,
    feature_means,
    feature_sds
) {
  
  # Match provincial GRDP per capita and population.
  province_index <- match(
    prediction_data$level_1,
    provincial_grdp_data$province
  )
  
  population_index <- match(
    prediction_data$level_1,
    provincial_population_data$province
  )
  
  prediction_data$grdp_pc_2025 <-
    provincial_grdp_data[["2025"]][province_index]
  
  prediction_data$province_population_2025 <-
    provincial_population_data[["2025"]][population_index]
  
  # Check that all required provincial values are available.
  if (anyNA(prediction_data$grdp_pc_2025) ||
      anyNA(prediction_data$province_population_2025)) {
    stop("Missing provincial GRDP or population values.")
  }
  
  # Check feature scaling parameters.
  if (any(!is.finite(feature_sds)) || any(feature_sds <= 0)) {
    stop("All feature standard deviations must be positive and finite.")
  }
  
  # Scale features using the shared training statistics.
  for (feature in feature_columns) {
    prediction_data[[paste0(feature, "_scaled")]] <-
      (prediction_data[[feature]] - feature_means[[feature]]) /
      feature_sds[[feature]]
  }
  
  # Return prepared data and prediction features.
  return(prediction_data = prediction_data)
}
