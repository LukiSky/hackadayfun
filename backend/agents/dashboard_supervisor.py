"""LangChain DashboardOrchestrator — DataVisualization → Storytelling → Audio chains."""

from __future__ import annotations

import json
import logging
import os
import re
import uuid

from agents.chart_service import generate_charts_for_request
from agents.langchain.engine import _model_name, invoke_chain
from agents.personas import persona_for_chat

logger = logging.getLogger(__name__)

# Logical roles mapped to the project's Hugging Face / F5-TTS stack
MODEL_FLEET = {
    "orchestrator": {
        "role": "orchestrator",
        "type": "llm",
        "id": _model_name(),
        "purpose": "Routes the user prompt through visualization, narrative, and audio chains.",
    },
    "data-analyst": {
        "role": "data-analyst",
        "type": "llm",
        "id": _model_name(),
        "purpose": "Extracts aggregate metrics and formats Recharts-ready chart configuration.",
    },
    "storyteller": {
        "role": "storyteller",
        "type": "llm",
        "id": _model_name(),
        "purpose": "Writes engaging narrative insights from chart data.",
    },
    "audio-generator": {
        "role": "audio-generator",
        "type": "tts",
        "id": "f5-tts",
        "purpose": "Converts narrative text to speech via POST /api/tts/speak.",
    },
}


def _pick_series(prompt: str, aggregates: dict) -> tuple[str, list[dict], str]:
    text = prompt.lower()
    by_workshop = aggregates.get("byWorkshop") or []
    by_region = aggregates.get("byRegion") or []
    by_theme = aggregates.get("byTheme") or aggregates.get("inferredThemes") or []
    sentiment = aggregates.get("sentiment") or []

    if "workshop" in text and by_workshop:
        return "Outcome by Workshop", by_workshop, "bar"
    if ("theme" in text or "feedback" in text) and by_theme:
        return "Feedback by Theme", by_theme, "bar"
    if "sentiment" in text or "trend" in text and sentiment:
        return "Sentiment Trend", sentiment, "line"
    if by_region:
        return "Outcome by Region", by_region, "bar"
    if by_workshop:
        return "Workshop Overview", by_workshop, "bar"
    return (
        "Dataset Overview",
        [{"name": "Responses", "value": aggregates.get("rowCount") or 0}],
        "bar",
    )


def run_data_visualization_chain(prompt: str, aggregates: dict) -> dict:
    """Query analytics layer and format chartConfig for Recharts."""
    title, series, chart_kind = _pick_series(prompt, aggregates)
    labels: list[str] = []
    values: list[float] = []
    for item in series[:12]:
        labels.append(str(item.get("name", "")))
        try:
            values.append(float(item.get("value") or 0))
        except (TypeError, ValueError):
            values.append(0.0)

    chart_id = f"viz-{uuid.uuid4().hex[:8]}"
    chart_config = {
        "id": chart_id,
        "type": "line-chart" if chart_kind == "line" else "bar-chart",
        "title": title,
        "labels": labels,
        "values": values,
        "engine": "recharts",
    }

    catalog_charts: list[dict] = []
    try:
        catalog_result = generate_charts_for_request(prompt)
        catalog_charts = catalog_result.get("charts") or []
    except Exception:
        logger.debug("Chart catalog skipped for supervisor", exc_info=True)

    visualization = {
        "id": chart_id,
        "sectionId": "revenue-viz",
        "engine": "recharts",
        "chartConfig": chart_config,
        "catalogCharts": catalog_charts[:2],
    }
    return {"chartConfig": chart_config, "visualization": visualization}


def run_storytelling_chain(prompt: str, chart_config: dict, aggregates: dict) -> str:
    """Narrative from chart data — StorytellingChain."""
    context = {
        "user_prompt": prompt,
        "chart": chart_config,
        "row_count": aggregates.get("rowCount"),
        "avg_outcome": aggregates.get("avgImprovement"),
    }
    persona = persona_for_chat()
    system = (
        f"{persona}\n\n"
        "You are the StorytellingChain agent. Analyze the chart JSON and write exactly "
        "2 short paragraphs explaining trends for LifeChanger workshop impact data. "
        "Tone: warm, engaging, easy to read aloud. Use only numbers present in the chart."
    )
    user = f"Chart data:\n{json.dumps(context, indent=2)}"

    if os.environ.get("HF_TOKEN"):
        try:
            return invoke_chain(system, user, temperature=0.4).strip()
        except Exception:
            logger.exception("StorytellingChain LLM failed")

    labels = chart_config.get("labels") or []
    values = chart_config.get("values") or []
    if labels and values:
        top_idx = max(range(len(values)), key=lambda i: values[i])
        lead = labels[top_idx]
        lead_val = values[top_idx]
        return (
            f"The data highlights {lead} as a leading segment with an average outcome "
            f"score of {lead_val:.2f}. Across {aggregates.get('rowCount', 0)} filtered "
            f"responses, patterns reflect how students and schools are experiencing "
            f"LifeChanger workshops.\n\n"
            f"When you listen to this insight, remember it is grounded in de-identified "
            f"CSV evidence from the active dashboard filters—not generic benchmarks."
        )
    return (
        "The current filtered view does not contain enough chart data to build a detailed "
        "story. Adjust filters on the left or ask for a specific region, workshop, or theme."
    )


