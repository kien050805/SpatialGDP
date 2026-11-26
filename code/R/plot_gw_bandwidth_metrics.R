plot_gw_bandwidth_metrics <- function(
    bandwidth_results,
    selected_bandwidth
) {
  
  # p1: 2025 holdout RMSE.
  p1 <- ggplot2::ggplot(
    bandwidth_results,
    ggplot2::aes(x = bandwidth, y = holdout_RMSE)
  ) +
    ggplot2::geom_line(color = "#0072B2", linewidth = 0.8) +
    ggplot2::geom_point(
      ggplot2::aes(color = bandwidth == selected_bandwidth),
      size = 2.5
    ) +
    ggplot2::scale_color_manual(
      values = c("FALSE" = "#0072B2", "TRUE" = "#D55E00"),
      guide = "none"
    ) +
    ggplot2::scale_x_log10() +
    ggplot2::geom_vline(
      xintercept = selected_bandwidth,
      linetype = "dashed",
      color = "#D55E00"
    ) +
    ggplot2::labs(
      title = "GW bandwidth grid: 2025 RMSE",
      x = expression(bandwidth),
      y = "2025 holdout RMSE"
    ) +
    ggplot2::theme_minimal()
  
  # p2: 2025 holdout R-squared.
  p2 <- ggplot2::ggplot(
    bandwidth_results,
    ggplot2::aes(x = bandwidth, y = holdout_R_squared)
  ) +
    ggplot2::geom_line(color = "#0072B2", linewidth = 0.8) +
    ggplot2::geom_point(
      ggplot2::aes(color = bandwidth == selected_bandwidth),
      size = 2.5
    ) +
    ggplot2::scale_color_manual(
      values = c("FALSE" = "#0072B2", "TRUE" = "#D55E00"),
      guide = "none"
    ) +
    ggplot2::scale_x_log10() +
    ggplot2::geom_vline(
      xintercept = selected_bandwidth,
      linetype = "dashed",
      color = "#D55E00"
    ) +
    ggplot2::labs(
      title = "GW bandwidth grid: 2025 R-squared",
      x = expression(bandwidth),
      y = expression("2025 holdout " * R^2)
    ) +
    ggplot2::theme_minimal()
  
  # Return the combined plot.
  p1 + p2 + patchwork::plot_layout(ncol = 2)
}