"""
Multi-step dashboard orchestrator (LangChain-style pipeline).

Chains:
  1. intent_chain — classify user goal
  2. planner_chain — LLM JSON plan (optional, HF_TOKEN)
  3. mutation_chain — build ADD/UPDATE/DELETE/CLEAR mutations
  4. narrative_chain — bot reply text
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from agents.ask_agent import ask_data_question
from agents.local_insights import ask_locally
from agents.chart_catalog import (
    CHART_TYPES,
    build_widget_from_request,
    infer_chart_type_from_prompt,
)
from agents.llm_client import complete_with_context
from agents.prompt_intent import orchestration_mode
from data.repository import MockDataRepository

_repo = MockDataRepository()

PLANNER_SYSTEM = """You are the Dashboard Planner for ImpactLens AI.
Given the user prompt, current widgets, and dataset summary, output ONLY valid JSON:
{
  "intent": "add_chart|edit_chart|delete_chart|clear|question|update_title",
  "chartType": "bar-chart|line-chart|pie-chart|kpi-card",
  "dimensionHint": "programs_attendance|programs_wellbeing|quarterly_attendance|sentiment|themes|at_risk",
  "targetWidgetId": null or "widget-xxx",
  "newTitle": null or string,
  "replyHint": "one sentence for the user"
}
No markdown. Use dataset dimensions only."""


def _analytics_payload() -> dict:
    return _repo.get_analytics()


def _widget_summary(widgets: list[dict]) -> list[dict]:
    return [
        {
            "id": w.get("id"),
            "type": w.get("type"),
            "title": w.get("title"),
            "labels": (w.get("labels") or [])[:6],
            "values": (w.get("values") or [])[:6],
        }
        for w in widgets
    ]


def _llm_plan(prompt: str, widgets: list[dict], analytics: dict) -> dict | None:
    if not os.environ.get("HF_TOKEN"):
        return None
    try:
        user = json.dumps(
            {
                "userPrompt": prompt,
                "currentWidgets": _widget_summary(widgets),
                "summary": analytics.get("summary"),
                "top_themes": analytics.get("top_themes", [])[:5],
                "sentiment": analytics.get("sentiment_distribution"),
            },
            indent=2,
        )
        raw = complete_with_context(PLANNER_SYSTEM, user, temperature=0.2)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except Exception:
        return None


def _mutation_add(widget: dict) -> dict:
    return {"type": "ADD_WIDGET", "payload": {"Widget": widget}}


def _mutation_update(target_id: str, properties: list[dict]) -> dict:
    return {
        "type": "UPDATE_WIDGET",
        "targetId": target_id,
        "payload": {"properties": properties},
    }


def _mutation_delete(target_id: str) -> dict:
    return {"type": "DELETE_WIDGET", "targetId": target_id}


def _mutation_clear() -> dict:
    return {"type": "CLEAR_DASHBOARD", "requiresConfirmation": True}


def _resolve_target_widget(prompt: str, widgets: list[dict]) -> dict | None:
    if not widgets:
        return None
    lower = prompt.lower()
    for w in widgets:
        title = (w.get("title") or "").lower()
        wid = (w.get("id") or "").lower()
        if title and title in lower:
            return w
        if wid and wid in lower:
            return w
    # "last chart" / "the chart"
    if re.search(r"\b(last|latest|this)\b.*\b(chart|widget)\b", lower):
        charts = [w for w in widgets if w.get("type") != "kpi-card"]
        return charts[-1] if charts else widgets[-1]
    return widgets[-1]


def _rule_mutations(
    prompt: str,
    widgets: list[dict],
    analytics: dict,
    plan: dict | None,
) -> tuple[list[dict], str]:
    mode = orchestration_mode(prompt)
    if plan and plan.get("intent"):
        mode_map = {
            "add_chart": "add_chart",
            "edit_chart": "edit",
            "delete_chart": "delete",
            "clear": "clear",
            "question": "question",
            "update_title": "dashboard_control",
        }
        mode = mode_map.get(plan["intent"], mode)

    mutations: list[dict] = []
    reply_parts: list[str] = []

    if mode == "clear":
        mutations.append(_mutation_clear())
        reply_parts.append("Cleared the dashboard — confirm to apply.")
        return mutations, " ".join(reply_parts)

    if mode == "delete":
        target = _resolve_target_widget(prompt, widgets)
        if target:
            mutations.append(_mutation_delete(target["id"]))
            tid = target.get("id", "widget")
            reply_parts.append(f"Removed «{target.get('title', tid)}».")
        else:
            reply_parts.append("No widget matched for deletion.")
        return mutations, " ".join(reply_parts)

    if mode == "edit":
        target = _resolve_target_widget(prompt, widgets)
        if not target:
            reply_parts.append("No widget to edit — add a chart first.")
            return mutations, " ".join(reply_parts)
        props: list[dict] = []
        new_type = infer_chart_type_from_prompt(prompt, target.get("type", "bar-chart"))
        if new_type != target.get("type"):
            props.append({"name": "type", "value": new_type})
        title_match = re.search(r'title\s+(?:to\s+)?["\']?([^"\']+)["\']?', prompt, re.I)
        if title_match:
            props.append({"name": "title", "value": title_match.group(1).strip()})
        if plan and plan.get("newTitle"):
            props.append({"name": "title", "value": plan["newTitle"]})
        if not props:
            props.append({"name": "type", "value": new_type})
        mutations.append(_mutation_update(target["id"], props))
        reply_parts.append(f"Updated «{target.get('title')}».")
        return mutations, " ".join(reply_parts)

    if mode == "add_chart":
        chart_type = None
        if plan and plan.get("chartType") in CHART_TYPES:
            chart_type = plan["chartType"]
        widget = build_widget_from_request(analytics, prompt, chart_type)
        if plan and plan.get("newTitle"):
            widget["title"] = plan["newTitle"]
        mutations.append(_mutation_add(widget))
        reply_parts.append(
            f"Added {widget['type'].replace('-', ' ')}: «{widget['title']}»."
        )
        return mutations, " ".join(reply_parts)

    if mode == "dashboard_control":
        title_match = re.search(
            r'(?:title|rename)\s+(?:to\s+)?["\']?([^"\']+)["\']?', prompt, re.I
        )
        dash_mutations = []
        if title_match:
            dash_mutations.append(
                {
                    "action": "update-title",
                    "data": {"pageTitle": title_match.group(1).strip()},
                }
            )
            reply_parts.append(f"Dashboard title set to «{title_match.group(1).strip()}».")
        return mutations, " ".join(reply_parts) or "Updated dashboard settings."

    return mutations, ""


def _narrative_chain(
    prompt: str,
    mode: str,
    rule_reply: str,
    insight: dict | None,
) -> str:
    if rule_reply:
        base = rule_reply
    elif insight:
        base = insight.get("answer", "")
    else:
        base = "Done."

    if mode == "question" and insight:
        return base

    if os.environ.get("HF_TOKEN") and mode != "question":
        try:
            extra = complete_with_context(
                "You are a concise dashboard copilot. One short friendly sentence.",
                f"User: {prompt}\nAction taken: {base}",
                temperature=0.4,
            )
            if extra and len(extra) < 280:
                return extra.strip()
        except Exception:
            pass
    return base


def orchestrate_dashboard_command(
    *,
    user_prompt: str,
    current_widgets: list[dict] | None = None,
    dashboard_state: dict | None = None,
    interactive: bool = True,
) -> dict[str, Any]:
    """
    Main entry: returns bot text, stateful mutations, legacy dashboardMutations, chain trace.
    """
    prompt = (user_prompt or "").strip()
    widgets = list(current_widgets or [])
    state = dict(dashboard_state or {})
    analytics = _analytics_payload()
    mode = orchestration_mode(prompt)

    chains_executed = ["intent_chain"]
    plan = _llm_plan(prompt, widgets, analytics) if interactive else None
    if plan:
        chains_executed.append("planner_chain")

    mutations: list[dict] = []
    dashboard_mutations: list[dict] = []
    insight = None

    if mode == "question":
        chains_executed.append("insight_chain")
        try:
            insight = ask_data_question(prompt)
        except Exception:
            insight = ask_locally(prompt)
        # Also add a chart when user asks "show me a chart of X" style — already excluded
        if re.search(r"\b(show|visuali[sz]e|chart)\b", prompt, re.I) and not insight:
            mode = "add_chart"

    rule_reply_text = ""
    if mode != "question":
        chains_executed.append("mutation_chain")
        rule_muts, rule_reply = _rule_mutations(prompt, widgets, analytics, plan)
        mutations.extend(rule_muts)
        rule_reply_text = rule_reply

    # Question + chart combo: "What is attendance and show a bar chart"
    if mode == "question" and re.search(
        r"\b(bar|line|pie)\s+chart\b|\bchart\b.*\b(by|of|for)\b", prompt, re.I
    ):
        chains_executed.append("mutation_chain")
        w = build_widget_from_request(analytics, prompt)
        mutations.append(_mutation_add(w))
        rule_reply_text = (rule_reply_text + f" Also added «{w['title']}».").strip()

    chains_executed.append("narrative_chain")
    bot_text = _narrative_chain(prompt, mode, rule_reply_text, insight)
    if mode == "question" and rule_reply_text and insight:
        bot_text = f"{insight.get('answer', '')}\n\n{rule_reply_text}".strip()

    title_match = re.search(
        r'(?:dashboard\s+title|title)\s+(?:to\s+)?["\']?([^"\']+)["\']?', prompt, re.I
    )
    if title_match:
        state["pageTitle"] = title_match.group(1).strip()
        dashboard_mutations.append(
            {"action": "update-title", "data": {"pageTitle": state["pageTitle"]}}
        )

    return {
        "botResponseText": bot_text,
        "mutations": mutations,
        "dashboardMutations": dashboard_mutations,
        "dashboardState": {
            "pageTitle": state.get("pageTitle", "Impact Dashboard"),
            "theme": state.get("theme", "light"),
            "editMode": state.get("editMode", interactive),
        },
        "editorIntent": mode,
        "currentDashboardState": _widget_summary(widgets),
        "source": "langchain" if plan else ("insight" if mode == "question" else "local"),
        "chainsExecuted": chains_executed,
        "followUpQuestions": _follow_ups(mode, mutations),
        "insight": insight,
    }


def _follow_ups(mode: str, mutations: list[dict]) -> list[str]:
    if mode == "question":
        return [
            "Add a bar chart of attendance by program",
            "Change the last chart to a pie chart",
        ]
    if any(m.get("type") == "ADD_WIDGET" for m in mutations):
        return [
            "Edit that chart title to Regional attendance",
            "Add a line chart of quarterly trends",
        ]
    return ["Add a pie chart of feedback sentiment", "Clear all widgets"]
