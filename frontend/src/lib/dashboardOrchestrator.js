export const DEFAULT_DASHBOARD_STATE = {
  pageTitle: "Dashboard",
  theme: "light",
  activeLayout: "standard",
};

export async function orchestrateLLM({
  userPrompt,
  currentDashboardState,
  aggregates,
  availableFields,
  activeFilters,
  evidenceRows,
  dynamicWidgetIds,
  currentDashboardWidgets,
  useSpeaker = true,
  storyMode = false,
  questionMode = false,
}) {
  const response = await fetch("/api/llm/orchestrate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      userPrompt,
      currentDashboardState,
      currentDashboardWidgets,
      aggregates,
      availableFields,
      activeFilters,
      evidenceRows,
      dynamicWidgetIds,
      useSpeaker,
      storyMode,
      questionMode,
    }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(
      typeof err.detail === "string" ? err.detail : "LLM orchestrate failed",
    );
  }

  return response.json();
}

export function normalizeWidget(raw) {
  if (!raw || typeof raw !== "object") return null;
  const id = raw.id || `widget-${Date.now()}`;
  const labels = raw.labels || raw.chartData?.labels || [];
  const values = raw.values || raw.chartData?.values || [];
  return {
    id,
    type: raw.type || "bar-chart",
    title: raw.title || raw.Title || "Generated chart",
    renderStatus: raw.renderStatus || "active",
    labels: Array.isArray(labels) ? labels : [],
    values: Array.isArray(values) ? values.map(Number) : [],
  };
}

/**
 * Apply dashboardMutations from /api/llm/orchestrate (UIMutations spec).
 */
export function applyDashboardMutations(mutations, handlers) {
  const {
    setDashboardState,
    setDynamicWidgets,
    onApplyFilter,
  } = handlers;

  for (const mutation of mutations || []) {
    const action = mutation.action;
    const target = mutation.target || mutation.targetWidgetId;
    const data = mutation.data ?? mutation.value ?? mutation.payload;

    switch (action) {
      case "clear-all-widgets":
        setDynamicWidgets([]);
        break;

      case "update-state":
      case "update-title":
        if (target === "DashboardState.PageTitle" || action === "update-title") {
          setDashboardState((current) => ({
            ...current,
            pageTitle: String(data ?? current.pageTitle),
          }));
        } else if (target === "DashboardState.Theme") {
          setDashboardState((current) => ({
            ...current,
            theme: String(data ?? "light"),
          }));
        } else if (target === "DashboardState.ActiveLayout") {
          setDashboardState((current) => ({
            ...current,
            activeLayout: String(data ?? "focus-mode"),
          }));
        }
        break;

      case "render-widget":
      case "render-chart": {
        const widget = normalizeWidget(
          typeof data === "string" ? { id: data } : data,
        );
        if (widget) {
          setDynamicWidgets((current) => {
            const without = current.filter((item) => item.id !== widget.id);
            return [...without, widget];
          });
        }
        break;
      }

      case "remove-element":
        setDynamicWidgets((current) =>
          current.filter((item) => item.id !== data && item.id !== target),
        );
        break;

      case "filter-table":
        if (data?.field && onApplyFilter) {
          onApplyFilter(data.field, data.value);
        }
        break;

      case "focus-widget":
      case "switch-tab":
      case "scroll-to": {
        const elId = target?.replace("dynamic-widgets-area", "") || target;
        if (elId && elId !== "dynamic-widgets-area") {
          document.getElementById(elId)?.scrollIntoView({
            behavior: "smooth",
            block: "start",
          });
        }
        break;
      }

      default:
        break;
    }
  }
}

export function themeClassName(theme) {
  return theme === "dark"
    ? "bg-[#1a1a1a] text-white"
    : "bg-[#F7F7F2] text-black";
}
