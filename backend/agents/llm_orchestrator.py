"""LLM dashboard orchestration — POST /api/llm/orchestrate."""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from typing import Any

from agents.dashboard_insights import build_local_dashboard_insight, generate_dashboard_insight
from agents.dashboard_editor import run_dashboard_editor
from agents.dashboard_supervisor import run_dashboard_supervisor
from agents.langchain.engine import invoke_chain
from agents.dashboard_chart_builder import wants_dashboard_chart
from agents.prompt_intent import is_analytical_question, is_dashboard_control_prompt

logger = logging.getLogger(__name__)

_DEFAULT_STATE = {
    "pageTitle": "AI Data Assistant",
    "theme": "light",
    "activeLayout": "focus-mode",
}


def _normalise_state(raw: dict | None) -> dict:
    state = dict(_DEFAULT_STATE)
    if not raw:
        return state
    state["pageTitle"] = (
        raw.get("pageTitle") or raw.get("PageTitle") or state["pageTitle"]
    )
    state["theme"] = raw.get("theme") or raw.get("Theme") or state["theme"]
    state["activeLayout"] = (
        raw.get("activeLayout")
        or raw.get("ActiveLayout")
        or state["activeLayout"]
    )
    return state


def _extract_title(prompt: str) -> str | None:
    patterns = [
        r"title\s+to\s+['\"]([^'\"]+)['\"]",
        r"title\s+to\s+(.+?)(?:\s+and\s+|\s*,\s*|\s*$)",
        r"rename\s+(?:the\s+)?dashboard\s+to\s+['\"]?([^'\"]+)['\"]?",
        r"change\s+(?:the\s+)?title\s+to\s+['\"]?([^'\"]+)['\"]?",
    ]
    for pattern in patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            return match.group(1).strip().rstrip(".")
    return None


def _widget_from_series(
    title: str,
    series: list[dict],
    *,
    chart_type: str = "bar-chart",
) -> dict:
    labels = [str(item.get("name", "")) for item in series[:12]]
    values = []
    for item in series[:12]:
        val = item.get("value")
        try:
            values.append(float(val) if val is not None else 0.0)
        except (TypeError, ValueError):
            values.append(0.0)
    return {
        "id": f"widget-{uuid.uuid4().hex[:8]}",
        "type": chart_type,
        "title": title,
        "renderStatus": "active",
        "labels": labels,
        "values": values,
    }


def _rule_based_mutations(
    prompt: str,
    state: dict,
    aggregates: dict,
    *,
    clear_first: bool = False,
) -> tuple[list[dict], dict, str]:
    """Heuristic mutations from prompt + CSV aggregates."""
    text = prompt.lower()
    mutations: list[dict] = []
    new_state = dict(state)

    if clear_first:
        mutations.append(
            {
                "type": "CLEAR_DASHBOARD",
                "requiresConfirmation": True,
            }
        )

    title = _extract_title(prompt)
    if title:
        new_state["pageTitle"] = title
        mutations.append(
            {
                "action": "update-state",
                "target": "DashboardState.PageTitle",
                "data": title,
            }
        )

    if "dark" in text and "theme" in text:
        new_state["theme"] = "dark"
        mutations.append(
            {
                "action": "update-state",
                "target": "DashboardState.Theme",
                "data": "dark",
            }
        )
    elif "light" in text and "theme" in text:
        new_state["theme"] = "light"
        mutations.append(
            {
                "action": "update-state",
                "target": "DashboardState.Theme",
                "data": "light",
            }
        )

    if "focus" in text and ("layout" in text or "mode" in text):
        new_state["activeLayout"] = "focus-mode"
        mutations.append(
            {
                "action": "update-state",
                "target": "DashboardState.ActiveLayout",
                "data": "focus-mode",
            }
        )
    elif "standard" in text and "layout" in text:
        new_state["activeLayout"] = "standard"
        mutations.append(
            {
                "action": "update-state",
                "target": "DashboardState.ActiveLayout",
                "data": "standard",
            }
        )

    wants_chart = any(
        kw in text
        for kw in (
            "chart",
            "bar chart",
            "graph",
            "visual",
            "plot",
            "generate",
            "show me",
        )
    )

    if wants_chart:
        from agents.dashboard_chart_builder import build_widgets_from_prompt

        widgets = build_widgets_from_prompt(prompt, max_charts=2)
        for widget in widgets:
            mutations.append(
                {
                    "action": "render-widget",
                    "target": "dynamic-widgets-area",
                    "data": widget,
                }
            )

    if mutations:
        reply = "I've updated the dashboard based on your request."
        if title:
            reply = f"Title set to '{title}'."
        if wants_chart and any(m["action"] == "render-widget" for m in mutations):
            reply = "I've generated a chart from your filtered LifeChanger data."
        if clear_first or (mutations and mutations[0]["action"] == "clear-all-widgets"):
            reply = "Dashboard cleared. " + reply
    else:
        reply = (
            "I can change the title, theme, layout, clear widgets, or generate charts "
            "from your data. Try: “Change the title to Q3 Report and show a bar chart by region.”"
        )

    return mutations, new_state, reply


