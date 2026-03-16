library(shiny)
library(shinydashboard)

dataset_tab_ui <- tabItem(
  tabName = "dataset",
  fluidRow(
    box(
      width = 12,
      title = "Exportar Dataset",
      status = "warning",
      solidHeader = TRUE,
      downloadButton("download_dataset_csv", "CSV dataset seleccionado"),
      downloadButton("download_dataset_png", "PNG score dataset"),
      downloadButton("download_filtered_csv", "CSV datasets filtrados")
    )
  ),
  fluidRow(
    box(width = 4, title = "Resumen Dataset", status = "warning", solidHeader = TRUE,
        htmlOutput("dataset_summary")),
    box(width = 8, title = "Puntaje Final", status = "warning", solidHeader = TRUE,
        plotlyOutput("dataset_score_bar", height = "210px"))
  ),
  fluidRow(
    box(width = 6, title = "Radar de Metadata (5 dimensiones)", status = "warning", solidHeader = TRUE,
        plotlyOutput("dataset_radar", height = "360px")),
    box(width = 6, title = "Detalle Tecnico", status = "warning", solidHeader = TRUE,
        tableOutput("dataset_metrics_table"))
  )
)

org_tab_ui <- tabItem(
  tabName = "dependencias",
  fluidRow(
    box(
      width = 12,
      title = "Exportar Dependencias",
      status = "warning",
      solidHeader = TRUE,
      downloadButton("download_org_csv", "CSV ranking dependencias"),
      downloadButton("download_org_png", "PNG ranking dependencias")
    )
  ),
  fluidRow(
    box(width = 12, title = "Ranking por Dependencia", status = "warning", solidHeader = TRUE,
        plotlyOutput("org_ranking", height = "430px"))
  ),
  fluidRow(
    box(width = 6, title = "Distribucion de Grados", status = "warning", solidHeader = TRUE,
        plotlyOutput("org_grade_dist", height = "280px")),
    box(width = 6, title = "Cobertura CSV por Dependencia", status = "warning", solidHeader = TRUE,
        plotlyOutput("org_csv_coverage", height = "280px"))
  )
)

longitudinal_tab_ui <- tabItem(
  tabName = "longitudinal",
  fluidRow(
    box(
      width = 12,
      title = "Exportar Longitudinal",
      status = "warning",
      solidHeader = TRUE,
      downloadButton("download_delta_csv", "CSV deltas"),
      downloadButton("download_delta_png", "PNG deltas"),
      downloadButton("download_gold_json", "JSON reporte Gold"),
      downloadButton("download_bundle_zip", "ZIP exportacion completa")
    )
  ),
  fluidRow(
    box(width = 12, title = "Cambio 2024 -> 2026 por Dependencia", status = "warning", solidHeader = TRUE,
        plotlyOutput("delta_chart", height = "420px"))
  ),
  fluidRow(
    box(width = 8, title = "Comparacion Snapshot A/B", status = "warning", solidHeader = TRUE,
        plotlyOutput("snapshot_compare_chart", height = "360px")),
    box(width = 4, title = "Resumen Comparacion", status = "warning", solidHeader = TRUE,
        tableOutput("snapshot_compare_table"))
  ),
  fluidRow(
    box(width = 7, title = "Tabla de Deltas", status = "warning", solidHeader = TRUE,
        tableOutput("delta_table")),
    box(width = 5, title = "Hallazgos Gold", status = "warning", solidHeader = TRUE,
        htmlOutput("gold_highlights"))
  )
)

content_tab_ui <- tabItem(
  tabName = "contenido",
  fluidRow(
    box(
      width = 12,
      title = "Exportar Contenido",
      status = "warning",
      solidHeader = TRUE,
      downloadButton("download_content_csv", "CSV contenido filtrado"),
      downloadButton("download_content_png", "PNG dispersion contenido")
    )
  ),
  fluidRow(
    box(width = 12, title = "Calidad de Contenido (CSV)", status = "warning", solidHeader = TRUE,
        plotlyOutput("content_scatter", height = "420px"))
  ),
  fluidRow(
    box(width = 12, title = "Observaciones", status = "warning", solidHeader = TRUE,
        htmlOutput("content_notes"))
  )
)
