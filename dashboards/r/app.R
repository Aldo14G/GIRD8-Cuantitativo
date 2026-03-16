library(shiny)
library(shinydashboard)
library(plotly)
library(dplyr)

source("R/helpers.R")
source("R/load_data.R")
source("R/ui_tabs.R")

data_root <- normalizePath(file.path("..", "Data", "files", "data"), winslash = "/", mustWork = FALSE)
snapshot_idx <- snapshot_index(data_root)
default_snapshot <- if (nrow(snapshot_idx) > 0) snapshot_idx$snapshot_date[[1]] else "latest"

ui <- dashboardPage(
  dashboardHeader(
    title = NULL,
    tags$li(
      class = "dropdown",
      tags$div(
        style = "text-align:right;width:100%;font-size:22px;font-weight:700;padding-right:18px;",
        "LABNL - Calidad de Datos Abiertos NL (v2026)"
      )
    )
  ),
  dashboardSidebar(
    width = 300,
    sidebarMenu(
      menuItem("Dataset", tabName = "dataset", icon = icon("table")),
      menuItem("Dependencias", tabName = "dependencias", icon = icon("building")),
      menuItem("Longitudinal", tabName = "longitudinal", icon = icon("chart-line")),
      menuItem("Contenido CSV", tabName = "contenido", icon = icon("file-csv"))
    ),
    hr(),
    selectInput("snapshot_date", "Snapshot", choices = if (nrow(snapshot_idx) > 0) snapshot_idx$snapshot_date else c("latest"), selected = default_snapshot),
    selectInput(
      "snapshot_a",
      "Comparar A",
      choices = if (nrow(snapshot_idx) > 0) snapshot_idx$snapshot_date else c("latest"),
      selected = if (nrow(snapshot_idx) > 0) snapshot_idx$snapshot_date[[min(1, nrow(snapshot_idx))]] else "latest"
    ),
    selectInput(
      "snapshot_b",
      "Comparar B",
      choices = if (nrow(snapshot_idx) > 1) snapshot_idx$snapshot_date else if (nrow(snapshot_idx) > 0) snapshot_idx$snapshot_date else c("latest"),
      selected = if (nrow(snapshot_idx) > 1) snapshot_idx$snapshot_date[[2]] else default_snapshot
    ),
    selectInput("dataset", "Seleccione un dataset", choices = NULL),
    selectInput("org", "Filtrar dependencia", choices = c("Todas"), selected = "Todas"),
    sliderInput("score_range", "Rango score final", min = 0, max = 1, value = c(0, 1), step = 0.01),
    hr(),
    h4("Fuente de datos"),
    htmlOutput("source_paths")
  ),
  dashboardBody(
    tags$head(tags$link(rel = "stylesheet", type = "text/css", href = "styles.css")),
    fluidRow(
      valueBoxOutput("vb_datasets", width = 3),
      valueBoxOutput("vb_orgs", width = 3),
      valueBoxOutput("vb_avg_score", width = 3),
      valueBoxOutput("vb_csv_cov", width = 3)
    ),
    tabItems(
      dataset_tab_ui,
      org_tab_ui,
      longitudinal_tab_ui,
      content_tab_ui
    )
  )
)

