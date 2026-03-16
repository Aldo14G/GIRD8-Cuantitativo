import { API } from "../config.js";

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} - ${url}`);
  }
  return response.json();
}

export async function checkHealth() {
  return fetchJson(API.health);
}

export async function getSnapshots() {
  return fetchJson(API.snapshots);
}

export async function getSnapshotBundle(snapshotDate) {
  const url = `${API.data}?snapshot=${encodeURIComponent(snapshotDate)}`;
  return fetchJson(url);
}
