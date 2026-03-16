import { SCORE_THRESHOLD } from "../config.js";
import { renderChart } from "../charts/manager.js";
import { escapeHtml } from "../utils/dom.js";
import { groupCounts, mean, median, percent, score, toNumber } from "../utils/format.js";

const METADATA_DIMENSIONS = [
  ["Completitud", "meta_completitud"],
  ["Actualizacion", "meta_actualizacion"],
  ["Accesibilidad", "meta_accesibilidad"],
  ["Documentacion", "meta_documentacion"],
  ["Apertura", "meta_apertura"],
];

export function setHealthStatus(element, text, stateClass = "") {
  element.textContent = `Estado: ${text}`;
  element.className = stateClass;
}

export function renderSnapshotInfo(element, snapshot) {
  element.textContent = `Snapshot: ${snapshot || "NA"}`;
}

export function renderSources(sourceListElement, paths) {
  const entries = [
    ["datasets", paths?.datasets],
    ["organizations", paths?.organizations],
    ["delta", paths?.delta],
    ["report", paths?.report],
  ];

  sourceListElement.innerHTML = entries
    .map(([label, value]) => `<li><strong>${escapeHtml(label)}:</strong> ${escapeHtml(value || "No disponible")}</li>`)
    .join("");
}

export function renderKpis(containerElement, datasets) {
  const scores = datasets.map((row) => toNumber(row.score_final)).filter((value) => Number.isFinite(value));
  const organizations = new Set(datasets.map((row) => row.org_title).filter(Boolean));
  const csvCoverage = datasets.length
    ? datasets.filter((row) => row.content_evaluated).length / datasets.length
    : Number.NaN;
  const lowDocumentation = datasets.filter(
    (row) => toNumber(row.meta_documentacion) < SCORE_THRESHOLD.lowDocumentation
  ).length;

  const cards = [
    ["Datasets", datasets.length],
    ["Dependencias", organizations.size],
    ["Score promedio", score(mean(scores))],
    ["Score mediana", score(median(scores))],
    ["Cobertura CSV", percent(csvCoverage)],
    ["Doc. baja (<0.70)", lowDocumentation],
  ];

  containerElement.innerHTML = cards
    .map(
      ([label, value]) =>
        `<article class="kpi-card"><span class="kpi-label">${escapeHtml(label)}</span><span class="kpi-value">${escapeHtml(
          value
        )}</span></article>`
    )
    .join("");
}

function getOperationalStatus(averageScore, coverage) {
  if (!Number.isFinite(averageScore) || !Number.isFinite(coverage)) {
    return ["Sin datos suficientes", "warn"];
  }
  if (averageScore >= 0.9 && coverage >= 0.95) {
    return ["Alto control de calidad", "ok"];
  }
  if (averageScore >= 0.85 && coverage >= 0.9) {
    return ["Calidad estable", "ok"];
  }
  if (averageScore >= 0.75) {
    return ["Atencion operativa", "warn"];
  }
  return ["Riesgo alto", "bad"];
}

export function renderExecutiveSummary(containerElement, datasets, report) {
  const scores = datasets.map((row) => toNumber(row.score_final)).filter((value) => Number.isFinite(value));
  const averageScore = mean(scores);
  const contentCoverage = datasets.length
    ? datasets.filter((row) => row.content_evaluated).length / datasets.length
    : Number.NaN;
  const noCsvCount = datasets.filter((row) => !row.has_csv).length;
  const standardsCount = datasets.filter((row) => row.standards_evaluated).length;
  const [status, statusClass] = getOperationalStatus(averageScore, contentCoverage);
  const findings = report?.hallazgos || {};

  containerElement.innerHTML = `
    <h2>Lectura ejecutiva</h2>
    <p>
      El snapshot activo registra calidad global de <strong>${score(averageScore)}</strong>
      y cobertura de contenido de <strong>${percent(contentCoverage)}</strong>.
      Estado operacional: <strong class="${statusClass}">${escapeHtml(status)}</strong>.
    </p>
    <p>
      Datasets sin CSV: <strong>${noCsvCount}</strong>.
      Datasets con estandares evaluados: <strong>${standardsCount}</strong>.
    </p>
    <div>
      <span class="pill">Delta promedio (Gold): ${score(findings.delta_promedio, 4)}</span>
      <span class="pill">Dependencias panel t0-t1: ${escapeHtml(findings.dependencias_analizadas ?? "NA")}</span>
      <span class="pill">Clasificacion dominante: ${escapeHtml(
        findings.clasificacion ? Object.keys(findings.clasificacion)[0] : "NA"
      )}</span>
    </div>
  `;
}

