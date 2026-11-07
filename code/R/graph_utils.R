library(ggplot2)

# Reusable scatterplot function
residual_plot <- function(data, x, y, title, xlab, ylab,
                          log_x = FALSE, smooth = TRUE,
                          zero_line = TRUE) {
  
  p <- ggplot(data, aes(x = .data[[x]], y = .data[[y]])) +
    geom_point(color = "#0072B2", alpha = 0.65, size = 1.8) +
    labs(title = title, x = xlab, y = ylab) +
    theme_minimal()
  
  if (zero_line) {
    p <- p + geom_hline(yintercept = 0, linetype = 2)
  }
  
  if (smooth) {
    p <- p +
      geom_line(
        data = lowess_data(
          data[[x]],
          data[[y]]
        ),
        aes(x = x, y = y),
        inherit.aes = FALSE,
        color = "#D55E00",
        linewidth = 0.8
      )
  }
  
  if (log_x) {
    p <- p + scale_x_log10()
  }
  
  p
}


# Lowes's smooth
lowess_data <- function(x, y) {
  result <- lowess(x, y)
  
  data.frame(
    x = result$x,
    y = result$y
  )
}