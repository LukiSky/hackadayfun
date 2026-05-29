"""Classify user prompts for dashboard orchestration."""

from __future__ import annotations

import re

CHART_VERBS = re.compile(
    r"\b(add|create|generate|show|build|make|plot|draw|display|put)\b.*\b(chart|graph|visual|widget|kpi)\b"
    r"|\b(chart|graph|visual|widget)\b.*\b(by|for|of|showing)\b"
    r"|\b(bar|line|pie)\s+chart\b",
    re.I,
)
EDIT_VERBS = re.compile(
    r"\b(change|update|edit|rename|modify|set)\b.*\b(chart|widget|title|type)\b"
    r"|\b(make|turn)\b.*\b(pie|bar|line)\b",
    re.I,
)
DELETE_VERBS = re.compile(
    r"\b(delete|remove|drop)\b.*\b(chart|widget)\b|\bclear\b.*\b(dashboard|widgets|charts)\b",
    re.I,
)
QUESTION_MARKERS = re.compile(
    r"\?|^(what|which|who|when|where|why|how|is|are|can|could|should|tell me|explain)\b",
    re.I,
)


def wants_chart(prompt: str) -> bool:
    return bool(CHART_VERBS.search(prompt))


def wants_edit(prompt: str) -> bool:
    return bool(EDIT_VERBS.search(prompt))


def wants_delete(prompt: str) -> bool:
    return bool(DELETE_VERBS.search(prompt))


def is_analytical_question(prompt: str) -> bool:
    if wants_chart(prompt) or wants_edit(prompt) or wants_delete(prompt):
        return False
    return bool(QUESTION_MARKERS.search(prompt.strip()))


def orchestration_mode(prompt: str) -> str:
    """Returns: clear | delete | edit | add_chart | question | dashboard_control."""
    lower = prompt.lower().strip()
    if re.search(r"\bclear\b.*\b(all|dashboard|everything|widgets)\b", lower):
        return "clear"
    if wants_delete(prompt):
        return "delete"
    if wants_edit(prompt):
        return "edit"
    if wants_chart(prompt):
        return "add_chart"
    if is_analytical_question(prompt):
        return "question"
    if re.search(r"\b(dashboard|layout|theme|title)\b", lower):
        return "dashboard_control"
    return "add_chart" if re.search(r"\b(chart|graph|visual|kpi)\b", lower) else "question"
