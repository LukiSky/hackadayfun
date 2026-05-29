/** Apply ADD / UPDATE / DELETE / CLEAR and legacy dashboard actions to widget state. */

export const CHART_TYPES = ["bar-chart", "line-chart", "pie-chart", "kpi-card"];

export function normalizeWidget(raw) {
  const w = raw?.Widget ?? raw?.widget ?? raw ?? {};
  return {
    id: w.id || `widget-${Date.now()}`,
    type: w.type || "bar-chart",
    title: w.title || "Chart",
    labels: Array.isArray(w.labels) ? w.labels : [],
    values: Array.isArray(w.values) ? w.values.map(Number) : [],
    value: w.value,
    gridPos: w.gridPos || "auto",
  };
}

export function applyStatefulMutations(widgets, mutations, options = {}) {
  const { onDashboardState, confirmClear = window.confirm } = options;
  let next = [...widgets];
  let dashboardPatch = null;

  for (const mutation of mutations || []) {
    const type = mutation.type || mutation.action;
    if (!type) continue;

    if (type === "CLEAR_DASHBOARD" || type === "clear-all-widgets") {
      const needsConfirm = mutation.requiresConfirmation !== false;
      if (needsConfirm && !confirmClear("Clear all dashboard widgets?")) continue;
      next = [];
      continue;
    }

    if (type === "DELETE_WIDGET" || type === "remove-element") {
      const id = mutation.targetId || mutation.targetWidgetId || mutation.data?.id;
      next = next.filter((w) => w.id !== id);
      continue;
    }

    if (type === "ADD_WIDGET" || type === "render-widget" || type === "render-chart") {
      const widget = normalizeWidget(mutation.payload?.Widget ? mutation.payload : mutation.data);
      const idx = next.findIndex((w) => w.id === widget.id);
      if (idx >= 0) next[idx] = { ...next[idx], ...widget };
      else next.push(widget);
      continue;
    }

    if (type === "UPDATE_WIDGET") {
      const id = mutation.targetId;
      const idx = next.findIndex((w) => w.id === id);
      if (idx < 0) continue;
      const updated = { ...next[idx] };
      const props = mutation.payload?.properties || [];
      for (const { name, value } of props) {
        if (name === "labels" || name === "values") {
          updated[name] = Array.isArray(value) ? value : updated[name];
        } else {
          updated[name] = value;
        }
      }
      if (mutation.payload && !mutation.payload.properties) {
        Object.assign(updated, mutation.payload);
      }
      next[idx] = updated;
      continue;
    }

    if (type === "update-title" || type === "update-state") {
      dashboardPatch = { ...(dashboardPatch || {}), ...(mutation.data || {}) };
      if (mutation.data?.pageTitle) dashboardPatch.pageTitle = mutation.data.pageTitle;
      if (mutation.data?.theme) dashboardPatch.theme = mutation.data.theme;
    }
  }

  if (dashboardPatch && onDashboardState) onDashboardState(dashboardPatch);
  return next;
}
