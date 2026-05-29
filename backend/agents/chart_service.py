"""Chart selection and LLM-assisted visualization for Ask + dedicated chart API."""

from __future__ import annotations

import json
import re

from agents.langchain.engine import invoke_chain as _invoke_chain
from agents.personas import persona_for_visualization
from data.chart_catalog import build_chart_catalog, chart_catalog_index, get_charts_by_ids
from data.prediction import build_prediction_charts
from data.repository import MockDataRepository

_repo = MockDataRepository()

# Keywords → chart ids (order = priority)
_CHART_KEYWORDS: list[tuple[str, list[str]]] = [
    (r"\b(sentiment|positive|negative|mixed|feeling)\b", ["sentiment_distribution"]),
    (r"\b(theme|topics?|pillar|health|tribe|skills|self|purpose)\b", ["top_themes", "workshop_topics_volume"]),
    (r"\b(attendance|show up|participat)\b", ["programs_attendance", "attendance_over_time"]),
    (r"\b(wellbeing|well-being|mental|stress)\b", ["programs_wellbeing", "wellbeing_over_time"]),
    (r"\b(facilitator|mentor|rating|trainer)\b", ["programs_facilitator_rating"]),
    (r"\b(question|survey|answer value|scale)\b", ["question_response_volume", "question_avg_scores"]),
    (r"\b(region|geograph|state|location)\b", ["responses_by_region"]),
    (r"\b(year level|grade|cohort)\b", ["responses_by_year_level"]),
    (r"\b(heartwarm|story|quote)\b", ["heartwarming_share"]),
    (r"\b(compromis|deviat|risk|delivery|quality issue)\b", ["workshop_delivery_flags"]),
    (r"\b(overview|summary|dashboard|kpi|how many)\b", ["kpi_overview"]),
    (r"\b(trend|over time|term|quarter|timeline)\b", ["attendance_over_time", "wellbeing_over_time"]),
    (r"\b(compare|comparison|program)\b", ["programs_attendance", "programs_wellbeing"]),
    (
        r"\b(predict|forecast|machine learning|ml|model|probability|feature importance)\b",
        [
            "ml_predicted_vs_actual",
            "ml_risk_probability_by_topic",
            "ml_wellbeing_forecast",
            "ml_feature_importance",
        ],
    ),
]

_VISUAL_INTENT = re.compile(
    r"\b(chart|graph|plot|visuali[sz]e|visual|bar chart|pie chart|line chart|"
    r"power\s*bi|powerbi|dashboard view|show me a|draw a|display a)\b",
    re.I,
)


def _catalog() -> list[dict]:
    raw = _repo.load_dataset()
    analytics = _repo.get_analytics()
    charts = build_chart_catalog(analytics, raw)
    predictions = _repo.get_predictions()
    charts.extend(build_prediction_charts(predictions))
    return charts


def list_all_charts() -> dict:
    charts = _catalog()
    return {
        "charts": charts,
        "index": chart_catalog_index(charts),
        "count": len(charts),
    }


def _keyword_chart_ids(question: str, *, max_charts: int = 3) -> list[str]:
    q = question.lower()
    ids: list[str] = []
    for pattern, chart_ids in _CHART_KEYWORDS:
        if re.search(pattern, q, re.I):
            for cid in chart_ids:
                if cid not in ids:
                    ids.append(cid)
        if len(ids) >= max_charts:
            break
    return ids[:max_charts]


def _llm_pick_chart_ids(question: str, index: list[dict], *, max_charts: int = 2) -> list[str]:
    system_prompt = persona_for_visualization()
    system_prompt += (
        f"\n\nTask constraint: Return STRICT JSON only: {{\"chart_ids\": [\"id1\"]}}. "
        f"Use at most {max_charts} chart IDs. Only use IDs from the catalog."
    )
    user_prompt = (
        f"Question: {question}\n\n"
        f"Chart catalog:\n{json.dumps(index, indent=2)}\n\n"
        "If the user wants a chart/graph/visual, pick the most relevant IDs. "
        "If no chart fits, return {\"chart_ids\": []}."
    )
    try:
        raw = _invoke_chain(system_prompt, user_prompt, temperature=0.1)
        start = raw.find("{")
        end = raw.rfind("}")
        parsed = json.loads(raw[start : end + 1]) if start >= 0 else {}
        ids = parsed.get("chart_ids", [])
        valid = {c["id"] for c in index}
        return [i for i in ids if i in valid][:max_charts]
    except Exception:
        return []


def select_charts_for_question(question: str, *, max_charts: int = 3) -> list[dict]:
    """Rule-based + optional LLM chart selection."""
    charts = _catalog()
    index = chart_catalog_index(charts)
    q = question.strip()

    wants_visual = bool(_VISUAL_INTENT.search(q))
    ids = _keyword_chart_ids(q, max_charts=max_charts)

    if wants_visual and len(ids) < max_charts:
        llm_ids = _llm_pick_chart_ids(q, index, max_charts=max_charts)
        for cid in llm_ids:
            if cid not in ids:
                ids.append(cid)

    if not ids and wants_visual:
        ids = _llm_pick_chart_ids(q, index, max_charts=max_charts) or ["kpi_overview", "sentiment_distribution"]

    if not ids and _keyword_chart_ids(q, max_charts=1):
        ids = _keyword_chart_ids(q, max_charts=max_charts)

    if wants_visual and not ids:
        ids = ["kpi_overview"]

    return get_charts_by_ids(charts, ids)


def generate_charts_for_request(question: str, chart_type: str | None = None) -> dict:
    """Explicit chart generation (Power BI–style request)."""
    charts = select_charts_for_question(question, max_charts=4)
    if chart_type:
        charts = [c for c in charts if c["type"] == chart_type] or charts[:1]
    return {
        "question": question,
        "charts": charts,
        "chart_count": len(charts),
        "framework": "chart_catalog+langchain",
    }


def attach_charts_to_ask(
    question: str,
    ask_result: dict,
    *,
    mode: str = "both",
    max_charts: int = 3,
) -> dict:
    """Merge visualization payloads into chat/ask responses."""
    ask_result = dict(ask_result)
    mode = (mode or "both").lower()

    if mode == "qa":
        ask_result["charts"] = []
        ask_result["has_visualizations"] = False
        return ask_result

    charts = select_charts_for_question(question, max_charts=max_charts)
    wants_visual = bool(_VISUAL_INTENT.search(question)) or mode == "charts"

    if mode == "charts" and not charts:
        charts = select_charts_for_question(question, max_charts=4) or get_charts_by_ids(
            _catalog(), ["kpi_overview", "sentiment_distribution"]
        )

    if mode == "both" and not charts and not wants_visual:
        ids = _keyword_chart_ids(question, max_charts=1)
        if ids:
            charts = get_charts_by_ids(_catalog(), ids)

    ask_result["charts"] = charts
    ask_result["has_visualizations"] = len(charts) > 0
    if charts:
        ask_result["visualization_note"] = (
            f"I've pulled together {len(charts)} chart(s) from the workshop data — take a look below."
        )
    return ask_result


def chart_summaries_for_llm(charts: list[dict]) -> str:
    lines = []
    for c in charts:
        top = (c.get("data") or [])[:3]
        preview = ", ".join(f"{d.get('label')}: {d.get('value')}" for d in top)
        lines.append(f"- {c.get('title')} ({c.get('type')}): {preview}")
    return "\n".join(lines) if lines else "No charts selected."
