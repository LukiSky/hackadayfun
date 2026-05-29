"""Dashboard insight responses for the hackathon frontend (POST /api/insights)."""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

from agents.langchain.engine import invoke_chain
from agents.personas import persona_for_chat


def _format_number(value) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(number - round(number)) < 0.01:
        return f"{int(round(number)):,}"
    return f"{number:,.2f}"


def _format_outcome_score(value) -> str:
    if value is None:
        return "not available"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def _evidence_label(row: dict, fields: dict) -> str:
    for key in ("feedback", "theme", "workshop"):
        column = fields.get(key)
        if column and row.get(column):
            text = str(row[column]).strip()
            if text:
                return text[:160]
    return "CSV evidence row"


def build_local_dashboard_insight(payload: dict) -> dict:
    """Mirror the frontend createLocalInsight() response shape."""
    question = (payload.get("question") or "").strip()
    aggregates = payload.get("aggregates") or {}
    filters = payload.get("activeFilters") or payload.get("filters") or {}
    evidence_rows = payload.get("evidenceRows") or []
    fields = payload.get("availableFields") or payload.get("fields") or {}

    active_filters = [
        f"{key}: {value}"
        for key, value in filters.items()
        if value and value != "All"
    ]
    filter_text = ", ".join(active_filters) if active_filters else "all records"

    by_region = aggregates.get("byRegion") or []
    by_workshop = aggregates.get("byWorkshop") or []
    by_theme = aggregates.get("byTheme") or []
    outcome = aggregates.get("outcome") or {}

    strongest_region = by_region[0] if by_region else None
    strongest_workshop = by_workshop[0] if by_workshop else None
    strongest_theme = by_theme[0] if by_theme else None
    strongest_value = strongest_region or strongest_workshop

    row_count = aggregates.get("rowCount") or 0
    avg_improvement = aggregates.get("avgImprovement")
    has_pre_post = bool(fields.get("preScore") and fields.get("postScore"))
    metric_label = "average uplift" if has_pre_post else "average outcome score"
    metric_value_text = _format_outcome_score(avg_improvement)

    valid_rows = outcome.get("validRows") or 0
    excluded_rows = outcome.get("excludedRows") or 0
    formula_label = outcome.get("formulaLabel") or "Outcome formula not detected"
    has_valid_data = bool(outcome.get("hasValidData"))

    if has_valid_data:
        metric_evidence = (
            f"{valid_rows} valid outcome rows; {excluded_rows} excluded. "
            f"Formula: {formula_label}."
        )
    else:
        metric_evidence = (
            f"No valid outcome score data was detected for this filtered view. "
            f"Formula checked: {formula_label}."
        )

    evidence_label = (
        f"{len(evidence_rows)} visible evidence rows" if evidence_rows else "the filtered CSV rows"
    )
    top_evidence = evidence_rows[0] if evidence_rows else None

    if question:
        lead = strongest_region["name"] if strongest_region else (
            strongest_workshop["name"] if strongest_workshop else "the current segment"
        )
        score_part = ""
        if has_valid_data and strongest_value:
            score_part = (
                f", with an {metric_label} of "
                f"{_format_outcome_score(strongest_value.get('value', avg_improvement))}"
            )
        answer = (
            f"Based on {filter_text}, the dataset points to {lead} as the best-performing area"
            f"{score_part}. This answer is grounded in {_format_number(row_count)} CSV rows and "
            f"{evidence_label}. {metric_evidence}"
        )
    else:
        region_part = (
            f"{strongest_region['name']} leading the region view"
            if strongest_region
            else "regional comparison unavailable"
        )
        score_sentence = (
            f"The {metric_label} is {metric_value_text}"
            if has_valid_data
            else metric_value_text
        )
        answer = (
            f"The current view covers {_format_number(row_count)} CSV rows. "
            f"{score_sentence}, with {region_part}. {metric_evidence}"
        )

    summary_bullets = [
        f"{_format_number(row_count)} source rows match the active filters.",
    ]
    if has_valid_data:
        summary_bullets.append(
            f"The {metric_label} is {metric_value_text}, using "
            f"{_format_number(valid_rows)} valid CSV rows."
        )
    else:
        summary_bullets.append("No valid outcome score data exists for the active filters.")
    summary_bullets.append(
        f"{_format_number(excluded_rows)} rows were excluded from Outcome Score because "
        "values were missing or invalid."
    )
    if strongest_workshop:
        summary_bullets.append(
            f"{strongest_workshop['name']} is the strongest workshop segment."
        )
    else:
        summary_bullets.append("Workshop field was not detected in the CSV.")
    if strongest_theme:
        summary_bullets.append(
            f"{strongest_theme['name']} is the most common feedback theme."
        )
    else:
        summary_bullets.append("Theme field was not detected in the CSV.")

    evidence_references = []
    for index, row in enumerate(evidence_rows[:4]):
        row_number = row.get("__rowNumber") or index + 1
        evidence_references.append(
            {
                "id": index + 1,
                "href": f"#evidence-row-{row_number}",
                "label": _evidence_label(row, fields),
            }
        )

    linked_data_points = []
    if strongest_value:
        linked_data_points.append(
            {
                "label": (
                    f"{strongest_value['name']}: "
                    f"{_format_outcome_score(strongest_value.get('value'))}"
                ),
                "href": "#chart-region",
            }
        )
    if has_valid_data:
        first_outcome_row = (outcome.get("evidenceRows") or [{}])[0]
        row_number = first_outcome_row.get("__rowNumber")
        linked_data_points.append(
            {
                "label": f"{_format_number(valid_rows)} valid outcome rows",
                "href": f"#evidence-row-{row_number}" if row_number else "#evidence-table",
            }
        )
    linked_data_points.append(
        {
            "label": f"{_format_number(row_count)} matching CSV rows",
            "href": (
                f"#evidence-row-{top_evidence.get('__rowNumber', 1)}"
                if top_evidence
                else "#evidence-table"
            ),
        }
    )

    return {
        "answer": answer,
        "summaryBullets": summary_bullets,
        "suggestedChart": "Outcome by region" if fields.get("region") else "Outcome by workshop",
        "evidenceReferences": evidence_references,
        "linkedDataPoints": linked_data_points,
        "followUpQuestions": [
            "Which segment has the strongest improvement?",
            "What themes appear most often?",
            "Which records need follow-up?",
        ],
        "source": "local",
    }