def _llm_orchestrate(
    prompt: str,
    state: dict,
    aggregates: dict,
    fields: dict,
    widget_ids: list[str],
) -> dict | None:
    if not os.environ.get("HF_TOKEN"):
        return None

    context = {
        "currentDashboardState": state,
        "aggregates_summary": {
            "rowCount": aggregates.get("rowCount"),
            "byRegion": (aggregates.get("byRegion") or [])[:6],
            "byWorkshop": (aggregates.get("byWorkshop") or [])[:6],
            "byTheme": (aggregates.get("byTheme") or aggregates.get("inferredThemes") or [])[:6],
        },
        "existingWidgetIds": widget_ids,
        "availableFields": fields,
    }

    system = (
        "You control a LifeChanger analytics dashboard UI. "
        "Respond with ONLY valid JSON (no markdown) matching this schema:\n"
        "{{\n"
        '  "botResponseText": "reply (use 2-3 sentences for questions; short for UI commands)",\n'
        '  "dashboardMutations": [\n'
        '    {{"action": "clear-all-widgets", "target": "dynamic-widgets-area", "data": null}},\n'
        '    {{"action": "update-state", "target": "DashboardState.PageTitle", "data": "string"}},\n'
        '    {{"action": "render-widget", "target": "dynamic-widgets-area", "data": {{"id":"widget-x","type":"bar-chart","title":"...","labels":[],"values":[]}}}}\n'
        "  ],\n"
        '  "dashboardState": {{"pageTitle":"...","theme":"light","activeLayout":"focus-mode"}}\n'
        "}}\n"
        "Use real aggregate numbers from context when building chart labels/values. "
        "Do not invent schools or regions not in context."
    )
    user = f"Context:\n{json.dumps(context, indent=2)}\n\nUser prompt: {prompt}"

    try:
        raw = invoke_chain(system, user, temperature=0.2).strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and parsed.get("botResponseText"):
            return parsed
    except Exception:
        logger.exception("LLM orchestrate JSON parse failed")
    return None


def _attach_supervisor_layers(result: dict, payload: dict) -> dict:
    """Merge LangChain DashboardOrchestrator chains into the API response."""
    prompt = (payload.get("userPrompt") or payload.get("text") or "").strip()
    aggregates = payload.get("aggregates") or {}
    supervisor = run_dashboard_supervisor(
        prompt,
        aggregates,
        use_speaker=bool(payload.get("useSpeaker", True)),
        force=bool(payload.get("storyMode", False)),
    )
    if not supervisor:
        return result

    result["modelFleet"] = supervisor["modelFleet"]
    result["chainsExecuted"] = supervisor["chainsExecuted"]
    result["dashboardLayout"] = supervisor["dashboardLayout"]
    result["visualizations"] = supervisor["visualizations"]
    result["storytellingBlocks"] = supervisor["storytellingBlocks"]
    result["audio"] = supervisor["audio"]

    block = supervisor["storytellingBlocks"][0] if supervisor["storytellingBlocks"] else None
    if block and not result.get("botResponseText"):
        result["botResponseText"] = block.get("narrativeText", "")

    mutations = list(result.get("dashboardMutations") or [])
    chart = supervisor.get("chartConfig")
    if chart:
        mutations.append(
            {
                "action": "render-widget",
                "target": "dynamic-widgets-area",
                "data": chart,
            }
        )
    result["dashboardMutations"] = mutations
    return result


def _merge_editor_result(result: dict, payload: dict) -> dict:
    prompt = (payload.get("userPrompt") or payload.get("text") or "").strip()
    aggregates = payload.get("aggregates") or {}
    fields = payload.get("availableFields") or {}
    current_widgets = payload.get("currentDashboardWidgets") or []

    editor = run_dashboard_editor(prompt, current_widgets, aggregates, fields=fields)
    result["mutations"] = editor.get("mutations") or []
    result["editorIntent"] = editor.get("intent")
    result["currentDashboardState"] = editor.get("currentDashboardState")
    if editor.get("botResponseText") and editor.get("intent") != "ADD":
        result["botResponseText"] = editor["botResponseText"]
    elif editor.get("intent") == "ADD" and not result.get("botResponseText"):
        result["botResponseText"] = editor["botResponseText"]
    elif editor.get("botResponseText") and result.get("source") == "local":
        result["botResponseText"] = editor["botResponseText"]
    return result


def _insight_focus_mutation(suggested_chart: str | None) -> list[dict]:
    if not suggested_chart:
        return []
    chart_ids = {
        "outcome by region": "chart-region",
        "average outcome score by region": "chart-region",
        "sentiment score trend over time": "chart-sentiment",
        "outcome by workshop": "chart-workshop",
        "feedback by theme": "chart-theme",
    }
    widget_id = chart_ids.get((suggested_chart or "").strip().lower(), "chart-region")
    return [
        {
            "action": "focus-widget",
            "targetWidgetId": widget_id,
            "value": {"chart": suggested_chart},
        }
    ]


