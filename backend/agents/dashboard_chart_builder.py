"""
Build dashboard widgets from the chart catalog + user prompt.

Bridges Power BI–style catalog charts to Recharts widget mutations (ADD_WIDGET).
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from agents.chart_service import _VISUAL_INTENT, generate_charts_for_request, select_charts_for_question

_CHART_TYPE_FROM_PROMPT = re.compile(
    r"\b(pie|donut|doughnut)\b",
    re.I,
)
_LINE_FROM_PROMPT = re.compile(r"\b(line|trend|over time|timeline)\b", re.I)
_KPI_FROM_PROMPT = re.compile(r"\b(kpi|metric|total|count|overview)\b", re.I)

_CATALOG_TO_WIDGET = {
    "bar": "bar-chart",
    "horizontalBar": "bar-chart",
    "pie": "pie-chart",
    "line": "line-chart",
}


def wants_dashboard_chart(prompt: str) -> bool:
    text = (prompt or "").strip()
    if not text:
        return False
    if _VISUAL_INTENT.search(text):
        return True
    if re.search(
        r"\b(add|create|generate|show|build|make|plot|draw|display|put)\b.*\b(chart|graph|visual|widget)\b"
        r"|\b(bar|line|pie)\s+chart\b"
        r"|\bchart\b.*\b(by|of|for|showing)\b",
        text,
        re.I,
    ):
        return True
    return bool(re.search(r"\b(visuali[sz]e|graph this|plot)\b", text, re.I))


def _infer_widget_type(prompt: str, catalog_type: str) -> str:
    if _CHART_TYPE_FROM_PROMPT.search(prompt):
        return "pie-chart"
    if _LINE_FROM_PROMPT.search(prompt) and "bar" not in prompt.lower():
        return "line-chart"
    if _KPI_FROM_PROMPT.search(prompt) and catalog_type == "bar":
        return "kpi-card"
    return _CATALOG_TO_WIDGET.get(catalog_type, "bar-chart")


def catalog_chart_to_widget(catalog_chart: dict, prompt: str = "") -> dict:
    data = catalog_chart.get("data") or []
    labels = [str(row.get("label", ""))[:40] for row in data]
    values = []
    for row in data:
        try:
            values.append(float(row.get("value", 0)))
        except (TypeError, ValueError):
            values.append(0.0)

    widget_type = _infer_widget_type(prompt, catalog_chart.get("type", "bar"))

    widget: dict[str, Any] = {
        "id": f"widget-{uuid.uuid4().hex[:8]}",
        "type": widget_type,
        "title": catalog_chart.get("title") or "Chart",
        "labels": labels,
        "values": values,
        "gridPos": "bottom-full",
        "dataSource": "lifechanger-csv",
        "renderStatus": "active",
        "catalogChartId": catalog_chart.get("id"),
    }

    if widget_type == "kpi-card" and values:
        widget["value"] = str(int(values[0]) if values[0] == int(values[0]) else round(values[0], 1))
        widget["labels"] = []
        widget["values"] = []

    return widget


def build_widgets_from_prompt(prompt: str, *, max_charts: int = 2) -> list[dict]:
    """Return one or more widgets for the dashboard canvas."""
    charts = select_charts_for_question(prompt, max_charts=max_charts)
    if not charts:
        try:
            result = generate_charts_for_request(prompt)
            charts = result.get("charts") or []
        except Exception:
            charts = []
    return [catalog_chart_to_widget(c, prompt) for c in charts[:max_charts]]


def build_primary_widget_from_prompt(prompt: str, aggregates: dict | None = None) -> dict:
    """Single best widget — catalog first, then aggregate heuristics."""
    widgets = build_widgets_from_prompt(prompt, max_charts=1)
    if widgets:
        return widgets[0]

    # Fallback: legacy aggregate buckets
    agg = aggregates or {}
    from agents.dashboard_supervisor import _pick_series

    title, series, chart_kind = _pick_series(prompt, agg)
    labels = [str(item.get("name", "")) for item in series[:12]]
    values = [float(item.get("value") or 0) for item in series[:12]]
    wtype = "line-chart" if chart_kind == "line" else "bar-chart"
    if _CHART_TYPE_FROM_PROMPT.search(prompt):
        wtype = "pie-chart"
    return {
        "id": f"widget-{uuid.uuid4().hex[:8]}",
        "type": wtype,
        "title": title,
        "labels": labels,
        "values": values,
        "gridPos": "bottom-full",
        "dataSource": "lifechanger-csv",
        "renderStatus": "active",
    }
