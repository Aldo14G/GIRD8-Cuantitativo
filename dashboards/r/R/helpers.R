format_pct <- function(x, digits = 1) {
  ifelse(is.na(x), "NA", paste0(round(x * 100, digits), "%"))
}

format_score <- function(x, digits = 3) {
  ifelse(is.na(x), "NA", format(round(x, digits), nsmall = digits))
}

safe_first <- function(x, fallback = NA_character_) {
  if (length(x) == 0 || all(is.na(x))) {
    return(fallback)
  }
  x[[1]]
}

score_badge_color <- function(score) {
  if (is.na(score)) return("#95a5a6")
  if (score >= 0.80) return("#2e7d32")
  if (score >= 0.65) return("#f9a825")
  if (score >= 0.50) return("#ef6c00")
  if (score >= 0.35) return("#d84315")
  "#b71c1c"
}

delta_color <- function(delta) {
  if (is.na(delta)) return("#95a5a6")
  if (delta > 0.02) return("#2e7d32")
  if (delta < -0.02) return("#b71c1c")
  "#f9a825"
}