def _answer_analytical_question(payload: dict, state: dict) -> dict:
    """Conversational Q&A with session memory + dashboard evidence metadata."""
    prompt = (payload.get("userPrompt") or payload.get("text") or "").strip()
    session_id = payload.get("session_id")
    aggregates = payload.get("aggregates") or {}
    fields = payload.get("availableFields") or {}

    insight_payload = {
        "question": prompt,
        "detailed": True,
        "activeFilters": payload.get("activeFilters") or {},
        "aggregates": aggregates,
        "evidenceRows": payload.get("evidenceRows") or [],
        "availableFields": fields,
        "session_id": session_id,
    }

    base = build_local_dashboard_insight(insight_payload)
    answer = base.get("answer") or ""
    source = base.get("source", "local")
    error_message = base.get("errorMessage")

    if os.environ.get("HF_TOKEN") and prompt:
        try:
            from agents.ask_agent import ask_data_question

            ask_result = ask_data_question(prompt, session_id=session_id)
            if ask_result.get("answer"):
                answer = ask_result["answer"]
                source = "langchain"
                error_message = None
        except Exception as exc:
            logger.exception("Conversational ask failed")
            error_message = str(exc)[:300]
            if source == "local":
                answer = (
                    f"{answer}\n\n"
                    f"(LLM note: {error_message}. Check HF_TOKEN and model in backend/.env.)"
                )

    mutations = _insight_focus_mutation(base.get("suggestedChart"))
    return {
        "botResponseText": answer,
        "dashboardMutations": mutations,
        "dashboardState": state,
        "source": source,
        "summaryBullets": base.get("summaryBullets") or [],
        "evidenceReferences": base.get("evidenceReferences") or [],
        "linkedDataPoints": base.get("linkedDataPoints") or [],
        "followUpQuestions": base.get("followUpQuestions") or [],
        "errorMessage": error_message,
        "session_id": session_id,
    }


def orchestrate_llm_command(payload: dict) -> dict:
    """
    Spec response:
      botResponseText, dashboardMutations, dashboardState, source,
      dashboardLayout, visualizations, storytellingBlocks (supervisor),
      mutations (stateful protocol)
    """
    prompt = (payload.get("userPrompt") or payload.get("text") or "").strip()
    state = _normalise_state(payload.get("currentDashboardState"))
    aggregates = payload.get("aggregates") or {}
    fields = payload.get("availableFields") or {}
    widget_ids = payload.get("dynamicWidgetIds") or []

    question_mode = bool(payload.get("questionMode"))
    story_mode = bool(payload.get("storyMode"))
    chart_request = wants_dashboard_chart(prompt) or is_dashboard_control_prompt(prompt)

    if (
        not story_mode
        and (question_mode or is_analytical_question(prompt))
        and not chart_request
    ):
        return _merge_editor_result(
            _answer_analytical_question(payload, state),
            payload,
        )

    if (
        not story_mode
        and is_analytical_question(prompt)
        and chart_request
    ):
        insight_result = _answer_analytical_question(payload, state)
        return _merge_editor_result(
            _attach_supervisor_layers(insight_result, payload),
            payload,
        )

    clear_first = bool(
        re.search(
            r"\b(clear|wipe|reset|start over)\b.*\b(dashboard|canvas|everything|all)\b",
            prompt,
            re.I,
        )
    )

    llm_result = _llm_orchestrate(prompt, state, aggregates, fields, widget_ids)
    if llm_result:
        mutations = llm_result.get("dashboardMutations") or []
        new_state = _normalise_state(llm_result.get("dashboardState") or state)
        for mutation in mutations:
            if mutation.get("action") == "update-state":
                target = mutation.get("target", "")
                val = mutation.get("data") or mutation.get("value")
                if target.endswith("PageTitle"):
                    new_state["pageTitle"] = str(val)
                elif target.endswith("Theme"):
                    new_state["theme"] = str(val)
                elif target.endswith("ActiveLayout"):
                    new_state["activeLayout"] = str(val)
        return _merge_editor_result(
            _attach_supervisor_layers(
                {
                    "botResponseText": llm_result.get("botResponseText", ""),
                    "dashboardMutations": mutations,
                    "dashboardState": new_state,
                    "source": "langchain",
                },
                payload,
            ),
            payload,
        )

    mutations, new_state, reply = _rule_based_mutations(
        prompt, state, aggregates, clear_first=clear_first
    )

    # Enrich reply with insight when no structural mutations
    if not mutations and prompt:
        insight = generate_dashboard_insight(
            {
                "question": prompt,
                "activeFilters": payload.get("activeFilters") or {},
                "aggregates": aggregates,
                "evidenceRows": payload.get("evidenceRows") or [],
                "availableFields": fields,
            }
        )
        reply = insight.get("answer") or reply
        source = insight.get("source", "local")
    else:
        source = "local"

    return _merge_editor_result(
        _attach_supervisor_layers(
            {
                "botResponseText": reply,
                "dashboardMutations": mutations,
                "dashboardState": new_state,
                "source": source,
            },
            payload,
        ),
        payload,
    )
