export function buildDefaultWidgets(aggregates) {
  const sentiment = aggregates?.sentiment || [];
  const byRegion = aggregates?.byRegion || [];
  const topRegion = byRegion[0];
  const outcome = aggregates?.outcome || {};
  const rowCount = aggregates?.rowCount || 0;
  const validOutcome = outcome.validRows ?? 0;

  const briefing =
    rowCount > 0
      ? `Across ${rowCount.toLocaleString()} filtered responses, ${
          topRegion?.name || "the leading segment"
        } shows the strongest regional outcome signal. Workshop delivery remains aligned with LifeChanger wellbeing goals.`
      : "Load the LifeChanger dataset and apply filters to generate your executive summary.";

  return [
    {
      id: "widget-rev-ytd",
      type: "line-chart",
      gridPos: "top-left",
      title: "Workshop Outcomes Over Time",
      labels: sentiment.length
        ? sentiment.map((point) => point.name)
        : ["No date axis"],
      values: sentiment.length
        ? sentiment.map((point) => point.value ?? 0)
        : [0],
      dataSource: "lifechanger-csv",
      renderStatus: "active",
    },
    {
      id: "widget-user-growth",
      type: "kpi-card",
      gridPos: "top-right",
      title: "Valid Outcome Rows",
      value: outcome.hasValidData
        ? `+${validOutcome}`
        : String(rowCount),
      kpiHelper: outcome.hasValidData
        ? "Rows used in outcome score formula"
        : "Total filtered CSV rows",
      dataSource: "lifechanger-csv",
      renderStatus: "active",
    },
    {
      id: "widget-morning-briefing",
      type: "audio-text",
      gridPos: "bottom-full",
      title: "Morning Executive Summary",
      content: briefing,
      dataSource: "lifechanger-csv",
      renderStatus: "active",
    },
  ];
}
