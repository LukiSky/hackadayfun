"""RunnableBranch-style fast query router (keyword classifier)."""

from __future__ import annotations

import re
from enum import Enum


class QueryRoute(str, Enum):
    METRICS = "metrics"  # instant tool path
    RISK = "risk"
    CHART = "chart"
    WORKSHOP = "workshop"
    STORY = "story"
    GENERAL = "general"


_ROUTE_PATTERNS: list[tuple[QueryRoute, re.Pattern]] = [
    (QueryRoute.CHART, re.compile(r"\b(chart|graph|plot|visuali|power\s*bi|dashboard)\b", re.I)),
    (QueryRoute.RISK, re.compile(r"\b(risk|at[- ]?risk|underperform|warning|compromis|deviat|flag)\b", re.I)),
    (QueryRoute.WORKSHOP, re.compile(r"\b(best|worst|top|lowest)\b.*\b(workshop|outcome|term)\b", re.I)),
    (QueryRoute.WORKSHOP, re.compile(r"\bwhich workshops?\b", re.I)),
    (QueryRoute.STORY, re.compile(r"\b(story|narrative|tell me about a student)\b", re.I)),
    (
        QueryRoute.METRICS,
        re.compile(
            r"\b(how many|count|total|average|avg|number of|percent|%)"
            r".*\b(response|workshop|school|student|participant|sentiment|rating)\b",
            re.I,
        ),
    ),
    (
        QueryRoute.METRICS,
        re.compile(r"^(how many|what is the total|what are the totals)\b", re.I),
    ),
]


def classify_route(question: str) -> QueryRoute:
    q = question.strip()
    for route, pattern in _ROUTE_PATTERNS:
        if pattern.search(q):
            return route
    return QueryRoute.GENERAL
