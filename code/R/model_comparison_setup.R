prepare_model_comparison_setup <- function(
  regression_data,
  training_years = 2020:2024,
  holdout_year = 2025,
  feature_columns = c("mean_radiance", "population", "pixel_count")
) {
  regression_data$population <- regression_data$population * 1000

  training_data <- regression_data[
    regression_data$year %in% training_years,
    ,
    drop = FALSE
  ]
  holdout_data <- regression_data[
    regression_data$year == holdout_year,
    ,
    drop = FALSE
  ]
  if (!identical(sort(unique(training_data$year)), training_years) ||
      nrow(holdout_data) == 0) {
    stop("Regression data must contain 2020-2024 training and 2025 holdout rows.")
  }

  feature_means <- vapply(training_data[feature_columns], mean, numeric(1))
  feature_sds <- vapply(training_data[feature_columns], sd, numeric(1))
  if (any(!is.finite(feature_means)) ||
      any(!is.finite(feature_sds)) ||
      any(feature_sds <= 0)) {
    stop("Training features must have finite means and positive finite standard deviations.")
  }

  scaled_feature_columns <- paste0(feature_columns, "_scaled")
  for (feature in feature_columns) {
    scaled_column <- paste0(feature, "_scaled")
    regression_data[[scaled_column]] <-
      (regression_data[[feature]] - feature_means[[feature]]) /
      feature_sds[[feature]]
  }
  training_data <- regression_data[
    regression_data$year %in% training_years,
    ,
    drop = FALSE
  ]
  holdout_data <- regression_data[
    regression_data$year == holdout_year,
    ,
    drop = FALSE
  ]

  temporal_extrapolation_weights <-
    rep(1 / length(training_years), length(training_years)) +
    (holdout_year - mean(training_years)) *
      (training_years - mean(training_years)) /
      sum((training_years - mean(training_years))^2)
  names(temporal_extrapolation_weights) <- as.character(training_years)

  year_columns <- paste0("year_", training_years)
  training_year_matrix <- outer(
    training_data$year,
    training_years,
    FUN = "=="
  ) * 1
  colnames(training_year_matrix) <- year_columns
  holdout_year_matrix <- matrix(
    rep(temporal_extrapolation_weights, each = nrow(holdout_data)),
    nrow = nrow(holdout_data),
    dimnames = list(NULL, year_columns)
  )

  X_train <- cbind(
    training_year_matrix,
    as.matrix(training_data[scaled_feature_columns])
  )
  X_test <- cbind(
    holdout_year_matrix,
    as.matrix(holdout_data[scaled_feature_columns])
  )

  y_train_raw <- training_data$grdp_per_capita
  y_test_raw <- holdout_data$grdp_per_capita
  response_mean <- mean(y_train_raw)
  response_sd <- sd(y_train_raw)
  if (!is.finite(response_mean) ||
      !is.finite(response_sd) ||
      response_sd <= 0) {
    stop("Training outcomes must have a finite mean and positive finite standard deviation.")
  }
  y_train <- (y_train_raw - response_mean) / response_sd
  y_test <- (y_test_raw - response_mean) / response_sd

  if (any(!is.finite(X_train)) ||
      any(!is.finite(X_test)) ||
      any(!is.finite(y_train)) ||
      any(!is.finite(y_test))) {
    stop("The standardized training and holdout data must be finite.")
  }

  list(
    regression_data = regression_data,
    training_data = training_data,
    holdout_data = holdout_data,
    training_years = training_years,
    holdout_year = holdout_year,
    feature_columns = feature_columns,
    scaled_feature_columns = scaled_feature_columns,
    feature_means = feature_means,
    feature_sds = feature_sds,
    temporal_extrapolation_weights = temporal_extrapolation_weights,
    X_train = X_train,
    X_test = X_test,
    y_train = y_train,
    y_test = y_test,
    y_train_raw = y_train_raw,
    y_test_raw = y_test_raw,
    response_mean = response_mean,
    response_sd = response_sd
  )
}

fit_ols_comparison <- function(model_setup) {
  fit <- lm.fit(
    x = model_setup$X_train,
    y = model_setup$y_train
  )
  if (fit$rank < ncol(model_setup$X_train) ||
      any(!is.finite(fit$coefficients))) {
    stop("The shared OLS reference design matrix is rank deficient.")
  }
  training_predicted_scaled <- as.vector(
    model_setup$X_train %*% fit$coefficients
  )
  holdout_predicted_scaled <- as.vector(
    model_setup$X_test %*% fit$coefficients
  )
  list(
    coefficients = fit$coefficients,
    training = data.frame(
      province = model_setup$training_data$province,
      year = model_setup$training_data$year,
      actual = model_setup$y_train_raw,
      predicted = training_predicted_scaled * model_setup$response_sd +
        model_setup$response_mean,
      actual_scaled = model_setup$y_train,
      predicted_scaled = training_predicted_scaled
    ),
    holdout = data.frame(
      province = model_setup$holdout_data$province,
      year = model_setup$holdout_year,
      actual = model_setup$y_test_raw,
      predicted = holdout_predicted_scaled * model_setup$response_sd +
        model_setup$response_mean,
      actual_scaled = model_setup$y_test,
      predicted_scaled = holdout_predicted_scaled
    )
  )
}

