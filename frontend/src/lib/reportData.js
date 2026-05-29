/** Map LifeChanger aggregates into enterprise report shapes. */

function formatPct(value, baseline = 0) {
  if (baseline === 0) return value >= 0 ? "+0%" : "0%";
  const pct = ((value - baseline) / Math.abs(baseline)) * 100;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}

function growthStatus(value, peers = []) {
  if (!peers.length) return "flat";
  const avg = peers.reduce((s, p) => s + p, 0) / peers.length;
  if (value > avg * 1.05) return "up";
  if (value < avg * 0.95) return "down";
  return "flat";
}

export function buildExecutiveNarrative({ aggregates, filters, fields }) {
  const regions = aggregates?.byRegion || [];
  const top = regions[0];
  const bottom = regions[regions.length - 1];
  const outcome = aggregates?.outcome;
  const rowCount = aggregates?.rowCount || 0;
  const filterBits = Object.entries(filters || {})
    .filter(([, v]) => v && v !== "All")
    .map(([k, v]) => `${k}: ${v}`);

  const headline =
    rowCount > 0
      ? `Across ${rowCount.toLocaleString()} workshop responses${
          filterBits.length ? ` (${filterBits.join(", ")})` : ""
        }, ${top?.name || "the leading region"} leads on average outcome score${
          outcome?.hasValidData
            ? ` at ${Number(top?.value ?? aggregates.avgImprovement).toFixed(2)}`
            : ""
        }.`
      : "Apply filters to populate the strategic review from the LifeChanger dataset.";

  const caution =
    regions.length > 1 && bottom
      ? `${bottom.name} trails peer regions; consider targeted facilitator follow-up and renewed engagement in Q4 planning.`
      : "Regional comparisons will appear once the CSV exposes a region field with multiple values.";

  return { headline, caution, top, bottom };
}

export function buildInsightKpis(aggregates) {
  const regions = aggregates?.byRegion || [];
  const values = regions.map((r) => r.value);
  const top = regions[0];
  const bottom = regions[regions.length - 1];
  const mid = regions[Math.floor(regions.length / 2)];

  const kpis = [];
  if (top) {
    kpis.push({
      label: `${top.name} — Leading`,
      value: `${Number(top.value).toFixed(2)} avg`,
      subtext: "Strongest regional outcome signal",
      status: "positive",
    });
  }
  if (mid && mid !== top) {
    kpis.push({
      label: `${mid.name} — Mid-tier`,
      value: `${Number(mid.value).toFixed(2)} avg`,
      subtext: "Monitor for drift vs. leaders",
      status: "warning",
    });
  }
  if (bottom && bottom !== top) {
    kpis.push({
      label: `${bottom.name} — Lagging`,
      value: `${Number(bottom.value).toFixed(2)} avg`,
      subtext: "Intervention recommended",
      status: "negative",
    });
  }
  if (!kpis.length) {
    kpis.push(
      {
        label: "Responses analysed",
        value: String(aggregates?.rowCount || 0),
        subtext: "Filtered CSV rows",
        status: "positive",
      },
      {
        label: "Feedback captured",
        value: String(aggregates?.feedbackRows || 0),
        subtext: "Rows with narrative evidence",
        status: "warning",
      },
      {
        label: "Outcome validity",
        value: aggregates?.outcome?.hasValidData ? "Valid" : "Limited",
        subtext: aggregates?.outcome?.formulaLabel || "Outcome formula pending",
        status: aggregates?.outcome?.hasValidData ? "positive" : "negative",
      },
    );
  }
  return kpis.slice(0, 3);
}

export function buildComboChartData(aggregates) {
  const regions = aggregates?.byRegion || [];
  if (!regions.length) {
    return [
      { name: "No region data", actual: 0, target: 0, cacIndex: 0 },
    ];
  }
  const maxVal = Math.max(...regions.map((r) => r.value), 1);
  return regions.map((r, i) => ({
    name: r.name,
    actual: Number(r.value.toFixed(2)),
    target: Number((maxVal * 0.92).toFixed(2)),
    cacIndex: Number(
      (
        (aggregates.feedbackRows / Math.max(aggregates.rowCount, 1)) *
        100 *
        (0.8 + i * 0.05)
      ).toFixed(1),
    ),
  }));
}

export function buildPivotRows(aggregates) {
  const regions = aggregates?.byRegion || [];
  const values = regions.map((r) => r.value);
  const total = values.reduce((s, v) => s + v, 0);
  const avg = values.length ? total / values.length : 0;

  const rows = regions.map((r) => ({
    region: r.name,
    revenue: r.value,
    growth: formatPct(r.value, avg),
    status: growthStatus(r.value, values),
    notes:
      r === regions[0]
        ? "Exceeded peer average"
        : r.value < avg
          ? "Requires intervention"
          : "Steady growth",
  }));

  if (rows.length) {
    rows.push({
      region: "Global Total",
      revenue: Number(avg.toFixed(2)),
      growth: formatPct(avg, avg),
      status: "up",
      notes: "",
      isFooter: true,
    });
  }
  return rows;
}

export function fiscalPeriodLabel(filters, dates) {
  if (filters?.fromDate && filters?.toDate) {
    return `${filters.fromDate} – ${filters.toDate}`;
  }
  if (dates?.min && dates?.max) {
    return `${dates.min} – ${dates.max}`;
  }
  return "All dates";
}
