plot_ridge_lambda_metrics <- function(
    lambda_results,
    selected_lambda
) {
  
  # p1: 2025 holdout RMSE.
  p1 <- ggplot2::ggplot(
    lambda_results,
    ggplot2::aes(x = lambda, y = holdout_RMSE)
  ) +
    ggplot2::geom_line(color = "#0072B2", linewidth = 0.8) +
    ggplot2::geom_point(
      ggplot2::aes(color = lambda == selected_lambda),
      size = 2.5
    ) +
    ggplot2::scale_color_manual(
      values = c("FALSE" = "#0072B2", "TRUE" = "#D55E00"),
      guide = "none"
    ) +
    ggplot2::scale_x_log10() +
    ggplot2::geom_vline(
      xintercept = selected_lambda,
      linetype = "dashed",
      color = "#D55E00"
    ) +
    ggplot2::labs(
      title = "Ridge penalty grid: 2025 RMSE",
      x = expression(lambda),
      y = "2025 holdout RMSE"
    ) +
    ggplot2::theme_minimal()
  
  # p2: 2025 holdout R-squared.
  p2 <- ggplot2::ggplot(
    lambda_results,
    ggplot2::aes(x = lambda, y = holdout_R_squared)
  ) +
    ggplot2::geom_line(color = "#0072B2", linewidth = 0.8) +
    ggplot2::geom_point(
      ggplot2::aes(color = lambda == selected_lambda),
      size = 2.5
    ) +
    ggplot2::scale_color_manual(
      values = c("FALSE" = "#0072B2", "TRUE" = "#D55E00"),
      guide = "none"
    ) +
    ggplot2::scale_x_log10() +
    ggplot2::geom_vline(
      xintercept = selected_lambda,
      linetype = "dashed",
      color = "#D55E00"
    ) +
    ggplot2::labs(
      title = "Ridge penalty grid: 2025 R-squared",
      x = expression(lambda),
      y = expression("2025 holdout " * R^2)
    ) +
    ggplot2::theme_minimal()
  
  # Return the combined plot.
  p1 + p2 + patchwork::plot_layout(ncol = 2)
}