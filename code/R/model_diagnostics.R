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

plot_actual_vs_fitted <- function(
    data,
    fitted,
    model_name = "Model 1"
) {
  if (length(fitted) != nrow(data) ||
      any(!is.finite(fitted))) {
    stop("Predictions must be finite and match the data rows.")
  }
  
  plot_data <- data.frame(
    actual = data$grdp_per_capita,
    fitted = fitted
  )
  
  ggplot2::ggplot(
    plot_data,
    ggplot2::aes(x = actual, y = fitted)
  ) +
    ggplot2::geom_point(
      color = "#0072B2",
      alpha = 0.65
    ) +
    ggplot2::geom_abline(
      slope = 1,
      intercept = 0,
      linetype = 2,
      color = "gray35"
    ) +
    ggplot2::labs(
      title = paste(model_name, "actual vs fitted"),
      x = "Actual GRDP per capita",
      y = "Fitted GRDP per capita"
    ) +
    ggplot2::theme_minimal()
}

plot_residual_diagnostics <- function(
    diagnostics,
    model_name = "Model 1",
    comparison_name = "Model 2",
    feature_columns = c("mean_radiance", "population", "pixel_count")
) {
  
  # General residual plot function with LOWESS smoothing.
  residual_plot <- function(
    data,
    x,
    y,
    title,
    x_label,
    y_label,
    log_x = FALSE,
    smooth = TRUE,
    color = "#0072B2",
    smooth_color = "#D55E00"
  ) {
    p <- ggplot2::ggplot(
      data,
      ggplot2::aes(x = .data[[x]], y = .data[[y]])
    ) +
      ggplot2::geom_point(
        color = color,
        alpha = 0.65
      ) +
      ggplot2::geom_hline(
        yintercept = 0,
        linetype = 2
      ) +
      ggplot2::labs(
        title = title,
        x = x_label,
        y = y_label
      ) +
      ggplot2::theme_minimal()
    
    if (smooth) {
      p <- p +
        ggplot2::geom_smooth(
          method = "loess",
          formula = y ~ x,
          se = FALSE,
          color = smooth_color,
          linewidth = 0.8
        )
    }
    
    if (log_x) {
      p <- p + ggplot2::scale_x_log10()
    }
    
    p
  }
  
  # 1. Model 1: residual vs fitted.
  p1 <- residual_plot(
    diagnostics,
    "model_fitted", "model_residual",
    paste(model_name, "residual vs fitted"),
    "Fitted values", "Residual"
  )
  
  # 2. Model 2: residual vs fitted.
  p2 <- residual_plot(
    diagnostics,
    "comparison_fitted", "comparison_residual",
    paste(comparison_name, "residual vs fitted"),
    "Fitted values", "Residual",
    color = "#D55E00",
    smooth_color = "#0072B2"
  )
  
  # 3. Normal Q-Q plot.
  p3 <- ggplot2::ggplot(
    diagnostics,
    ggplot2::aes(sample = model_residual)
  ) +
    ggplot2::stat_qq(color = "#0072B2", alpha = 0.65) +
    ggplot2::stat_qq_line(color = "#D55E00") +
    ggplot2::labs(
      title = paste(model_name, "residual normal Q-Q"),
      x = "Theoretical quantiles",
      y = "Sample quantiles"
    ) +
    ggplot2::theme_minimal()
  
  # 4. Scale-location plot.
  p4 <- residual_plot(
    diagnostics,
    "model_fitted", "scale_location",
    paste(model_name, "scale-location"),
    "Fitted values",
    expression(sqrt("|standardized residual|")),
    smooth = TRUE
  )
  
  # 5–7. Residuals against predictor variables.
  feature_plots <- lapply(feature_columns, function(feature) {
    residual_plot(
      diagnostics,
      feature,
      "model_residual",
      paste("Residual vs", gsub("_", " ", feature)),
      gsub("_", " ", feature),
      "Model residual",
      log_x = feature == "population"
    )
  })
  
  # 8. Residual distribution by year.
  p8 <- ggplot2::ggplot(
    diagnostics,
    ggplot2::aes(x = factor(year), y = model_residual)
  ) +
    ggplot2::geom_boxplot(
      fill = "#B8D8E8",
      color = "#0072B2"
    ) +
    ggplot2::geom_hline(yintercept = 0, linetype = 2) +
    ggplot2::labs(
      title = "Residual distribution by year",
      x = "Year",
      y = "Model residual"
    ) +
    ggplot2::theme_minimal()
  
  # Combine the eight plots.
  diagnostic_plot <- patchwork::wrap_plots(
    c(list(p1, p2, p3, p4), feature_plots, list(p8)),
    ncol = 4
  ) +
    patchwork::plot_annotation(
      title = paste(model_name, "and", comparison_name,
                    "residual diagnostics")
    )
  
  return(list(
    individual = list(
      residual_fitted = p1,
      comparison_residual_fitted = p2,
      qq = p3,
      scale_location = p4,
      feature_plots = feature_plots,
      residual_by_year = p8
    ),
    combined = diagnostic_plot
  ))
}

plot_model_comparison <- function(
    data,
    fitted,
    comparison_fitted,
    model_name = "Model 1",
    comparison_name = "Model 2"
) {
  if (length(fitted) != nrow(data) ||
      length(comparison_fitted) != nrow(data) ||
      any(!is.finite(fitted)) ||
      any(!is.finite(comparison_fitted))) {
    stop("Model predictions must be finite and match the data rows.")
  }
  
  plot_data <- data.frame(
    actual = rep(data$grdp_per_capita, 2),
    fitted = c(fitted, comparison_fitted),
    model = factor(
      rep(c(model_name, comparison_name), each = nrow(data)),
      levels = c(model_name, comparison_name)
    )
  )
  
  ggplot2::ggplot(
    plot_data,
    ggplot2::aes(
      x = actual,
      y = fitted,
      color = model,
      shape = model
    )
  ) +
    ggplot2::geom_point(alpha = 0.65, size = 2) +
    ggplot2::geom_abline(
      slope = 1,
      intercept = 0,
      linetype = 2,
      color = "gray35"
    ) +
    ggplot2::scale_color_manual(
      values = c("#0072B2", "#D55E00")
    ) +
    ggplot2::scale_shape_manual(
      values = c(16, 1)
    ) +
    ggplot2::labs(
      title = "Actual vs fitted: model comparison",
      x = "Actual GRDP per capita",
      y = "Fitted GRDP per capita",
      color = NULL,
      shape = NULL
    ) +
    ggplot2::theme_minimal()
}