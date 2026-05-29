"""Deterministic LangChain tools — bypass LLM for facts and calculations."""

from __future__ import annotations

import json

from langchain_core.tools import tool

from agents.risk_opportunity import identify_risks_and_opportunities
from data.repository import MockDataRepository

_repo = MockDataRepository()


@tool
def get_dataset_metrics() -> str:
    """Return core quantitative metrics: responses, workshops, schools, ratings, sentiment."""
    a = _repo.get_analytics()
    s = a["summary"]
    meta = a.get("meta", {})
    payload = {
        "valid_responses": s.get("valid_responses"),
        "total_workshops": s.get("total_workshops") or s.get("total_sessions"),
        "total_schools": s.get("total_schools") or s.get("unique_schools"),
        "total_participants": s.get("total_participants"),
        "avg_answer_value": s.get("avg_answer_value"),
        "avg_facilitator_rating": s.get("avg_facilitator_rating"),
        "heartwarming_count": s.get("heartwarming_count"),
        "at_risk_topics": s.get("at_risk_count"),
        "sentiment_distribution": a.get("sentiment_distribution"),
        "top_themes": a.get("top_themes", [])[:5],
        "source_format": meta.get("source_format"),
    }
    return json.dumps(payload, indent=2)


@tool
def get_risk_and_warning_signals() -> str:
    """Return program risks, early warnings, and compromised/deviated workshops."""
    a = _repo.get_analytics()
    risks = identify_risks_and_opportunities()
    payload = {
        "risks": risks.get("risks", [])[:10],
        "opportunities": risks.get("opportunities", [])[:5],
        "early_warnings": a.get("early_warnings", [])[:10],
    }
    return json.dumps(payload, indent=2)


@tool
def get_workshop_outcome_rankings() -> str:
    """Return best and lowest performing workshops by composite score."""
    a = _repo.get_analytics()
    return json.dumps(a.get("workshop_outcomes", {}), indent=2)


@tool
def get_correlation_insights() -> str:
    """Return condition–outcome association insights (facilitator rating vs student scores)."""
    a = _repo.get_analytics()
    return json.dumps(a.get("correlations", []), indent=2)


@tool
def search_feedback_context(query: str, limit: int = 8) -> str:
    """Search student feedback quotes by keyword overlap (fast local retrieval)."""
    from agents.langchain.retriever import search_feedback

    docs = search_feedback(query, k=min(limit, 15))
    return json.dumps(docs, indent=2)


IMPACTLENS_TOOLS = [
    get_dataset_metrics,
    get_risk_and_warning_signals,
    get_workshop_outcome_rankings,
    get_correlation_insights,
    search_feedback_context,
]
