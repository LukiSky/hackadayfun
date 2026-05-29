"""Build chart series from analytics for dashboard widgets."""

from __future__ import annotations

import re
import uuid
from typing import Any

CHART_TYPES = ("bar-chart", "line-chart", "pie-chart", "kpi-card")

DIMENSION_ALIASES: dict[str, str] = {
    "program": "programs_attendance",
    "programs": "programs_attendance",
    "attendance": "programs_attendance",
    "wellbeing": "programs_wellbeing",
    "participants": "programs_participants",
    "sessions": "programs_sessions",
    "term": "quarterly_attendance",
    "terms": "quarterly_attendance",
    "quarter": "quarterly_attendance",
    "quarterly": "quarterly_attendance",
    "trend": "quarterly_attendance",
    "sentiment": "sentiment",
    "feedback": "sentiment",
    "theme": "themes",
    "themes": "themes",
    "topic": "themes",
    "school": "programs_attendance",
    "risk": "at_risk",
    "at-risk": "at_risk",
}


def _new_widget_id() -> str:
    return f"widget-{uuid.uuid4().hex[:8]}"


def _series_from_programs(programs: list[dict], value_key: str, title: str) -> dict[str, Any]:
    labels = [p["name"][:28] for p in programs[:12]]
    values = [float(p.get(value_key, 0)) for p in programs[:12]]
    if value_key == "attendance_rate":
        values = [round(v * 100, 1) for v in values]
    return {
        "id": _new_widget_id(),
        "type": "bar-chart",
        "title": title,
        "labels": labels,
        "values": values,
        "dimension": value_key,
    }


def build_series(analytics: dict, dimension: str) -> dict[str, Any]:
    programs = analytics.get("programs") or []
    trends = analytics.get("quarterly_trends") or {}
    sentiment = analytics.get("sentiment_distribution") or {}
    themes = analytics.get("top_themes") or []

    if dimension == "programs_wellbeing":
        return _series_from_programs(programs, "wellbeing_score_avg", "Wellbeing by program")
    if dimension == "programs_participants":
        return _series_from_programs(programs, "participants", "Participants by program")
    if dimension == "programs_sessions":
        return _series_from_programs(programs, "sessions_completed", "Sessions by program")
    if dimension == "quarterly_attendance":
        terms = trends.get("terms") or []
        values = [round(v * 100, 1) for v in (trends.get("overall_attendance") or [])]
        return {
            "id": _new_widget_id(),
            "type": "line-chart",
            "title": "Attendance trend by term",
            "labels": terms,
            "values": values,
            "dimension": dimension,
        }
    if dimension == "quarterly_wellbeing":
        terms = trends.get("terms") or []
        return {
            "id": _new_widget_id(),
            "type": "line-chart",
            "title": "Wellbeing trend by term",
            "labels": terms,
            "values": [float(v) for v in (trends.get("wellbeing_avg") or [])],
            "dimension": dimension,
        }
    if dimension == "sentiment":
        labels = list(sentiment.keys()) or ["positive", "mixed", "negative"]
        return {
            "id": _new_widget_id(),
            "type": "pie-chart",
            "title": "Feedback sentiment",
            "labels": labels,
            "values": [float(sentiment.get(k, 0)) for k in labels],
            "dimension": dimension,
        }
    if dimension == "themes":
        top = themes[:8]
        return {
            "id": _new_widget_id(),
            "type": "bar-chart",
            "title": "Top feedback themes",
            "labels": [t[0][:24] for t in top],
            "values": [float(t[1]) for t in top],
            "dimension": dimension,
        }
    if dimension == "at_risk":
        at_risk = analytics.get("at_risk_programs") or []
        return {
            "id": _new_widget_id(),
            "type": "bar-chart",
            "title": "At-risk programs (count=1 each)",
            "labels": [p["name"][:28] for p in at_risk[:12]] or ["None"],
            "values": [1.0] * min(len(at_risk), 12) or [0],
            "dimension": dimension,
        }
    # default: programs attendance
    return _series_from_programs(programs, "attendance_rate", "Attendance by program")


def infer_dimension_from_prompt(prompt: str) -> str:
    lower = prompt.lower()
    for token, dim in DIMENSION_ALIASES.items():
        if re.search(rf"\b{re.escape(token)}\b", lower):
            return dim
    if "pie" in lower and ("sentiment" in lower or "feedback" in lower):
        return "sentiment"
    if "line" in lower or "trend" in lower:
        return "quarterly_attendance"
    return "programs_attendance"


def infer_chart_type_from_prompt(prompt: str, default: str = "bar-chart") -> str:
    lower = prompt.lower()
    if "pie" in lower:
        return "pie-chart"
    if "line" in lower or "trend" in lower:
        return "line-chart"
    if "kpi" in lower or "metric" in lower or "total" in lower:
        return "kpi-card"
    if "bar" in lower:
        return "bar-chart"
    return default


def build_kpi_from_analytics(analytics: dict, prompt: str) -> dict[str, Any]:
    summary = analytics.get("summary") or {}
    lower = prompt.lower()
    if "session" in lower:
        value = str(summary.get("total_sessions", "—"))
        title = "Total sessions"
    elif "school" in lower:
        value = str(summary.get("unique_schools", "—"))
        title = "Partner schools"
    elif "risk" in lower:
        value = str(summary.get("at_risk_count", "—"))
        title = "At-risk programs"
    else:
        value = f"{int((summary.get('avg_attendance') or 0) * 100)}%"
        title = "Average attendance"
    return {
        "id": _new_widget_id(),
        "type": "kpi-card",
        "title": title,
        "value": value,
        "labels": [],
        "values": [],
    }


def build_widget_from_request(analytics: dict, prompt: str, chart_type: str | None = None) -> dict[str, Any]:
    ctype = chart_type or infer_chart_type_from_prompt(prompt)
    if ctype == "kpi-card":
        return build_kpi_from_analytics(analytics, prompt)
    dim = infer_dimension_from_prompt(prompt)
    widget = build_series(analytics, dim)
    widget["type"] = ctype
    if ctype == "pie-chart" and dim not in ("sentiment", "themes"):
        widget = build_series(analytics, "sentiment")
        widget["type"] = "pie-chart"
    return widget