def _llm_dashboard_insight(payload: dict, base: dict) -> dict | None:
    question = (payload.get("question") or "").strip()
    if not question or not os.environ.get("HF_TOKEN"):
        return None

    aggregates = payload.get("aggregates") or {}
    filters = payload.get("activeFilters") or {}
    evidence_rows = payload.get("evidenceRows") or []
    fields = payload.get("availableFields") or payload.get("fields") or {}
    outcome = aggregates.get("outcome") or {}
    detailed = bool(payload.get("detailed") or payload.get("mode") == "detailed")

    context = {
        "question": question,
        "filters": filters,
        "row_count": aggregates.get("rowCount"),
        "feedback_rows": aggregates.get("feedbackRows"),
        "avg_outcome": aggregates.get("avgImprovement"),
        "outcome_formula": outcome.get("formulaLabel"),
        "outcome_valid_rows": outcome.get("validRows"),
        "outcome_excluded_rows": outcome.get("excludedRows"),
        "has_valid_outcome_data": outcome.get("hasValidData"),
        "by_region": (aggregates.get("byRegion") or [])[:8],
        "by_workshop": (aggregates.get("byWorkshop") or [])[:8],
        "by_school": (aggregates.get("bySchool") or [])[:6],
        "by_participant_group": (aggregates.get("byParticipantGroup") or [])[:6],
        "themes": (aggregates.get("inferredThemes") or aggregates.get("byTheme") or [])[:8],
        "sentiment_breakdown": aggregates.get("sentimentBreakdown") or [],
        "warning_signals": aggregates.get("warningSignals") or [],
        "detected_fields": {k: v for k, v in fields.items() if v},
        "evidence_samples": [
            {
                "row": row.get("__rowNumber"),
                "snippet": _evidence_label(row, fields),
            }
            for row in evidence_rows[:6]
        ],
    }

    persona = persona_for_chat()
    if detailed:
        length_rule = (
            "Write a detailed, helpful explanation in 2–4 short paragraphs (about 120–220 words).\n"
            "Structure your answer:\n"
            "1) Direct answer to the question with specific numbers from context.\n"
            "2) How the active filters shape this view.\n"
            "3) Compare the top 1–2 segments (region, workshop, or theme) when relevant.\n"
            "4) One sentence on evidence limits (valid vs excluded outcome rows) if outcome data exists.\n"
            "5) What chart or filter on the dashboard the user should check next.\n"
            "Use plain English. Do not invent regions, schools, or statistics not in the JSON."
        )
    else:
        length_rule = (
            "Keep answers to 3–5 sentences. Do not invent numbers."
        )

    system_prompt = (
        f"{persona}\n\n"
        "You are the ImpactLensAI analytics copilot for LifeChanger workshop CSV data.\n"
        "Answer in warm, professional, evidence-backed language.\n"
        "Use only the JSON context provided. Mention active filters when relevant.\n"
        f"{length_rule}"
    )
    user_prompt = (
        f"Context:\n{json.dumps(context, indent=2)}\n\nQuestion: {question}"
    )

    try:
        answer = invoke_chain(system_prompt, user_prompt, temperature=0.35).strip()
        if not answer:
            return None
        enriched = dict(base)
        enriched["answer"] = answer
        enriched["source"] = "langchain"
        return enriched
    except Exception as exc:
        logger.exception("Dashboard insight LLM failed")
        if os.environ.get("HF_TOKEN"):
            enriched = dict(base)
            enriched["source"] = "error"
            enriched["errorMessage"] = str(exc)[:300]
            return enriched
        return None


def generate_dashboard_insight(payload: dict) -> dict:
    """Primary handler for POST /api/insights from the React dashboard."""
    base = build_local_dashboard_insight(payload)
    llm_result = _llm_dashboard_insight(payload, base)
    result = llm_result or base
    if payload.get("detailed") and result.get("source") == "local" and (
        payload.get("question") or ""
    ).strip():
        result["answer"] = (
            f"{base['answer']}\n\n"
            "Open the region and workshop charts in the Main Analysis Panel "
            "to compare segments visually. Use Evidence Used below for CSV row links."
        )
    return result
