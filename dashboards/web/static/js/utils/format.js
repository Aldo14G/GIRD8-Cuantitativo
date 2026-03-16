export function toNumber(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : Number.NaN;
}

export function score(value, digits = 3) {
  const parsed = toNumber(value);
  return Number.isFinite(parsed) ? parsed.toFixed(digits) : "NA";
}

export function percent(value, digits = 1) {
  const parsed = toNumber(value);
  return Number.isFinite(parsed) ? `${(parsed * 100).toFixed(digits)}%` : "NA";
}

export function median(values) {
  if (!values.length) {
    return Number.NaN;
  }
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  if (sorted.length % 2 !== 0) {
    return sorted[middle];
  }
  return (sorted[middle - 1] + sorted[middle]) / 2;
}

export function mean(values) {
  if (!values.length) {
    return Number.NaN;
  }
  const total = values.reduce((acc, cur) => acc + cur, 0);
  return total / values.length;
}

export function groupCounts(items, mapper) {
  const groups = {};
  items.forEach((item) => {
    const key = mapper(item) ?? "NA";
    groups[key] = (groups[key] || 0) + 1;
  });
  return groups;
}
