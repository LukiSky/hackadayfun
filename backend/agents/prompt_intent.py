"""Classify chat prompts: analytical questions vs dashboard control commands."""

from __future__ import annotations

import re

_DASHBOARD_CONTROL_PATTERNS = [
    r"\b(add_widget|update_widget|delete_widget|clear_dashboard)\b",
    r"\b(regenerate|re-generate)\s+(the\s+)?dashboard\b",
    r"\b(build|create|generate)\s+(a\s+)?(detailed\s+)?(executive\s+)?dashboard\b",
    r"\b(append|add)\s+(a\s+)?(pie|bar|line)\s+chart\b",
    r"\bchange\s+(the\s+)?(title|theme|layout)\b",
    r"\bset\s+(page\s+)?title\s+to\b",
    r"\bclear\s+(the\s+)?(dashboard|canvas|widgets)\b",
    r"\b(story\s+mode|storytelling\s+blocks?)\b",
    r"\bpage\s+title\s*:",
    r"\bkeep\s+existing\s+default\s+widgets\b",
    r"\bdefault_to_append\b",
]

_QUESTION_PATTERNS = [
    r"\?",
    r"^\s*(which|what|who|how|why|when|where)\b",
    r"\b(which|what|who|how|why|when|where)\s+\w+",
    r"\b(best|worst|strongest|weakest|leading|lagging|underperforming)\b",
    r"\b(compare|comparison|versus|vs\.?)\b",
    r"\b(tell me|explain|describe|summarize|summary of)\b",
    r"\b(how many|how much|what is the|what are the)\b",
]


def is_dashboard_control_prompt(prompt: str) -> bool:
    text = (prompt or "").strip().lower()
    if not text:
        return False
    if len(text) > 350 and any(
        kw in text
        for kw in (
            "add_widget",
            "update_widget",
            "regenerate the dashboard",
            "demo regeneration",
            "default_to_append",
        )
    ):
        return True
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in _DASHBOARD_CONTROL_PATTERNS)


_CHART_IN_QUESTION = re.compile(
    r"\b(add|show|create|generate|plot|draw|build|make|display)\b.*\b(chart|graph|visual|pie|bar|line|kpi)\b"
    r"|\b(chart|graph)\b.*\b(by|of|for|showing)\b"
    r"|\b(bar|line|pie|donut)\s+chart\b"
    r"|\bvisuali[sz]e\b",
    re.I,
)


def is_analytical_question(prompt: str) -> bool:
    text = (prompt or "").strip()
    if not text or is_dashboard_control_prompt(text):
        return False
    if _CHART_IN_QUESTION.search(text):
        return False
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in _QUESTION_PATTERNS)
