"""Stateful dashboard editor — intent routing + mutation protocol (append by default)."""

from __future__ import annotations

import json
import logging
import os
import re
import uuid

from agents.dashboard_chart_builder import build_primary_widget_from_prompt, wants_dashboard_chart
from agents.dashboard_supervisor import run_data_visualization_chain, run_storytelling_chain
from agents.langchain.engine import invoke_chain

logger = logging.getLogger(__name__)

_EXPLICIT_CLEAR = re.compile(
    r"\b(clear|wipe|reset|start over|remove all|delete all)\b.*\b(dashboard|canvas|everything|all widgets)\b"
    r"|\b(clear|wipe)\s+(the\s+)?dashboard\b",
    re.I,
)
_EXPLICIT_DELETE_WIDGET = re.compile(
    r"\b(remove|delete)\b.*\b(briefing|widget|chart|kpi|summary|growth|revenue|ytd)\b",
    re.I,
)
_EDIT_INTENT = re.compile(
    r"\b(change|update|edit|convert|switch|make)\b.*\b(to|into|a)\b",
    re.I,
)
_WIDGET_REF = {
    "ytd": "widget-rev-ytd",
    "revenue": "widget-rev-ytd",
    "year-to-date": "widget-rev-ytd",
    "growth": "widget-user-growth",
    "user": "widget-user-growth",
    "kpi": "widget-user-growth",
    "briefing": "widget-morning-briefing",
    "morning": "widget-morning-briefing",
    "summary": "widget-morning-briefing",
    "narrative": "widget-morning-briefing",
    "story": "widget-morning-briefing",
}


def _widget_summary(widgets: list[dict]) -> list[dict]:
    return [
        {
            "id": w.get("id"),
            "type": w.get("type"),
            "title": w.get("title"),
        }
        for w in widgets
        if w.get("id")
    ]


def classify_intent(prompt: str, current_widgets: list[dict]) -> str:
    text = prompt.strip()
    if _EXPLICIT_CLEAR.search(text):
        return "CLEAR_ALL"
    if _EXPLICIT_DELETE_WIDGET.search(text):
        return "DELETE_WIDGET"
    if _EDIT_INTENT.search(text):
        return "EDIT_EXISTING"
    if wants_dashboard_chart(text):
        return "ADD"
    if re.search(r"\b(add|show|create|generate|new)\b", text, re.I):
        return "ADD"
    if re.search(r"\b(pie|bar|line|chart|kpi)\b", text, re.I):
        return "ADD"
    return "ADD"


def _resolve_target_id(prompt: str, widgets: list[dict]) -> str | None:
    lower = prompt.lower()
    for key, wid in _WIDGET_REF.items():
        if key in lower:
            return wid
    for widget in widgets:
        title = (widget.get("title") or "").lower()
        if title and title in lower:
            return widget["id"]
    return widgets[0]["id"] if widgets else None


def _build_add_widget(prompt: str, aggregates: dict) -> dict:
    return build_primary_widget_from_prompt(prompt, aggregates)


def _build_add_widgets(prompt: str, aggregates: dict, *, max_charts: int = 2) -> list[dict]:
    from agents.dashboard_chart_builder import build_widgets_from_prompt

    widgets = build_widgets_from_prompt(prompt, max_charts=max_charts)
    if widgets:
        return widgets
    return [_build_add_widget(prompt, aggregates)]


def run_dashboard_editor(
    prompt: str,
    current_widgets: list[dict],
    aggregates: dict,
    *,
    fields: dict | None = None,
) -> dict:
    """
    Returns mutation protocol response:
      mutations[], botResponseText, intent, currentDashboardState
    """
    intent = classify_intent(prompt, current_widgets)
    mutations: list[dict] = []
    reply = ""

    if intent == "CLEAR_ALL":
        mutations.append({"type": "CLEAR_DASHBOARD", "requiresConfirmation": True})
        reply = "I've cleared the dashboard. Default widgets can be restored by refreshing."
    elif intent == "DELETE_WIDGET":
        target_id = _resolve_target_id(prompt, current_widgets)
        if target_id:
            mutations.append({"type": "DELETE_WIDGET", "targetId": target_id})
            reply = f"Removed {target_id} from the canvas."
        else:
            reply = "I couldn't identify which widget to remove. Try naming it (e.g. morning briefing)."
    elif intent == "EDIT_EXISTING":
        target_id = _resolve_target_id(prompt, current_widgets)
        if not target_id:
            reply = "No widget matched for editing. Specify YTD revenue, user growth, or morning briefing."
        else:
            properties: list[dict] = []
            lower = prompt.lower()
            if "bar" in lower:
                properties.append({"name": "type", "value": "bar-chart"})
            elif "line" in lower:
                properties.append({"name": "type", "value": "line-chart"})
            elif "pie" in lower:
                properties.append({"name": "type", "value": "pie-chart"})
            if properties:
                mutations.append(
                    {
                        "type": "UPDATE_WIDGET",
                        "targetId": target_id,
                        "payload": {"properties": properties},
                    }
                )
                reply = f"Updated {target_id} in place."
            elif target_id == "widget-morning-briefing":
                narrative = run_storytelling_chain(
                    prompt,
                    {"labels": [], "values": []},
                    aggregates,
                )
                mutations.append(
                    {
                        "type": "UPDATE_WIDGET",
                        "targetId": target_id,
                        "payload": {"properties": [{"name": "content", "value": narrative}]},
                    }
                )
                reply = "Refreshed the morning briefing narrative."
            else:
                viz = run_data_visualization_chain(prompt, aggregates)
                chart = viz["chartConfig"]
                mutations.append(
                    {
                        "type": "UPDATE_WIDGET",
                        "targetId": target_id,
                        "payload": {
                            "properties": [
                                {"name": "labels", "value": chart.get("labels")},
                                {"name": "values", "value": chart.get("values")},
                                {"name": "title", "value": chart.get("title")},
                            ]
                        },
                    }
                )
                reply = f"Refreshed data for {target_id}."
    else:
        new_widgets = _build_add_widgets(prompt, aggregates, max_charts=2)
        for widget in new_widgets:
            mutations.append({"type": "ADD_WIDGET", "payload": {"Widget": widget}})
        titles = ", ".join(f"«{w.get('title', 'chart')}»" for w in new_widgets)
        reply = (
            f"Added {len(new_widgets)} chart(s) to the dashboard: {titles}. "
            "Existing widgets were preserved."
        )

    if os.environ.get("HF_TOKEN") and intent == "ADD":
        try:
            context = {
                "intent": intent,
                "CURRENT_DASHBOARD_STATE": _widget_summary(current_widgets),
                "new_widget": mutations[-1].get("payload") if mutations else None,
            }
            llm_reply = invoke_chain(
                "You are the DashboardEditorChain narrator. Confirm the mutation in one friendly sentence.",
                f"Context:\n{json.dumps(context)}\n\nUser: {prompt}",
                temperature=0.3,
            ).strip()
            if llm_reply:
                reply = llm_reply
        except Exception:
            logger.debug("Editor narration LLM skipped", exc_info=True)

    return {
        "botResponseText": reply,
        "mutations": mutations,
        "intent": intent,
        "currentDashboardState": _widget_summary(current_widgets),
        "preservation": "DEFAULT_TO_APPEND",
    }