def run_audio_chain(narrative_text: str, *, use_speaker: bool) -> dict:
    """
    AudioChain — narrative is returned for client-side F5-TTS playback.
    Server does not embed binary audio in JSON; frontend calls /api/tts/speak.
    """
    return {
        "audioStreamId": "revenue-audio-stream",
        "narrativeText": narrative_text,
        "useSpeaker": use_speaker,
        "audioUrl": None,
        "preload": "auto",
        "provider": MODEL_FLEET["audio-generator"]["id"],
    }


def regenerate_story_for_detail(
    detail_level: str,
    aggregates: dict,
    *,
    chart_config: dict | None = None,
    user_prompt: str | None = None,
) -> dict:
    """Re-run StorytellingChain with Summary / Standard / Deep Dive length."""
    level = detail_level or "Standard"
    chart = chart_config or run_data_visualization_chain(
        user_prompt or "workshop outcomes", aggregates
    )["chartConfig"]

    length_guide = {
        "Summary": "Write exactly 1 concise paragraph (3-4 sentences).",
        "Standard": "Write exactly 2 engaging paragraphs.",
        "Deep Dive": "Write 3-4 paragraphs with specific data points and implications.",
    }.get(level, "Write exactly 2 engaging paragraphs.")

    context = {
        "detail_level": level,
        "chart": chart,
        "row_count": aggregates.get("rowCount"),
        "user_prompt": user_prompt,
    }
    persona = persona_for_chat()
    system = (
        f"{persona}\n\n"
        "You are the StorytellingChain agent regenerating narrative for the dashboard. "
        f"{length_guide} Use only numbers from the chart JSON."
    )
    user = f"Context:\n{json.dumps(context, indent=2)}"

    if os.environ.get("HF_TOKEN"):
        try:
            narrative = invoke_chain(system, user, temperature=0.35).strip()
            if narrative:
                return {
                    "narrativeText": narrative,
                    "detailLevel": level,
                    "source": "langchain",
                    "chartConfig": chart,
                }
        except Exception:
            logger.exception("Story regeneration failed")

    base_narrative = run_storytelling_chain(
        user_prompt or f"Detail level {level}", chart, aggregates
    )
    return {
        "narrativeText": base_narrative,
        "detailLevel": level,
        "source": "local",
        "chartConfig": chart,
    }


def _wants_story_dashboard(prompt: str) -> bool:
    text = prompt.lower()
    return bool(
        re.search(
            r"\b(story|stories|narrative|tell me|insight|read aloud|listen|"
            r"revenue|q3|quarter|explain the trend)\b",
            text,
        )
    )


def run_dashboard_supervisor(
    prompt: str,
    aggregates: dict,
    *,
    use_speaker: bool = True,
    force: bool = False,
) -> dict | None:
    """
    Full LangChain supervisor output:
    dashboardLayout, visualizations, storytellingBlocks, modelFleet, audio
    """
    if not force and not _wants_story_dashboard(prompt):
        return None

    viz_chain = run_data_visualization_chain(prompt, aggregates)
    chart_config = viz_chain["chartConfig"]
    narrative = run_storytelling_chain(prompt, chart_config, aggregates)
    audio = run_audio_chain(narrative, use_speaker=use_speaker)

    storytelling_block = {
        "id": f"story-{uuid.uuid4().hex[:8]}",
        "sectionId": "revenue-story",
        "title": "Key Insights",
        "narrativeText": narrative,
        "audioStreamId": audio["audioStreamId"],
        "playbackLabel": "Listen to Insight",
        "chartRef": chart_config["id"],
    }

    return {
        "modelFleet": MODEL_FLEET,
        "chainsExecuted": [
            "DataVisualizationChain",
            "StorytellingChain",
            "AudioChain",
        ],
        "dashboardLayout": [
            {
                "id": "story-driven-dashboard",
                "type": "story-driven-dashboard",
                "sections": ["revenue-viz", "revenue-story"],
            }
        ],
        "visualizations": [viz_chain["visualization"]],
        "storytellingBlocks": [storytelling_block],
        "audio": audio,
        "chartConfig": chart_config,
    }