server <- function(input, output, session) {
  data_bundle <- reactive({
    snapshot <- input$snapshot_date
    if (identical(snapshot, "latest")) {
      load_snapshot_data(snapshot_date = NULL, data_root = data_root)
    } else {
      load_snapshot_data(snapshot_date = snapshot, data_root = data_root)
    }
  })

  observe({
    bundle <- data_bundle()
    datasets <- bundle$datasets
    if (!is.null(datasets) && nrow(datasets) > 0) {
      updateSelectInput(session, "dataset", choices = datasets$name, selected = datasets$name[[1]])
      org_choices <- c("Todas", sort(unique(datasets$org_title)))
      updateSelectInput(session, "org", choices = org_choices, selected = "Todas")
    } else {
      updateSelectInput(session, "dataset", choices = character(0), selected = character(0))
      updateSelectInput(session, "org", choices = c("Todas"), selected = "Todas")
    }
  })

  output$source_paths <- renderUI({
    p <- data_bundle()$paths
    tags$div(
      tags$small(tags$b("Datasets:"), tags$br(), ifelse(is.na(p$datasets), "No disponible", p$datasets)),
      tags$br(),
      tags$small(tags$b("Dependencias:"), tags$br(), ifelse(is.na(p$organizations), "No disponible", p$organizations)),
      tags$br(),
      tags$small(tags$b("Delta:"), tags$br(), ifelse(is.na(p$delta), "No disponible", p$delta)),
      tags$br(),
      tags$small(tags$b("Gold Report:"), tags$br(), ifelse(is.na(p$report), "No disponible", p$report))
    )
  })

  filtered_datasets <- reactive({
    datasets <- data_bundle()$datasets
    req(!is.null(datasets))
    df <- datasets %>%
      filter(score_final >= input$score_range[1], score_final <= input$score_range[2])
    if (!identical(input$org, "Todas")) {
      df <- df %>% filter(org_title == input$org)
    }
    df
  })

  selected_dataset <- reactive({
    datasets <- data_bundle()$datasets
    req(!is.null(datasets), input$dataset)
    datasets %>% filter(name == input$dataset) %>% slice(1)
  })

  output$vb_datasets <- renderValueBox({
    datasets <- data_bundle()$datasets
    n <- if (is.null(datasets)) 0 else nrow(filtered_datasets())
    valueBox(value = n, subtitle = "Datasets visibles", icon = icon("table"), color = "yellow")
  })

  output$vb_orgs <- renderValueBox({
    datasets <- data_bundle()$datasets
    n <- if (is.null(datasets)) 0 else dplyr::n_distinct(filtered_datasets()$org_title)
    valueBox(value = n, subtitle = "Dependencias", icon = icon("building"), color = "yellow")
  })

  output$vb_avg_score <- renderValueBox({
    datasets <- data_bundle()$datasets
    avg <- if (is.null(datasets) || nrow(filtered_datasets()) == 0) NA_real_ else mean(filtered_datasets()$score_final, na.rm = TRUE)
    valueBox(value = format_score(avg), subtitle = "Score final promedio", icon = icon("chart-bar"), color = "yellow")
  })

  output$vb_csv_cov <- renderValueBox({
    datasets <- data_bundle()$datasets
    cov <- if (is.null(datasets) || nrow(filtered_datasets()) == 0) NA_real_ else mean(filtered_datasets()$content_evaluated, na.rm = TRUE)
    valueBox(value = format_pct(cov), subtitle = "Cobertura CSV", icon = icon("file-csv"), color = "yellow")
  })

  output$dataset_summary <- renderUI({
    row <- selected_dataset()
    req(nrow(row) == 1)
    tags$div(
      tags$p(tags$b("Titulo:"), row$title),
      tags$p(tags$b("Dependencia:"), row$org_title),
      tags$p(tags$b("Score final:"), format_score(row$score_final), " (", row$grade, ")"),
      tags$p(tags$b("Meta score:"), format_score(row$meta_score)),
      tags$p(tags$b("Content score:"), format_score(row$content_score)),
      tags$p(tags$b("Recursos:"), row$num_resources),
      tags$p(tags$b("Con CSV:"), ifelse(isTRUE(row$has_csv), "Si", "No")),
      tags$p(tags$b("Ultima modificacion:"), as.character(row$metadata_modified))
    )
  })

  output$dataset_score_bar <- renderPlotly({
    row <- selected_dataset()
    req(nrow(row) == 1)
    sc <- as.numeric(row$score_final)
    plot_ly(
      x = sc,
      y = "Score Final",
      type = "bar",
      orientation = "h",
      marker = list(color = score_badge_color(sc)),
      text = format_score(sc),
      textposition = "inside",
      insidetextanchor = "middle"
    ) %>%
      layout(
        xaxis = list(title = "Score", range = c(0, 1)),
        yaxis = list(title = ""),
        margin = list(l = 90, r = 20, t = 20, b = 40)
      )
  })

  output$dataset_radar <- renderPlotly({
    row <- selected_dataset()
    req(nrow(row) == 1)
    vals <- c(
      Completitud = as.numeric(row$meta_completitud),
      Actualizacion = as.numeric(row$meta_actualizacion),
      Accesibilidad = as.numeric(row$meta_accesibilidad),
      Documentacion = as.numeric(row$meta_documentacion),
      Apertura = as.numeric(row$meta_apertura)
    )
    plot_ly(
      type = "scatterpolar",
      r = vals,
      theta = names(vals),
      fill = "toself",
      mode = "markers+lines+text",
      text = format_score(vals),
      textposition = "top right",
      marker = list(color = "#f2c94c"),
      line = list(color = "#1f2937", width = 2)
    ) %>%
      layout(
        polar = list(radialaxis = list(visible = TRUE, range = c(0, 1))),
        showlegend = FALSE,
        margin = list(l = 40, r = 40, t = 30, b = 20)
      )
  })

  output$dataset_metrics_table <- renderTable({
    row <- selected_dataset()
    req(nrow(row) == 1)
    data.frame(
      metrica = c("Meta score", "Content score", "Layers evaluated", "CSV files evaluados", "CSV total KB", "Tags", "Grupos"),
      valor = c(
        format_score(row$meta_score),
        format_score(row$content_score),
        as.character(row$layers_evaluated),
        as.character(row$content_files),
        as.character(round(as.numeric(row$csv_total_kb), 2)),
        as.character(row$num_tags),
        as.character(row$num_groups)
      )
    )
  }, striped = TRUE, hover = TRUE)

  output$org_ranking <- renderPlotly({
    orgs <- data_bundle()$organizations
    req(!is.null(orgs), nrow(orgs) > 0)
    d <- orgs %>% arrange(score_final_mean) %>% mutate(org_title = factor(org_title, levels = org_title))
    plot_ly(
      data = d,
      x = ~score_final_mean,
      y = ~org_title,
      type = "bar",
      orientation = "h",
      marker = list(color = "#f2c94c", line = list(color = "#111827", width = 1)),
      text = ~format_score(score_final_mean),
      textposition = "outside"
    ) %>%
      layout(
        xaxis = list(title = "Score final medio", range = c(0, 1)),
        yaxis = list(title = "Dependencia"),
        margin = list(l = 340, r = 40, t = 20, b = 40)
      )
  })

  output$org_grade_dist <- renderPlotly({
    orgs <- data_bundle()$organizations
    req(!is.null(orgs), nrow(orgs) > 0)
    d <- orgs %>% count(org_grade)
    plot_ly(data = d, x = ~org_grade, y = ~n, type = "bar", marker = list(color = "#1f2937")) %>%
      layout(xaxis = list(title = "Grade"), yaxis = list(title = "Dependencias"))
  })

  output$org_csv_coverage <- renderPlotly({
    orgs <- data_bundle()$organizations
    req(!is.null(orgs), nrow(orgs) > 0)
    d <- orgs %>% arrange(pct_with_csv) %>% mutate(org_title = factor(org_title, levels = org_title))
    plot_ly(
      data = d,
      x = ~pct_with_csv,
      y = ~org_title,
      type = "bar",
      orientation = "h",
      marker = list(color = "#6b7280"),
      text = ~format_pct(pct_with_csv),
      textposition = "outside"
    ) %>%
      layout(
        xaxis = list(title = "Cobertura CSV", range = c(0, 1)),
        yaxis = list(title = ""),
        margin = list(l = 340, r = 40, t = 20, b = 40)
      )
  })

  output$delta_chart <- renderPlotly({
    delta <- data_bundle()$delta
    req(!is.null(delta), nrow(delta) > 0)
    d <- delta %>% mutate(org_title = factor(org_title, levels = org_title[order(delta_score_final_mean)]))
    colors <- vapply(d$delta_score_final_mean, delta_color, character(1))
    plot_ly(
      data = d,
      x = ~delta_score_final_mean,
      y = ~org_title,
      type = "bar",
      orientation = "h",
      marker = list(color = colors),
      text = ~round(delta_score_final_mean, 4),
      textposition = "outside"
    ) %>%
      layout(
        xaxis = list(title = "Delta score final (2026 - 2024)", zeroline = TRUE, zerolinewidth = 2),
        yaxis = list(title = "Dependencia"),
        margin = list(l = 300, r = 40, t = 20, b = 40)
      )
  })

  output$delta_table <- renderTable({
    delta <- data_bundle()$delta
    req(!is.null(delta), nrow(delta) > 0)
    delta %>% select(org_title, score_final_mean_t0, score_final_mean_t1, delta_score_final_mean, clasificacion)
  }, striped = TRUE, hover = TRUE)

  output$gold_highlights <- renderUI({
    report <- data_bundle()$report
    if (is.null(report)) return(tags$p("No hay reporte Gold disponible."))
    hall <- report$hallazgos
    tags$div(
      tags$p(tags$b("Dependencias analizadas:"), hall$dependencias_analizadas),
      tags$p(tags$b("Delta promedio:"), hall$delta_promedio),
      tags$p(tags$b("Delta mediana:"), hall$delta_mediana),
      tags$p(tags$b("Clasificacion:"), paste(names(hall$clasificacion), hall$clasificacion, collapse = "; ")),
      tags$hr(),
      tags$p(tags$b("Modelo predictivo:"), if (!is.null(report$modelo_predictivo$error)) report$modelo_predictivo$error else "Disponible")
    )
  })

  snapshot_compare <- reactive({
    req(input$snapshot_a, input$snapshot_b)
    a_bundle <- load_snapshot_data(snapshot_date = input$snapshot_a, data_root = data_root)
    b_bundle <- load_snapshot_data(snapshot_date = input$snapshot_b, data_root = data_root)
    if (is.null(a_bundle$organizations) || is.null(b_bundle$organizations)) {
      return(NULL)
    }

    a <- a_bundle$organizations %>% select(org_title, score_a = score_final_mean)
    b <- b_bundle$organizations %>% select(org_title, score_b = score_final_mean)

    full_join(a, b, by = "org_title") %>%
      mutate(
        score_a = as.numeric(score_a),
        score_b = as.numeric(score_b),
        delta_b_minus_a = score_b - score_a
      ) %>%
      filter(!is.na(delta_b_minus_a)) %>%
      arrange(delta_b_minus_a)
  })

  output$snapshot_compare_chart <- renderPlotly({
    cmp <- snapshot_compare()
    req(!is.null(cmp), nrow(cmp) > 0)
    d <- cmp %>% mutate(org_title = factor(org_title, levels = org_title))
    colors <- vapply(d$delta_b_minus_a, delta_color, character(1))
    plot_ly(
      data = d,
      x = ~delta_b_minus_a,
      y = ~org_title,
      type = "bar",
      orientation = "h",
      marker = list(color = colors),
      text = ~round(delta_b_minus_a, 4),
      textposition = "outside"
    ) %>%
      layout(
        xaxis = list(
          title = paste0("Delta score final (", input$snapshot_b, " - ", input$snapshot_a, ")"),
          zeroline = TRUE,
          zerolinewidth = 2
        ),
        yaxis = list(title = "Dependencia"),
        margin = list(l = 300, r = 40, t = 20, b = 40)
      )
  })

  output$snapshot_compare_table <- renderTable({
    cmp <- snapshot_compare()
    req(!is.null(cmp), nrow(cmp) > 0)
    top_up <- cmp %>% arrange(desc(delta_b_minus_a)) %>% head(3)
    top_down <- cmp %>% arrange(delta_b_minus_a) %>% head(3)
    bind_rows(
      data.frame(tipo = "Mejora", dependencia = top_up$org_title, delta = round(top_up$delta_b_minus_a, 4)),
      data.frame(tipo = "Deterioro", dependencia = top_down$org_title, delta = round(top_down$delta_b_minus_a, 4))
    )
  }, striped = TRUE, hover = TRUE)

  output$content_scatter <- renderPlotly({
    datasets <- data_bundle()$datasets
    req(!is.null(datasets), nrow(filtered_datasets()) > 0)
    d <- filtered_datasets()
    plot_ly(
      data = d,
      x = ~meta_score,
      y = ~content_score,
      type = "scatter",
      mode = "markers",
      color = ~org_title,
      text = ~paste0("Dataset: ", title, "<br>Score final: ", round(score_final, 3)),
      hoverinfo = "text",
      marker = list(size = 10, opacity = 0.75)
    ) %>%
      layout(
        xaxis = list(title = "Meta score"),
        yaxis = list(title = "Content score", range = c(0, 1)),
        showlegend = FALSE
      )
  })

  output$content_notes <- renderUI({
    datasets <- data_bundle()$datasets
    req(!is.null(datasets), nrow(filtered_datasets()) > 0)
    d <- filtered_datasets()
    tags$div(
      tags$p(tags$b("Datasets con contenido evaluado:"), sum(d$content_evaluated, na.rm = TRUE), "de", nrow(d)),
      tags$p(tags$b("Promedio content score:"), format_score(mean(d$content_score, na.rm = TRUE))),
      tags$p(tags$b("Min content score:"), format_score(min(d$content_score, na.rm = TRUE))),
      tags$p(tags$b("Max content score:"), format_score(max(d$content_score, na.rm = TRUE))),
      tags$p(tags$b("Nota de robustez:"), "Si hay CSV invalidos, el pipeline los mueve a data/bronze/csv_quarantine.")
    )
  })

  output$download_dataset_csv <- downloadHandler(
    filename = function() paste0("dataset_", input$dataset, "_", input$snapshot_date, ".csv"),
    content = function(file) {
      row <- selected_dataset()
      write.csv(row, file, row.names = FALSE, na = "")
    }
  )

  output$download_filtered_csv <- downloadHandler(
    filename = function() paste0("datasets_filtrados_", input$snapshot_date, ".csv"),
    content = function(file) {
      write.csv(filtered_datasets(), file, row.names = FALSE, na = "")
    }
  )

  output$download_org_csv <- downloadHandler(
    filename = function() paste0("dependencias_", input$snapshot_date, ".csv"),
    content = function(file) {
      orgs <- data_bundle()$organizations
      if (is.null(orgs)) {
        write.csv(data.frame(mensaje = "Sin datos"), file, row.names = FALSE)
      } else {
        write.csv(orgs, file, row.names = FALSE, na = "")
      }
    }
  )

  output$download_delta_csv <- downloadHandler(
    filename = function() paste0("delta_dependencias_", input$snapshot_date, ".csv"),
    content = function(file) {
      delta <- data_bundle()$delta
      if (is.null(delta)) {
        write.csv(data.frame(mensaje = "Sin datos"), file, row.names = FALSE)
      } else {
        write.csv(delta, file, row.names = FALSE, na = "")
      }
    }
  )

  output$download_gold_json <- downloadHandler(
    filename = function() paste0("gold_report_", input$snapshot_date, ".json"),
    content = function(file) {
      report <- data_bundle()$report
      if (is.null(report)) {
        jsonlite::write_json(list(mensaje = "Sin datos"), file, pretty = TRUE, auto_unbox = TRUE)
      } else {
        jsonlite::write_json(report, file, pretty = TRUE, auto_unbox = TRUE)
      }
    }
  )

  output$download_content_csv <- downloadHandler(
    filename = function() paste0("contenido_filtrado_", input$snapshot_date, ".csv"),
    content = function(file) {
      d <- filtered_datasets() %>% select(name, title, org_title, meta_score, content_score, score_final, content_evaluated, content_files)
      write.csv(d, file, row.names = FALSE, na = "")
    }
  )

  output$download_dataset_png <- downloadHandler(
    filename = function() paste0("dataset_score_", input$dataset, "_", input$snapshot_date, ".png"),
    content = function(file) {
      row <- selected_dataset()
      grDevices::png(file, width = 1100, height = 600, res = 120)
      sc <- as.numeric(row$score_final)
      barplot(sc, horiz = TRUE, xlim = c(0, 1), col = score_badge_color(sc), border = "#111827", names.arg = "Score Final")
      title(main = paste("Dataset:", row$name))
      text(x = min(sc + 0.03, 0.95), y = 0.7, labels = format_score(sc), col = "#111827")
      grDevices::dev.off()
    }
  )

  output$download_org_png <- downloadHandler(
    filename = function() paste0("ranking_dependencias_", input$snapshot_date, ".png"),
    content = function(file) {
      orgs <- data_bundle()$organizations
      grDevices::png(file, width = 1400, height = 950, res = 120)
      if (is.null(orgs) || nrow(orgs) == 0) {
        plot.new(); text(0.5, 0.5, "Sin datos de dependencias")
      } else {
        d <- orgs %>% arrange(score_final_mean)
        par(mar = c(5, 28, 4, 2))
        barplot(
          d$score_final_mean,
          names.arg = d$org_title,
          horiz = TRUE,
          las = 1,
          xlim = c(0, 1),
          col = "#f2c94c",
          border = "#111827"
        )
        title(main = "Ranking por Dependencia - Score Final Medio")
      }
      grDevices::dev.off()
    }
  )

  output$download_delta_png <- downloadHandler(
    filename = function() paste0("delta_dependencias_", input$snapshot_date, ".png"),
    content = function(file) {
      delta <- data_bundle()$delta
      grDevices::png(file, width = 1400, height = 900, res = 120)
      if (is.null(delta) || nrow(delta) == 0) {
        plot.new(); text(0.5, 0.5, "Sin datos longitudinales")
      } else {
        d <- delta %>% arrange(delta_score_final_mean)
        cols <- ifelse(d$delta_score_final_mean > 0.02, "#2e7d32", ifelse(d$delta_score_final_mean < -0.02, "#b71c1c", "#f9a825"))
        par(mar = c(5, 28, 4, 2))
        barplot(
          d$delta_score_final_mean,
          names.arg = d$org_title,
          horiz = TRUE,
          las = 1,
          col = cols,
          border = "#111827"
        )
        abline(v = 0, lwd = 2)
        title(main = "Delta Score Final (2026 - 2024)")
      }
      grDevices::dev.off()
    }
  )

  output$download_content_png <- downloadHandler(
    filename = function() paste0("dispersion_contenido_", input$snapshot_date, ".png"),
    content = function(file) {
      d <- filtered_datasets()
      grDevices::png(file, width = 1200, height = 850, res = 120)
      if (is.null(d) || nrow(d) == 0) {
        plot.new(); text(0.5, 0.5, "Sin datos filtrados")
      } else {
        plot(
          d$meta_score,
          d$content_score,
          pch = 19,
          col = "#1f2937aa",
          xlim = c(0, 1),
          ylim = c(0, 1),
          xlab = "Meta score",
          ylab = "Content score",
          main = "Dispersion Meta vs Contenido"
        )
        abline(0, 1, lty = 2, col = "#6b7280")
      }
      grDevices::dev.off()
    }
  )

  output$download_bundle_zip <- downloadHandler(
    filename = function() paste0("dashboard_export_", input$snapshot_date, "_", format(Sys.time(), "%Y%m%d_%H%M%S"), ".zip"),
    content = function(file) {
      bundle <- data_bundle()
      dsel <- selected_dataset()
      dflt <- filtered_datasets()
      cmp <- snapshot_compare()

      out_dir <- tempfile("dashboard_export_")
      dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

      if (!is.null(bundle$datasets)) write.csv(bundle$datasets, file.path(out_dir, "datasets_snapshot.csv"), row.names = FALSE, na = "")
      if (!is.null(bundle$organizations)) write.csv(bundle$organizations, file.path(out_dir, "organizations_snapshot.csv"), row.names = FALSE, na = "")
      if (!is.null(bundle$delta)) write.csv(bundle$delta, file.path(out_dir, "delta_snapshot.csv"), row.names = FALSE, na = "")
      if (!is.null(bundle$report)) jsonlite::write_json(bundle$report, file.path(out_dir, "gold_report.json"), pretty = TRUE, auto_unbox = TRUE)

      write.csv(dsel, file.path(out_dir, "dataset_selected.csv"), row.names = FALSE, na = "")
      write.csv(dflt, file.path(out_dir, "datasets_filtered.csv"), row.names = FALSE, na = "")
      if (!is.null(cmp)) write.csv(cmp, file.path(out_dir, "snapshot_compare.csv"), row.names = FALSE, na = "")

      png_dataset <- file.path(out_dir, "dataset_score.png")
      grDevices::png(png_dataset, width = 1100, height = 600, res = 120)
      sc <- as.numeric(dsel$score_final)
      barplot(sc, horiz = TRUE, xlim = c(0, 1), col = score_badge_color(sc), border = "#111827", names.arg = "Score Final")
      title(main = paste("Dataset:", dsel$name))
      text(x = min(sc + 0.03, 0.95), y = 0.7, labels = format_score(sc), col = "#111827")
      grDevices::dev.off()

      png_org <- file.path(out_dir, "ranking_dependencias.png")
      grDevices::png(png_org, width = 1400, height = 950, res = 120)
      if (is.null(bundle$organizations) || nrow(bundle$organizations) == 0) {
        plot.new(); text(0.5, 0.5, "Sin datos de dependencias")
      } else {
        d <- bundle$organizations %>% arrange(score_final_mean)
        par(mar = c(5, 28, 4, 2))
        barplot(d$score_final_mean, names.arg = d$org_title, horiz = TRUE, las = 1, xlim = c(0, 1), col = "#f2c94c", border = "#111827")
        title(main = "Ranking por Dependencia - Score Final Medio")
      }
      grDevices::dev.off()

      png_delta <- file.path(out_dir, "delta_dependencias.png")
      grDevices::png(png_delta, width = 1400, height = 900, res = 120)
      if (is.null(bundle$delta) || nrow(bundle$delta) == 0) {
        plot.new(); text(0.5, 0.5, "Sin datos longitudinales")
      } else {
        d <- bundle$delta %>% arrange(delta_score_final_mean)
        cols <- ifelse(d$delta_score_final_mean > 0.02, "#2e7d32", ifelse(d$delta_score_final_mean < -0.02, "#b71c1c", "#f9a825"))
        par(mar = c(5, 28, 4, 2))
        barplot(d$delta_score_final_mean, names.arg = d$org_title, horiz = TRUE, las = 1, col = cols, border = "#111827")
        abline(v = 0, lwd = 2)
        title(main = "Delta Score Final")
      }
      grDevices::dev.off()

      png_content <- file.path(out_dir, "dispersion_contenido.png")
      grDevices::png(png_content, width = 1200, height = 850, res = 120)
      if (is.null(dflt) || nrow(dflt) == 0) {
        plot.new(); text(0.5, 0.5, "Sin datos filtrados")
      } else {
        plot(dflt$meta_score, dflt$content_score, pch = 19, col = "#1f2937aa", xlim = c(0, 1), ylim = c(0, 1), xlab = "Meta score", ylab = "Content score", main = "Dispersion Meta vs Contenido")
        abline(0, 1, lty = 2, col = "#6b7280")
      }
      grDevices::dev.off()

      files <- list.files(out_dir, recursive = TRUE, full.names = TRUE)
      if (length(files) == 0) {
        writeLines("No hay contenido para exportar.", file.path(out_dir, "README.txt"))
      }
      rel_files <- list.files(out_dir, recursive = TRUE, full.names = FALSE)

      zip_done <- FALSE
      old <- getwd()
      on.exit(setwd(old), add = TRUE)
      setwd(out_dir)

      tryCatch({
        utils::zip(zipfile = file, files = list.files(".", recursive = TRUE, all.files = FALSE))
        zip_done <- TRUE
      }, error = function(e) {
        zip_done <<- FALSE
      })

      if (!zip_done && requireNamespace("zip", quietly = TRUE)) {
        zip::zipr(zipfile = file, files = file.path(out_dir, rel_files), root = out_dir)
        zip_done <- TRUE
      }

      if (!zip_done) {
        stop("No se pudo generar ZIP. Instala utilitario zip del sistema o paquete R 'zip'.")
      }
    }
  )
}

shinyApp(ui = ui, server = server)
