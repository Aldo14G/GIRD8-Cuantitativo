library(readr)
library(dplyr)
library(jsonlite)

extract_snapshot_date <- function(path) {
  name <- basename(path)
  m <- regexpr("(20[0-9]{6})", name, perl = TRUE)
  if (m < 0) return(NA_character_)
  regmatches(name, m)
}

latest_in_set <- function(paths) {
  if (length(paths) == 0) return(NA_character_)
  paths[which.max(file.info(paths)$mtime)]
}

find_latest_file <- function(dir_path, pattern) {
  files <- list.files(dir_path, pattern = pattern, full.names = TRUE)
  if (length(files) == 0) return(NA_character_)
  latest_in_set(files)
}

parse_list_col <- function(x) {
  if (is.null(x)) return(list())
  lapply(x, function(v) {
    if (is.na(v) || !nzchar(v)) return(character())
    txt <- trimws(v)
    txt <- gsub("^\\[", "", txt)
    txt <- gsub("\\]$", "", txt)
    if (!nzchar(txt)) return(character())
    parts <- strsplit(txt, "\\s*,\\s*")[[1]]
    parts <- gsub("^'|'$|^\"|\"$", "", parts)
    trimws(parts)
  })
}

snapshot_index <- function(data_root = NULL) {
  if (is.null(data_root)) {
    data_root <- normalizePath(file.path("..", "Data", "files", "data"), winslash = "/", mustWork = FALSE)
  }

  silver_dir <- file.path(data_root, "silver")
  gold_dir <- file.path(data_root, "gold")

  ds <- list.files(silver_dir, pattern = "^evaluated_datasets_.*\\.csv$", full.names = TRUE)
  org <- list.files(silver_dir, pattern = "^evaluated_organizations_.*\\.csv$", full.names = TRUE)
  dlt <- list.files(gold_dir, pattern = "^delta_dependencias_.*\\.csv$", full.names = TRUE)
  rpt <- list.files(gold_dir, pattern = "^report_longitudinal_.*\\.json$", full.names = TRUE)

  dates <- sort(unique(na.omit(c(
    vapply(ds, extract_snapshot_date, character(1)),
    vapply(org, extract_snapshot_date, character(1)),
    vapply(dlt, extract_snapshot_date, character(1)),
    vapply(rpt, extract_snapshot_date, character(1))
  ))), decreasing = TRUE)

  if (length(dates) == 0) {
    return(data.frame(
      snapshot_date = character(0),
      has_datasets = logical(0),
      has_organizations = logical(0),
      has_delta = logical(0),
      has_report = logical(0),
      stringsAsFactors = FALSE
    ))
  }

  data.frame(
    snapshot_date = dates,
    has_datasets = dates %in% vapply(ds, extract_snapshot_date, character(1)),
    has_organizations = dates %in% vapply(org, extract_snapshot_date, character(1)),
    has_delta = dates %in% vapply(dlt, extract_snapshot_date, character(1)),
    has_report = dates %in% vapply(rpt, extract_snapshot_date, character(1)),
    stringsAsFactors = FALSE
  )
}

load_snapshot_data <- function(snapshot_date = NULL, data_root = NULL) {
  if (is.null(data_root)) {
    data_root <- normalizePath(file.path("..", "Data", "files", "data"), winslash = "/", mustWork = FALSE)
  }

  silver_dir <- file.path(data_root, "silver")
  gold_dir <- file.path(data_root, "gold")

  ds_all <- list.files(silver_dir, pattern = "^evaluated_datasets_.*\\.csv$", full.names = TRUE)
  org_all <- list.files(silver_dir, pattern = "^evaluated_organizations_.*\\.csv$", full.names = TRUE)
  dlt_all <- list.files(gold_dir, pattern = "^delta_dependencias_.*\\.csv$", full.names = TRUE)
  rpt_all <- list.files(gold_dir, pattern = "^report_longitudinal_.*\\.json$", full.names = TRUE)

  choose_for_date <- function(paths) {
    if (length(paths) == 0) return(NA_character_)
    if (is.null(snapshot_date)) return(latest_in_set(paths))
    dated <- paths[vapply(paths, extract_snapshot_date, character(1)) == snapshot_date]
    if (length(dated) == 0) return(NA_character_)
    latest_in_set(dated)
  }

  ds_path <- choose_for_date(ds_all)
  org_path <- choose_for_date(org_all)
  dlt_path <- choose_for_date(dlt_all)
  rpt_path <- choose_for_date(rpt_all)

  if (is.na(ds_path) && length(ds_all) > 0) ds_path <- latest_in_set(ds_all)
  if (is.na(org_path) && length(org_all) > 0) org_path <- latest_in_set(org_all)
  if (is.na(dlt_path) && length(dlt_all) > 0) dlt_path <- latest_in_set(dlt_all)
  if (is.na(rpt_path) && length(rpt_all) > 0) rpt_path <- latest_in_set(rpt_all)

  datasets <- NULL
  orgs <- NULL
  delta <- NULL
  report <- NULL

  if (!is.na(ds_path)) {
    datasets <- readr::read_csv(ds_path, show_col_types = FALSE)
    for (col in c("formats", "groups", "tags", "csv_paths")) {
      if (col %in% names(datasets)) {
        datasets[[col]] <- parse_list_col(datasets[[col]])
      }
    }
  }

  if (!is.na(org_path)) {
    orgs <- readr::read_csv(org_path, show_col_types = FALSE)
  }

  if (!is.na(dlt_path)) {
    delta <- readr::read_csv(dlt_path, show_col_types = FALSE)
  }

  if (!is.na(rpt_path)) {
    report <- jsonlite::fromJSON(rpt_path, simplifyVector = TRUE)
  }

  list(
    datasets = datasets,
    organizations = orgs,
    delta = delta,
    report = report,
    paths = list(
      datasets = ds_path,
      organizations = org_path,
      delta = dlt_path,
      report = rpt_path
    )
  )
}
