const state = {
  snapshots: [],
  data: null,
  filteredDatasets: [],
  compareRows: [],
  charts: {},
};

const els = {
  status: document.getElementById("serverStatus"),
  snapshotSelect: document.getElementById("snapshotSelect"),
  snapshotA: document.getElementById("snapshotA"),
  snapshotB: document.getElementById("snapshotB"),
  orgFilter: document.getElementById("orgFilter"),
  scoreMin: document.getElementById("scoreMin"),
  scoreMax: document.getElementById("scoreMax"),
  datasetSelect: document.getElementById("datasetSelect"),
  sourceList: document.getElementById("sourceList"),
  kpiGrid: document.getElementById("kpiGrid"),
  datasetSummary: document.getElementById("datasetSummary"),
  datasetMetricsTable: document.getElementById("datasetMetricsTable"),
  compareTable: document.getElementById("compareTable"),
  contentNotes: document.getElementById("contentNotes"),
  downloadDatasetCsv: document.getElementById("downloadDatasetCsv"),
  downloadDatasetJson: document.getElementById("downloadDatasetJson"),
  downloadOrgsCsv: document.getElementById("downloadOrgsCsv"),
  downloadDeltaCsv: document.getElementById("downloadDeltaCsv"),
  downloadGoldJson: document.getElementById("downloadGoldJson"),
  downloadFilteredCsv: document.getElementById("downloadFilteredCsv"),
};

function setStatus(text, ok = true) {
  els.status.textContent = text;
  els.status.style.borderColor = ok ? "#cce3ff" : "#f3b1ac";
  els.status.style.color = ok ? "#0f62fe" : "#b42318";
}

function toNumber(value) {
  if (value === null || value === undefined || value === "") return NaN;
  const n = Number(value);
  return Number.isFinite(n) ? n : NaN;
}

function score(value, digits = 3) {
  const n = toNumber(value);
  return Number.isFinite(n) ? n.toFixed(digits) : "NA";
}

function pct(value, digits = 1) {
  const n = toNumber(value);
  return Number.isFinite(n) ? `${(n * 100).toFixed(digits)}%` : "NA";
}

