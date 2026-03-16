export function byId(id) {
  return document.getElementById(id);
}

export function setOptions(selectEl, values, selectedValue) {
  selectEl.innerHTML = "";
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    if (selectedValue !== undefined && value === selectedValue) {
      option.selected = true;
    }
    selectEl.appendChild(option);
  });
}

export function downloadBlob(filename, mimeType, content) {
  const blob = new Blob([content], { type: mimeType });
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(objectUrl);
}

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
