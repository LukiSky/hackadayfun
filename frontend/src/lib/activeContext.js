const CHART_TYPES = new Set(["bar-chart", "line-chart", "pie-chart", "bar", "line", "pie"]);

export function buildActiveContext({
  dashboardWidgets = [],
  dynamicWidgets = [],
  storyDashboard = {},
  datasetMeta = null,
}) {
  const currentWidgets = [];
  const seen = new Set();
  const allWidgets = dashboardWidgets.length ? dashboardWidgets : dynamicWidgets;

  function addWidget(id, type) {
    const key = `${id}:${type}`;
    if (!id || seen.has(key)) return;
    seen.add(key);
    currentWidgets.push({ id, type });
  }

  for (const widget of allWidgets) {
    addWidget(widget.id, widget.type || "bar-chart");
  }

  for (const viz of storyDashboard.visualizations || []) {
    const type = viz.chartConfig?.type || "bar-chart";
    addWidget(viz.sectionId || viz.id || "revenue-viz", type);
  }

  if ((storyDashboard.storytellingBlocks || []).length) {
    addWidget("revenue-story", "audio-text");
  }

  if (!currentWidgets.some((widget) => CHART_TYPES.has(widget.type))) {
    const hasViz = (storyDashboard.visualizations || []).length > 0;
    if (!hasViz && allWidgets.length === 0) {
      // no chart on canvas
    }
  }

  return {
    currentWidgets,
    activeDataSources: [
      datasetMeta?.file
        ? `lifechanger://${datasetMeta.file}`
        : "lifechanger-csv",
    ],
  };
}

export function contextHasChartTypes(activeContext) {
  return (activeContext?.currentWidgets || []).some((widget) =>
    CHART_TYPES.has(widget.type),
  );
}

export function contextHasAudioText(activeContext) {
  return (activeContext?.currentWidgets || []).some(
    (widget) => widget.type === "audio-text",
  );
}

export const CHART_PALETTES = {
  Monochrome: ["#000000", "#4A4A4A", "#6A6A6A", "#8A8A8A"],
  "Brand Colors": ["#000000", "#87BAE5", "#FFD100", "#6A8FB3"],
  "High Contrast": ["#000000", "#FF0000", "#0000FF", "#FFD100"],
};

export const DEFAULT_WIDGET_SETTINGS = {
  "revenue-viz": {
    theme: "Brand Colors",
    showDataLabels: true,
    xAxisInterval: "Monthly",
  },
  "revenue-story": {
    voiceModel: "Professional (Female)",
    playbackSpeed: 1.0,
    detailLevel: "Standard",
  },
};

export const VOICE_TO_SPEAKER = {
  "Professional (Female)": "adultFemale1",
  "Energetic (Male)": "adultMale1",
  "Calm (Neutral)": "narrator",
};
