import { normalizeWidget } from "./dashboardOrchestrator.js";

function normalizeIncomingWidget(raw) {
  const widget = raw?.Widget || raw?.widget || raw;
  if (!widget) return null;
  const base = normalizeWidget(widget) || widget;
  return {
    ...base,
    gridPos: widget.gridPos || "bottom-full",
    value: widget.value ?? widget.Value,
    content: widget.content ?? widget.Content,
    kpiHelper: widget.kpiHelper,
    dataSource: widget.dataSource || widget.DataSource || "lifechanger-csv",
    title: widget.title ?? widget.Title ?? base?.title,
  };
}

function applyProperties(widget, properties) {
  const next = { ...widget };
  for (const prop of properties || []) {
    const name = prop.name || prop.property;
    const value = prop.value;
    if (name === "type") next.type = value;
    else if (name === "title") next.title = value;
    else if (name === "content") next.content = value;
    else if (name === "value") next.value = value;
    else if (name === "labels") next.labels = value;
    else if (name === "values") next.values = value;
    else next[name] = value;
  }
  return next;
}

/**
 * Stateful mutation protocol + legacy dashboardMutations.
 */
export function applyStatefulMutations(mutations, handlers) {
  const {
    setDashboardWidgets,
    setDashboardState,
    setDynamicWidgets,
    onApplyFilter,
    onClearConfirm,
  } = handlers;

  const setWidgets = setDashboardWidgets || setDynamicWidgets;
  if (!setWidgets) return;

  for (const mutation of mutations || []) {
    const type = mutation.type || mutation.action;
    const targetId = mutation.targetId || mutation.target || mutation.targetWidgetId;
    const payload = mutation.payload ?? mutation.data ?? mutation.value;

    switch (type) {
      case "CLEAR_DASHBOARD":
        if (mutation.requiresConfirmation && onClearConfirm) {
          onClearConfirm(() => setWidgets([]));
        } else {
          setWidgets([]);
        }
        break;

      case "ADD_WIDGET": {
        const widget = normalizeIncomingWidget(payload);
        if (widget) {
          setWidgets((current) => {
            if (current.some((item) => item.id === widget.id)) {
              return current.map((item) =>
                item.id === widget.id ? { ...item, ...widget } : item,
              );
            }
            return [...current, widget];
          });
        }
        break;
      }

      case "UPDATE_WIDGET":
        setWidgets((current) =>
          current.map((item) => {
            if (item.id !== targetId) return item;
            const properties = payload?.properties || payload?.Property || [];
            const list = Array.isArray(properties)
              ? properties
              : properties
                ? [properties]
                : [];
            if (list.length) return applyProperties(item, list);
            return { ...item, ...normalizeIncomingWidget(payload) };
          }),
        );
        break;

      case "DELETE_WIDGET":
        setWidgets((current) => current.filter((item) => item.id !== targetId));
        break;

      case "clear-all-widgets":
        if (
          String(payload?.explicit || mutation.explicit) === "true" ||
          mutation.requiresConfirmation === false
        ) {
          setWidgets([]);
        }
        break;

      case "update-state":
      case "update-title":
        if (setDashboardState) {
          if (targetId === "DashboardState.PageTitle" || type === "update-title") {
            setDashboardState((current) => ({
              ...current,
              pageTitle: String(payload ?? current.pageTitle),
            }));
          } else if (targetId === "DashboardState.Theme") {
            setDashboardState((current) => ({
              ...current,
              theme: String(payload ?? "light"),
            }));
          } else if (targetId === "DashboardState.ActiveLayout") {
            setDashboardState((current) => ({
              ...current,
              activeLayout: String(payload ?? "focus-mode"),
            }));
          }
        }
        break;

      case "render-widget":
      case "render-chart": {
        const widget = normalizeIncomingWidget(payload);
        if (widget) {
          setWidgets((current) => {
            const exists = current.some((item) => item.id === widget.id);
            if (exists) {
              return current.map((item) =>
                item.id === widget.id ? { ...item, ...widget } : item,
              );
            }
            return [...current, widget];
          });
        }
        break;
      }

      case "remove-element":
        setWidgets((current) =>
          current.filter((item) => item.id !== targetId && item.id !== payload),
        );
        break;

      case "filter-table":
        if (payload?.field && onApplyFilter) {
          onApplyFilter(payload.field, payload.value);
        }
        break;

      case "focus-widget":
      case "switch-tab":
      case "scroll-to":
        if (targetId) {
          document.getElementById(targetId)?.scrollIntoView({
            behavior: "smooth",
            block: "start",
          });
        }
        break;

      default:
        break;
    }
  }
}

export function mergeMutationLists(...lists) {
  return lists.flat().filter(Boolean);
}