fit_ols_holdout_reference <- function(model_setup) {
  ols <- fit_ols_comparison(model_setup)
  result <- ols$holdout
  result$residual <- result$actual - result$predicted
  result$residual_scaled <- result$actual_scaled - result$predicted_scaled
  result
}

write_model_comparison_diagnostics <- function(
  model_name,
  training_data,
  holdout_data,
  training_fitted,
  holdout_fitted,
  ols_training,
  ols_holdout,
  data_output_dir,
  figure_output_dir,
  file_prefix,
  feature_columns
) {
  make_split_diagnostics <- function(data, fitted, ols_fitted, split) {
    if (length(fitted) != nrow(data) ||
        length(ols_fitted) != nrow(data) ||
        any(!is.finite(fitted)) ||
        any(!is.finite(ols_fitted))) {
      stop(sprintf(
        "%s model predictions must be finite and match the data rows.",
        split
      ))
    }
    diagnostics <- data.frame(
      province = data$province,
      year = data$year,
      year_factor = factor(data$year),
      actual = data$grdp_per_capita,
      model_fitted = fitted,
      model_residual = data$grdp_per_capita - fitted,
      ols_fitted = ols_fitted,
      ols_residual = data$grdp_per_capita - ols_fitted,
      split = split
    )
    for (feature in feature_columns) {
      diagnostics[[feature]] <- data[[feature]]
    }
    diagnostics$standardized_residual <-
      diagnostics$model_residual /
      max(sd(diagnostics$model_residual), .Machine$double.eps)
    diagnostics$scale_location <-
      sqrt(abs(diagnostics$standardized_residual))
    diagnostics
  }

  training_diagnostics <- make_split_diagnostics(
    training_data,
    training_fitted,
    ols_training,
    "training"
  )
  holdout_diagnostics <- make_split_diagnostics(
    holdout_data,
    holdout_fitted,
    ols_holdout,
    "holdout"
  )

  calculate_metrics <- function(actual, fitted, split, label) {
    residual <- actual - fitted
    total_sum_squares <- sum((actual - mean(actual))^2)
    if (!is.finite(total_sum_squares) || total_sum_squares <= 0) {
      stop(sprintf("%s outcomes must have positive finite variance.", split))
    }
    data.frame(
      split = split,
      model = label,
      R_squared = 1 - sum(residual^2) / total_sum_squares,
      RMSE = sqrt(mean(residual^2))
    )
  }
  model_comparison <- rbind(
    calculate_metrics(
      training_diagnostics$actual,
      training_diagnostics$model_fitted,
      "training",
      model_name
    ),
    calculate_metrics(
      training_diagnostics$actual,
      training_diagnostics$ols_fitted,
      "training",
      "Ordinary least squares reference"
    ),
    calculate_metrics(
      holdout_diagnostics$actual,
      holdout_diagnostics$model_fitted,
      "holdout",
      model_name
    ),
    calculate_metrics(
      holdout_diagnostics$actual,
      holdout_diagnostics$ols_fitted,
      "holdout",
      "Ordinary least squares reference"
    )
  )

  utils::write.csv(
    model_comparison,
    file.path(data_output_dir, paste0(file_prefix, "_comparison_metrics.csv")),
    row.names = FALSE
  )
  utils::write.csv(
    training_diagnostics,
    file.path(data_output_dir, paste0(file_prefix, "_training_diagnostics.csv")),
    row.names = FALSE
  )
  utils::write.csv(
    holdout_diagnostics,
    file.path(data_output_dir, paste0(file_prefix, "_holdout_diagnostics.csv")),
    row.names = FALSE
  )

  make_plots <- function(diagnostics, split) {
    actual_fitted <- ggplot2::ggplot(diagnostics) +
      ggplot2::geom_point(
        ggplot2::aes(x = actual, y = model_fitted, color = model_name),
        alpha = 0.65
      ) +
      ggplot2::geom_point(
        ggplot2::aes(x = actual, y = ols_fitted, color = "OLS reference"),
        shape = 1,
        alpha = 0.65
      ) +
      ggplot2::geom_abline(
        slope = 1,
        intercept = 0,
        linetype = 2,
        color = "gray35"
      ) +
      ggplot2::scale_color_manual(
        values = stats::setNames(c("#0072B2", "#D55E00"),
                                 c(model_name, "OLS reference"))
      ) +
      ggplot2::labs(
        title = paste(toupper(split), "actual vs fitted"),
        x = "Actual GRDP per capita",
        y = "Fitted GRDP per capita",
        color = NULL
      ) +
      ggplot2::theme_minimal()

    residual_fitted <- ggplot2::ggplot(
      diagnostics,
      ggplot2::aes(x = model_fitted, y = model_residual)
    ) +
      ggplot2::geom_point(color = "#0072B2", alpha = 0.65) +
      ggplot2::geom_hline(yintercept = 0, linetype = 2) +
      ggplot2::labs(
        title = paste(model_name, "residual vs fitted"),
        x = "Fitted values",
        y = "Residual"
      ) +
      ggplot2::theme_minimal()
    ols_residual_fitted <- ggplot2::ggplot(
      diagnostics,
      ggplot2::aes(x = ols_fitted, y = ols_residual)
    ) +
      ggplot2::geom_point(color = "#D55E00", alpha = 0.65) +
      ggplot2::geom_hline(yintercept = 0, linetype = 2) +
      ggplot2::labs(
        title = "OLS residual vs fitted",
        x = "OLS fitted values",
        y = "OLS residual"
      ) +
      ggplot2::theme_minimal()
    residual_qq <- ggplot2::ggplot(
      diagnostics,
      ggplot2::aes(sample = model_residual)
    ) +
      ggplot2::stat_qq(color = "#0072B2", alpha = 0.65) +
      ggplot2::stat_qq_line(color = "#D55E00") +
      ggplot2::labs(
        title = "Model residual Q-Q",
        x = "Theoretical quantiles",
        y = "Sample quantiles"
      ) +
      ggplot2::theme_minimal()
    scale_location <- ggplot2::ggplot(
      diagnostics,
      ggplot2::aes(x = model_fitted, y = scale_location)
    ) +
      ggplot2::geom_point(color = "#0072B2", alpha = 0.65) +
      ggplot2::labs(
        title = "Scale-location",
        x = "Fitted values",
        y = expression(sqrt("|standardized residual|"))
      ) +
      ggplot2::theme_minimal()
    feature_plots <- lapply(feature_columns, function(feature) {
      ggplot2::ggplot(
        diagnostics,
        ggplot2::aes(
          x = .data[[feature]],
          y = model_residual
        )
      ) +
        ggplot2::geom_point(color = "#0072B2", alpha = 0.65) +
        ggplot2::geom_hline(yintercept = 0, linetype = 2) +
        ggplot2::labs(
          title = paste("Residual vs", gsub("_", " ", feature)),
          x = gsub("_", " ", feature),
          y = "Model residual"
        ) +
        ggplot2::theme_minimal()
    })
    residual_by_year <- ggplot2::ggplot(
      diagnostics,
      ggplot2::aes(x = year_factor, y = model_residual)
    ) +
      ggplot2::geom_boxplot(fill = "#B8D8E8", color = "#0072B2") +
      ggplot2::geom_hline(yintercept = 0, linetype = 2) +
      ggplot2::labs(
        title = "Residual distribution by year",
        x = "Year",
        y = "Model residual"
      ) +
      ggplot2::theme_minimal()

    diagnostic_plot <- patchwork::wrap_plots(
      c(
        list(residual_fitted, ols_residual_fitted, residual_qq, scale_location),
        feature_plots,
        list(residual_by_year)
      ),
      ncol = 4
    ) +
      patchwork::plot_annotation(
        title = paste(model_name, split, "residual diagnostics")
      )
    list(actual_fitted = actual_fitted, diagnostics = diagnostic_plot)
  }

  for (split in c("training", "holdout")) {
    diagnostics <- if (split == "training") {
      training_diagnostics
    } else {
      holdout_diagnostics
    }
    plots <- make_plots(diagnostics, split)
    ggplot2::ggsave(
      file.path(
        figure_output_dir,
        paste0(file_prefix, "_", split, "_actual_vs_fitted.png")
      ),
      plots$actual_fitted,
      width = 11.25,
      height = 6.875,
      dpi = 160
    )
    ggplot2::ggsave(
      file.path(
        figure_output_dir,
        paste0(file_prefix, "_", split, "_residual_diagnostics.png")
      ),
      plots$diagnostics,
      width = 14,
      height = 8,
      dpi = 180
    )
  }

  model_comparison
}
