const chartRegistry = {};

export function renderChart(key, canvasElement, config) {
  if (chartRegistry[key]) {
    chartRegistry[key].destroy();
  }
  if (canvasElement) {
    canvasElement.width = canvasElement.offsetWidth;
    canvasElement.height = canvasElement.offsetHeight;
  }
  chartRegistry[key] = new Chart(canvasElement, config);
}

export function destroyAllCharts() {
  Object.keys(chartRegistry).forEach((key) => {
    chartRegistry[key].destroy();
    delete chartRegistry[key];
  });
}
