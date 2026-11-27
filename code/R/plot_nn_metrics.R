plot_nn_metrics <- function(nn_results) {
  
  # Select the decay rate minimizing RMSE for each number of neurons.
  nn_best <- nn_results |>
    dplyr::group_by(size) |>
    dplyr::slice_min(
      holdout_RMSE,
      n = 1,
      with_ties = FALSE
    ) |>
    dplyr::ungroup() |>
    dplyr::arrange(size)
  
  # Identify the neuron count with the lowest overall holdout RMSE.
  selected_nn <- nn_best |>
    dplyr::slice_min(
      holdout_RMSE,
      n = 1,
      with_ties = FALSE
    )
  
  # p1: 2025 holdout RMSE.
  p1 <- ggplot2::ggplot(
    nn_best,
    ggplot2::aes(x = size, y = holdout_RMSE)
  ) +
    ggplot2::geom_line(color = "#0072B2", linewidth = 0.8) +
    ggplot2::geom_point(
      ggplot2::aes(color = size == selected_nn$size),
      size = 2.5
    ) +
    ggplot2::scale_color_manual(
      values = c("FALSE" = "#0072B2", "TRUE" = "#D55E00"),
      guide = "none"
    ) +
    ggplot2::geom_vline(
      xintercept = selected_nn$size,
      linetype = "dashed",
      color = "#D55E00"
    ) +
    ggplot2::labs(
      title = "Neural network: 2025 RMSE",
      x = "Number of hidden neurons",
      y = "2025 holdout RMSE"
    ) +
    ggplot2::theme_minimal()
  
  # p2: 2025 holdout R-squared.
  p2 <- ggplot2::ggplot(
    nn_best,
    ggplot2::aes(x = size, y = holdout_R_squared)
  ) +
    ggplot2::geom_line(color = "#0072B2", linewidth = 0.8) +
    ggplot2::geom_point(
      ggplot2::aes(color = size == selected_nn$size),
      size = 2.5
    ) +
    ggplot2::scale_color_manual(
      values = c("FALSE" = "#0072B2", "TRUE" = "#D55E00"),
      guide = "none"
    ) +
    ggplot2::geom_vline(
      xintercept = selected_nn$size,
      linetype = "dashed",
      color = "#D55E00"
    ) +
    ggplot2::labs(
      title = "Neural network: 2025 R-squared",
      x = "Number of hidden neurons",
      y = expression("2025 holdout " * R^2)
    ) +
    ggplot2::theme_minimal()
  
  # Return the combined plot.
  p1 + p2 + patchwork::plot_layout(ncol = 2)
}