function htmlEscape(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} on ${url}`);
  }
  return response.json();
}

function setOptions(selectEl, values, selected) {
  selectEl.innerHTML = "";
  values.forEach((val) => {
    const option = document.createElement("option");
    option.value = val;
    option.textContent = val;
    if (selected !== undefined && val === selected) option.selected = true;
    selectEl.appendChild(option);
  });
}

function destroyChart(name) {
  if (state.charts[name]) {
    state.charts[name].destroy();
    delete state.charts[name];
  }
}

function chart(name, canvasId, config) {
  destroyChart(name);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  state.charts[name] = new Chart(ctx, config);
}

function recordsToCsv(records) {
  if (!records || records.length === 0) return "mensaje\nSin datos\n";
  const keys = Array.from(
    records.reduce((acc, row) => {
      Object.keys(row).forEach((k) => acc.add(k));
      return acc;
    }, new Set())
  );

  const rows = [keys.join(",")];
  for (const row of records) {
    const cells = keys.map((k) => {
      let val = row[k];
      if (Array.isArray(val)) val = JSON.stringify(val);
      if (val === null || val === undefined) val = "";
      const text = String(val).replaceAll('"', '""');
      return /[",\n]/.test(text) ? `"${text}"` : text;
    });
    rows.push(cells.join(","));
  }
  return rows.join("\n");
}

function downloadText(filename, text, mime = "text/plain;charset=utf-8") {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function currentDataset() {
  const name = els.datasetSelect.value;
  return state.filteredDatasets.find((row) => row.name === name) ?? null;
}

function applyFilters() {
  const datasets = state.data?.datasets ?? [];
  const org = els.orgFilter.value;
  const min = toNumber(els.scoreMin.value);
  const max = toNumber(els.scoreMax.value);

  state.filteredDatasets = datasets.filter((row) => {
    const s = toNumber(row.score_final);
    const inScore = (!Number.isFinite(min) || s >= min) && (!Number.isFinite(max) || s <= max);
    const inOrg = org === "Todas" || row.org_title === org;
    return inScore && inOrg;
  });

  const datasetNames = state.filteredDatasets.map((row) => row.name);
  setOptions(els.datasetSelect, datasetNames, datasetNames[0]);
}

function renderSources() {
  const paths = state.data?.paths ?? {};
  const items = [
    ["datasets", paths.datasets],
    ["organizations", paths.organizations],
    ["delta", paths.delta],
    ["report", paths.report],
  ];
  els.sourceList.innerHTML = items
    .map(([k, v]) => `<li><strong>${htmlEscape(k)}:</strong> ${htmlEscape(v ?? "No disponible")}</li>`)
    .join("");
}

function renderKpis() {
  const datasets = state.filteredDatasets;
  const orgCount = new Set(datasets.map((r) => r.org_title)).size;
  const avgScore = datasets.length
    ? datasets.reduce((acc, row) => acc + (toNumber(row.score_final) || 0), 0) / datasets.length
    : NaN;
  const cov = datasets.length
    ? datasets.reduce((acc, row) => acc + (row.content_evaluated ? 1 : 0), 0) / datasets.length
    : NaN;

  const cards = [
    ["Datasets visibles", datasets.length],
    ["Dependencias", orgCount],
    ["Score final promedio", score(avgScore)],
    ["Cobertura CSV", pct(cov)],
  ];

  els.kpiGrid.innerHTML = cards
    .map(
      ([label, value]) =>
        `<article class="kpi"><span class="label">${htmlEscape(label)}</span><span class="value">${htmlEscape(
          value
        )}</span></article>`
    )
    .join("");
}

function renderDatasetSummary() {
  const row = currentDataset();
  if (!row) {
    els.datasetSummary.innerHTML = `<p class="note">No hay dataset disponible para los filtros actuales.</p>`;
    return;
  }

  els.datasetSummary.innerHTML = `
    <p><strong>Titulo:</strong> ${htmlEscape(row.title)}</p>
    <p><strong>Dependencia:</strong> ${htmlEscape(row.org_title)}</p>
    <p><strong>Score final:</strong> ${score(row.score_final)} (${htmlEscape(row.grade)})</p>
    <p><strong>Meta score:</strong> ${score(row.meta_score)}</p>
    <p><strong>Content score:</strong> ${score(row.content_score)}</p>
    <p><strong>Recursos:</strong> ${htmlEscape(row.num_resources)}</p>
    <p><strong>Con CSV:</strong> ${row.has_csv ? "Si" : "No"}</p>
    <p><strong>Ultima modificacion:</strong> ${htmlEscape(row.metadata_modified)}</p>
  `;
}

function renderDatasetMetrics() {
  const row = currentDataset();
  if (!row) {
    els.datasetMetricsTable.innerHTML = "";
    return;
  }

  const records = [
    ["Meta score", score(row.meta_score)],
    ["Content score", score(row.content_score)],
    ["Layers evaluated", row.layers_evaluated ?? "NA"],
    ["CSV files evaluados", row.content_files ?? "NA"],
    ["CSV total KB", score(row.csv_total_kb, 2)],
    ["Tags", row.num_tags ?? "NA"],
    ["Grupos", row.num_groups ?? "NA"],
  ];

  els.datasetMetricsTable.innerHTML = `
    <thead><tr><th>Metrica</th><th>Valor</th></tr></thead>
    <tbody>
      ${records.map(([k, v]) => `<tr><td>${htmlEscape(k)}</td><td>${htmlEscape(v)}</td></tr>`).join("")}
    </tbody>
  `;
}

function renderDatasetCharts() {
  const row = currentDataset();
  if (!row) {
    destroyChart("datasetScore");
    destroyChart("datasetRadar");
    return;
  }

  const sc = toNumber(row.score_final);
  chart("datasetScore", "datasetScoreChart", {
    type: "bar",
    data: {
      labels: ["Score final"],
      datasets: [{
        data: [sc],
        backgroundColor: sc >= 0.8 ? "#1f7a1f" : sc >= 0.65 ? "#a36100" : "#b42318",
      }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { min: 0, max: 1 },
      },
      plugins: { legend: { display: false } },
    },
  });

  chart("datasetRadar", "datasetRadarChart", {
    type: "radar",
    data: {
      labels: ["Completitud", "Actualizacion", "Accesibilidad", "Documentacion", "Apertura"],
      datasets: [{
        label: row.name,
        data: [
          toNumber(row.meta_completitud),
          toNumber(row.meta_actualizacion),
          toNumber(row.meta_accesibilidad),
          toNumber(row.meta_documentacion),
          toNumber(row.meta_apertura),
        ],
        fill: true,
        borderColor: "#0f62fe",
        backgroundColor: "rgba(15, 98, 254, 0.18)",
        pointBackgroundColor: "#0f62fe",
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { r: { min: 0, max: 1 } },
      plugins: { legend: { display: false } },
    },
  });
}

function renderOrgCharts() {
  const orgs = state.data?.organizations ?? [];
  if (!orgs.length) {
    destroyChart("orgRanking");
    destroyChart("orgGrade");
    destroyChart("orgCoverage");
    return;
  }

  const sorted = [...orgs].sort((a, b) => toNumber(a.score_final_mean) - toNumber(b.score_final_mean));
  chart("orgRanking", "orgRankingChart", {
    type: "bar",
    data: {
      labels: sorted.map((r) => r.org_title),
      datasets: [{
        data: sorted.map((r) => toNumber(r.score_final_mean)),
        backgroundColor: "#0f62fe",
      }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      scales: { x: { min: 0, max: 1 } },
      plugins: { legend: { display: false } },
    },
  });

  const grades = {};
  orgs.forEach((r) => {
    const g = r.org_grade || "NA";
    grades[g] = (grades[g] || 0) + 1;
  });
  chart("orgGrade", "orgGradeChart", {
    type: "bar",
    data: {
      labels: Object.keys(grades),
      datasets: [{ data: Object.values(grades), backgroundColor: "#1f2937" }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
    },
  });

  chart("orgCoverage", "orgCoverageChart", {
    type: "bar",
    data: {
      labels: sorted.map((r) => r.org_title),
      datasets: [{ data: sorted.map((r) => toNumber(r.pct_with_csv)), backgroundColor: "#6b7280" }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      scales: { x: { min: 0, max: 1 } },
      plugins: { legend: { display: false } },
    },
  });
}

function deltaColor(value) {
  if (value > 0.02) return "#1f7a1f";
  if (value < -0.02) return "#b42318";
  return "#a36100";
}

function renderDeltaChart() {
  const rows = state.data?.delta ?? [];
  if (!rows.length) {
    destroyChart("delta");
    return;
  }

  const sorted = [...rows].sort((a, b) => toNumber(a.delta_score_final_mean) - toNumber(b.delta_score_final_mean));
  const deltas = sorted.map((r) => toNumber(r.delta_score_final_mean));
  chart("delta", "deltaChart", {
    type: "bar",
    data: {
      labels: sorted.map((r) => r.org_title),
      datasets: [{
        data: deltas,
        backgroundColor: deltas.map(deltaColor),
      }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { beginAtZero: false } },
    },
  });
}

function renderCompareTable() {
  const rows = state.compareRows;
  if (!rows.length) {
    els.compareTable.innerHTML = "<tbody><tr><td>No hay comparacion disponible.</td></tr></tbody>";
    return;
  }

  const topUp = [...rows].sort((a, b) => b.delta_b_minus_a - a.delta_b_minus_a).slice(0, 3);
  const topDown = [...rows].sort((a, b) => a.delta_b_minus_a - b.delta_b_minus_a).slice(0, 3);
  const merged = [
    ...topUp.map((r) => ({ tipo: "Mejora", ...r })),
    ...topDown.map((r) => ({ tipo: "Deterioro", ...r })),
  ];

  els.compareTable.innerHTML = `
    <thead><tr><th>Tipo</th><th>Dependencia</th><th>Delta</th></tr></thead>
    <tbody>
      ${merged
        .map(
          (r) =>
            `<tr><td>${htmlEscape(r.tipo)}</td><td>${htmlEscape(r.org_title)}</td><td>${score(
              r.delta_b_minus_a,
              4
            )}</td></tr>`
        )
        .join("")}
    </tbody>
  `;
}

async function renderCompareChart() {
  const a = els.snapshotA.value;
  const b = els.snapshotB.value;
  if (!a || !b) {
    destroyChart("compare");
    state.compareRows = [];
    renderCompareTable();
    return;
  }

  try {
    const payload = await fetchJson(`/api/compare?snapshot_a=${encodeURIComponent(a)}&snapshot_b=${encodeURIComponent(b)}`);
    const rows = payload.rows || [];
    state.compareRows = rows;

    if (!rows.length) {
      destroyChart("compare");
      renderCompareTable();
      return;
    }

    const sorted = [...rows].sort((x, y) => x.delta_b_minus_a - y.delta_b_minus_a);
    const deltas = sorted.map((r) => toNumber(r.delta_b_minus_a));
    chart("compare", "compareChart", {
      type: "bar",
      data: {
        labels: sorted.map((r) => r.org_title),
        datasets: [{ data: deltas, backgroundColor: deltas.map(deltaColor) }],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          title: { display: true, text: `Delta ${b} - ${a}` },
        },
      },
    });
    renderCompareTable();
  } catch (err) {
    destroyChart("compare");
    state.compareRows = [];
    renderCompareTable();
  }
}

function renderContentChart() {
  const d = state.filteredDatasets;
  if (!d.length) {
    destroyChart("content");
    return;
  }

  const points = d
    .map((row) => ({
      x: toNumber(row.meta_score),
      y: toNumber(row.content_score),
    }))
    .filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y));

  chart("content", "contentScatter", {
    type: "scatter",
    data: {
      datasets: [{
        data: points,
        pointBackgroundColor: "rgba(15, 98, 254, 0.6)",
        pointRadius: 5,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { min: 0, max: 1, title: { display: true, text: "Meta score" } },
        y: { min: 0, max: 1, title: { display: true, text: "Content score" } },
      },
    },
  });

  const contentValues = d.map((r) => toNumber(r.content_score)).filter((v) => Number.isFinite(v));
  const avg = contentValues.length ? contentValues.reduce((a, b) => a + b, 0) / contentValues.length : NaN;
  const min = contentValues.length ? Math.min(...contentValues) : NaN;
  const max = contentValues.length ? Math.max(...contentValues) : NaN;
  const evaluated = d.filter((r) => r.content_evaluated).length;

  els.contentNotes.innerHTML = `
    <p><strong>Datasets con contenido evaluado:</strong> ${evaluated} de ${d.length}</p>
    <p><strong>Promedio content score:</strong> ${score(avg)}</p>
    <p><strong>Min content score:</strong> ${score(min)}</p>
    <p><strong>Max content score:</strong> ${score(max)}</p>
    <p class="note">Los CSV invalidos son aislados en data/bronze/csv_quarantine por el pipeline.</p>
  `;
}

function renderAll() {
  applyFilters();
  renderSources();
  renderKpis();
  renderDatasetSummary();
  renderDatasetMetrics();
  renderDatasetCharts();
  renderOrgCharts();
  renderDeltaChart();
  renderContentChart();
  renderCompareChart();
}

async function loadSnapshot(snapshot) {
  setStatus("Cargando datos...", true);
  try {
    state.data = await fetchJson(`/api/data?snapshot=${encodeURIComponent(snapshot)}`);

    const datasets = state.data.datasets || [];
    const orgs = ["Todas", ...new Set(datasets.map((r) => r.org_title).filter(Boolean))].sort();
    setOptions(els.orgFilter, orgs, orgs[0]);

    const names = datasets.map((r) => r.name);
    setOptions(els.datasetSelect, names, names[0]);

    setStatus(`Snapshot ${state.data.resolved_snapshot || "N/A"} cargado`, true);
    renderAll();
  } catch (error) {
    setStatus(`Error al cargar: ${error.message}`, false);
  }
}

async function loadSnapshots() {
  const payload = await fetchJson("/api/snapshots");
  state.snapshots = payload.snapshots || [];
  const dates = state.snapshots.map((r) => r.snapshot_date);

  if (!dates.length) {
    setOptions(els.snapshotSelect, ["latest"], "latest");
    setOptions(els.snapshotA, ["latest"], "latest");
    setOptions(els.snapshotB, ["latest"], "latest");
    return "latest";
  }

  const defaultDate = payload.default_snapshot || dates[0];
  setOptions(els.snapshotSelect, dates, defaultDate);
  setOptions(els.snapshotA, dates, dates[0]);
  setOptions(els.snapshotB, dates, dates[Math.min(1, dates.length - 1)]);
  return defaultDate;
}

function bindEvents() {
  els.snapshotSelect.addEventListener("change", () => loadSnapshot(els.snapshotSelect.value));
  els.snapshotA.addEventListener("change", renderCompareChart);
  els.snapshotB.addEventListener("change", renderCompareChart);

  [els.orgFilter, els.scoreMin, els.scoreMax].forEach((el) => {
    el.addEventListener("change", renderAll);
  });

  els.datasetSelect.addEventListener("change", () => {
    renderDatasetSummary();
    renderDatasetMetrics();
    renderDatasetCharts();
  });

  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));

      button.classList.add("active");
      document.getElementById(`tab-${button.dataset.tab}`).classList.add("active");
    });
  });

  els.downloadDatasetCsv.addEventListener("click", () => {
    const row = currentDataset();
    if (!row) return;
    downloadText(`dataset_${row.name}.csv`, recordsToCsv([row]), "text/csv;charset=utf-8");
  });

  els.downloadDatasetJson.addEventListener("click", () => {
    const row = currentDataset();
    if (!row) return;
    downloadText(`dataset_${row.name}.json`, JSON.stringify(row, null, 2), "application/json;charset=utf-8");
  });

  els.downloadOrgsCsv.addEventListener("click", () => {
    downloadText("dependencias.csv", recordsToCsv(state.data?.organizations || []), "text/csv;charset=utf-8");
  });

  els.downloadDeltaCsv.addEventListener("click", () => {
    downloadText("delta_dependencias.csv", recordsToCsv(state.data?.delta || []), "text/csv;charset=utf-8");
  });

  els.downloadGoldJson.addEventListener("click", () => {
    downloadText(
      "gold_report.json",
      JSON.stringify(state.data?.report || { mensaje: "No disponible" }, null, 2),
      "application/json;charset=utf-8"
    );
  });

  els.downloadFilteredCsv.addEventListener("click", () => {
    downloadText("datasets_filtrados.csv", recordsToCsv(state.filteredDatasets), "text/csv;charset=utf-8");
  });
}

async function bootstrap() {
  try {
    const health = await fetchJson("/api/health");
    if (!health.ok) throw new Error("health endpoint not ok");

    const defaultSnapshot = await loadSnapshots();
    bindEvents();
    await loadSnapshot(defaultSnapshot);
  } catch (error) {
    setStatus(`No se pudo iniciar: ${error.message}`, false);
  }
}

bootstrap();