export function renderGradeChart(canvasElement, datasets) {
  const gradeCounts = groupCounts(datasets, (row) => row.grade || "NA");
  renderChart("grade-distribution", canvasElement, {
    type: "doughnut",
    data: {
      labels: Object.keys(gradeCounts),
      datasets: [
        {
          data: Object.values(gradeCounts),
          backgroundColor: ["#1f7a1f", "#2e90fa", "#a36100", "#b42318", "#98a2b3"],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "bottom" } },
    },
  });
}

export function renderDimensionChart(canvasElement, datasets) {
  const dimensionMeans = METADATA_DIMENSIONS.map(([, key]) => {
    const values = datasets.map((row) => toNumber(row[key])).filter((value) => Number.isFinite(value));
    const avg = mean(values);
    if (!Number.isFinite(avg)) {
      return 0;
    }
    return Math.max(0, Math.min(1, avg));
  });

  renderChart("dimension-means", canvasElement, {
    type: "bar",
    data: {
      labels: METADATA_DIMENSIONS.map(([label]) => label),
      datasets: [{
        data: dimensionMeans,
        backgroundColor: "#1a73e8",
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          min: 0,
          max: 1,
          ticks: { stepSize: 0.2 },
        },
      },
      plugins: { legend: { display: false } },
    },
  });
}

export function renderOrganizationChart(canvasElement, organizations) {
  const top = [...organizations]
    .sort((a, b) => toNumber(b.score_final_mean) - toNumber(a.score_final_mean))
    .slice(0, 10);

  renderChart("organization-ranking", canvasElement, {
    type: "bar",
    data: {
      labels: top.map((row) => row.org_title),
      datasets: [{
        data: top.map((row) => toNumber(row.score_final_mean)),
        backgroundColor: "#1a73e8",
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
}

function renderTable(tableElement, headers, rows) {
  const headerHtml = `<thead><tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr></thead>`;
  const bodyHtml = `<tbody>${rows
    .map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`)
    .join("")}</tbody>`;
  tableElement.innerHTML = headerHtml + bodyHtml;
}

export function renderTopAndAlerts(topTableElement, alertTableElement, datasets, alertRows) {
  const topRows = [...datasets]
    .sort((a, b) => toNumber(b.score_final) - toNumber(a.score_final))
    .slice(0, 5)
    .map((row) => [row.name, row.org_title, score(row.score_final)]);

  const alertData = alertRows.map((row) => {
    let risk = "Bajo score";
    if (!row.has_csv) {
      risk = "Sin CSV";
    } else if (toNumber(row.meta_documentacion) < SCORE_THRESHOLD.severeDocumentation) {
      risk = "Documentacion baja";
    }
    return [row.name, risk, score(row.score_final)];
  });

  renderTable(topTableElement, ["Dataset", "Dependencia", "Score"], topRows);
  renderTable(alertTableElement, ["Dataset", "Riesgo", "Score"], alertData);
}

export function renderLongitudinal(containerElement, report) {
  const findings = report?.hallazgos || {};
  const topImprovement = findings.top_mejora || [];
  const topDeterioration = findings.top_deterioro || [];

  containerElement.innerHTML = `
    <h2>Hallazgos longitudinales 2024-2026</h2>
    <p>
      Dependencias analizadas: <strong>${escapeHtml(findings.dependencias_analizadas ?? "NA")}</strong>.
      Delta promedio: <strong>${score(findings.delta_promedio, 4)}</strong>.
      Delta mediana: <strong>${score(findings.delta_mediana, 4)}</strong>.
    </p>
    <div class="grid-two" style="margin-top: 0.5rem;">
      <div>
        <h3 style="margin: 0 0 0.4rem;">Top mejora</h3>
        <ul>
          ${topImprovement
            .map((row) => `<li>${escapeHtml(row.org_title)}: ${score(row.delta_score_final_mean, 4)}</li>`)
            .join("")}
        </ul>
      </div>
      <div>
        <h3 style="margin: 0 0 0.4rem;">Top deterioro</h3>
        <ul>
          ${topDeterioration
            .map((row) => `<li>${escapeHtml(row.org_title)}: ${score(row.delta_score_final_mean, 4)}</li>`)
            .join("")}
        </ul>
      </div>
    </div>
  `;
}
