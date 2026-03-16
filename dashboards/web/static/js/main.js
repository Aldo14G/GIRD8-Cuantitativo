import { IDS } from "./config.js";
import { checkHealth, getSnapshotBundle, getSnapshots } from "./services/api.js";
import { getAlertDatasets, setBundle, setSnapshots, store, applyDatasetFilters } from "./state/store.js";
import { byId, downloadBlob, setOptions } from "./utils/dom.js";
import { mean, score, toNumber } from "./utils/format.js";
import {
  setHealthStatus,
  renderDimensionChart,
  renderExecutiveSummary,
  renderGradeChart,
  renderKpis,
  renderLongitudinal,
  renderOrganizationChart,
  renderSnapshotInfo,
  renderSources,
  renderTopAndAlerts,
} from "./ui/render.js";

const ui = {
  snapshotSelect: byId(IDS.snapshotSelect),
  orgFilter: byId(IDS.orgFilter),
  searchInput: byId(IDS.searchInput),
  scoreMin: byId(IDS.scoreMin),
  scoreMax: byId(IDS.scoreMax),
  sourceList: byId(IDS.sourceList),
  snapshotInfo: byId(IDS.snapshotInfo),
  healthInfo: byId(IDS.healthInfo),
  kpiGrid: byId(IDS.kpiGrid),
  summaryBlock: byId(IDS.summaryBlock),
  topTable: byId(IDS.topTable),
  alertTable: byId(IDS.alertTable),
  longitudinalBox: byId(IDS.longitudinalBox),
  downloadExecutive: byId(IDS.downloadExecutive),
  gradeChart: byId(IDS.gradeChart),
  dimensionChart: byId(IDS.dimensionChart),
  orgChart: byId(IDS.orgChart),
};

function currentFilters() {
  return {
    organization: ui.orgFilter.value,
    query: ui.searchInput.value,
    scoreMin: toNumber(ui.scoreMin.value),
    scoreMax: toNumber(ui.scoreMax.value),
  };
}

function updateOrganizationOptions(datasets) {
  const organizations = ["Todas", ...new Set(datasets.map((row) => row.org_title).filter(Boolean))].sort();
  setOptions(ui.orgFilter, organizations, "Todas");
}

function renderPage() {
  const filtered = applyDatasetFilters(currentFilters());
  const organizations = store.bundle?.organizations || [];
  const report = store.bundle?.report || {};
  const alerts = getAlertDatasets(8);

  renderSources(ui.sourceList, store.bundle?.paths);
  renderSnapshotInfo(ui.snapshotInfo, store.bundle?.resolved_snapshot);
  renderKpis(ui.kpiGrid, filtered);
  renderExecutiveSummary(ui.summaryBlock, filtered, report);
  renderGradeChart(ui.gradeChart, filtered);
  renderDimensionChart(ui.dimensionChart, filtered);
  renderOrganizationChart(ui.orgChart, organizations);
  renderTopAndAlerts(ui.topTable, ui.alertTable, filtered, alerts);
  renderLongitudinal(ui.longitudinalBox, report);
}

function buildExecutivePayload() {
  const filtered = store.filteredDatasets;
  const scoreValues = filtered
    .map((row) => toNumber(row.score_final))
    .filter((value) => Number.isFinite(value));
  const contentCoverage = filtered.length
    ? filtered.filter((row) => row.content_evaluated).length / filtered.length
    : null;

  return {
    snapshot: store.bundle?.resolved_snapshot,
    generated_at: new Date().toISOString(),
    kpis: {
      datasets: filtered.length,
      organizations: new Set(filtered.map((row) => row.org_title)).size,
      score_mean: Number.isFinite(mean(scoreValues)) ? Number(score(mean(scoreValues))) : null,
      content_coverage: contentCoverage,
      no_csv_count: filtered.filter((row) => !row.has_csv).length,
      low_documentation_count: filtered.filter((row) => toNumber(row.meta_documentacion) < 0.7).length,
    },
    top5: [...filtered]
      .sort((a, b) => toNumber(b.score_final) - toNumber(a.score_final))
      .slice(0, 5),
    alerts: getAlertDatasets(15),
    report: store.bundle?.report || {},
  };
}

function bindEvents() {
  ui.snapshotSelect.addEventListener("change", async () => {
    try {
      setHealthStatus(ui.healthInfo, "cargando...", "warn");
      const bundle = await getSnapshotBundle(ui.snapshotSelect.value);
      setBundle(bundle);
      updateOrganizationOptions(bundle.datasets || []);
      renderPage();
      setHealthStatus(ui.healthInfo, "ok", "ok");
    } catch (error) {
      setHealthStatus(ui.healthInfo, `error: ${error.message}`, "bad");
    }
  });

  [ui.orgFilter, ui.searchInput, ui.scoreMin, ui.scoreMax].forEach((element) => {
    element.addEventListener("input", renderPage);
    element.addEventListener("change", renderPage);
  });

  ui.downloadExecutive.addEventListener("click", () => {
    const payload = buildExecutivePayload();
    const name = `resumen_ejecutivo_${store.bundle?.resolved_snapshot || "snapshot"}.json`;
    downloadBlob(name, "application/json;charset=utf-8", JSON.stringify(payload, null, 2));
  });
}

async function bootstrap() {
  try {
    await checkHealth();
    setHealthStatus(ui.healthInfo, "ok", "ok");

    const snapshotPayload = await getSnapshots();
    const snapshots = snapshotPayload.snapshots || [];
    const snapshotDates = snapshots.map((row) => row.snapshot_date);
    const activeSnapshot = snapshotPayload.default_snapshot || snapshotDates[0] || "latest";

    setSnapshots(snapshots, activeSnapshot);
    setOptions(ui.snapshotSelect, snapshotDates.length ? snapshotDates : ["latest"], activeSnapshot);

    setHealthStatus(ui.healthInfo, "cargando datos...", "warn");
    const bundle = await getSnapshotBundle(activeSnapshot);
    setBundle(bundle);
    updateOrganizationOptions(bundle.datasets || []);
    bindEvents();
    renderPage();
    setHealthStatus(ui.healthInfo, "ok", "ok");
  } catch (error) {
    setHealthStatus(ui.healthInfo, `error: ${error.message}`, "bad");
  }
}

bootstrap();
