import { SCORE_THRESHOLD } from "../config.js";
import { toNumber } from "../utils/format.js";

export const store = {
  snapshots: [],
  activeSnapshot: null,
  bundle: null,
  filteredDatasets: [],
};

export function setSnapshots(rows, activeSnapshot) {
  store.snapshots = rows;
  store.activeSnapshot = activeSnapshot;
}

export function setBundle(bundle) {
  store.bundle = bundle;
}

export function applyDatasetFilters({ organization, query, scoreMin, scoreMax }) {
  const datasets = store.bundle?.datasets || [];
  const normalizedQuery = query.trim().toLowerCase();

  store.filteredDatasets = datasets.filter((row) => {
    const currentScore = toNumber(row.score_final);
    const scorePass =
      (!Number.isFinite(scoreMin) || currentScore >= scoreMin) &&
      (!Number.isFinite(scoreMax) || currentScore <= scoreMax);
    const orgPass = organization === "Todas" || row.org_title === organization;
    const searchable = `${row.name || ""} ${row.title || ""}`.toLowerCase();
    const searchPass = !normalizedQuery || searchable.includes(normalizedQuery);
    return scorePass && orgPass && searchPass;
  });

  return store.filteredDatasets;
}

export function getAlertDatasets(limit = 8) {
  const rows = store.filteredDatasets;
  return [...rows]
    .filter(
      (row) =>
        toNumber(row.score_final) < SCORE_THRESHOLD.warning ||
        !row.has_csv ||
        toNumber(row.meta_documentacion) < SCORE_THRESHOLD.severeDocumentation
    )
    .sort((a, b) => toNumber(a.score_final) - toNumber(b.score_final))
    .slice(0, limit);
}
