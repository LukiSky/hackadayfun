"""Load and clean LifeChanger Salesforce-style workshop CSV (PRD schema)."""

from __future__ import annotations

import csv
from pathlib import Path

REQUIRED_FIELDS = (
    "SUBMISSION_ID",
    "QUESTION_TEXT",
    "ANSWER_TEXT",
    "WORKSHOP_CODE",
    "SCHOOL_NAME",
)


def _strip(value: str | None) -> str:
    return (value or "").strip()


def _parse_bool(value: str | None) -> bool:
    text = _strip(value).upper()
    if text in {"TRUE", "YES", "Y", "1"}:
        return True
    if text in {"FALSE", "NO", "N", "0", "NOT APPLICABLE", "N/A", ""}:
        return False
    return False


def _parse_float(value: str | None) -> float | None:
    text = _strip(value)
    if not text:
        return None
    text = text.replace("$", "").replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def _parse_int(value: str | None) -> int | None:
    num = _parse_float(value)
    if num is None:
        return None
    return int(num)


def _is_valid_row(row: dict[str, str]) -> bool:
    return all(_strip(row.get(field)) for field in REQUIRED_FIELDS)


def load_lifechanger_csv(path: Path | str) -> dict:
    """Return normalized dataset package for analytics layer."""
    path = Path(path)
    responses: list[dict] = []

    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not _is_valid_row(row):
                continue
            answer_value = _parse_float(row.get("ANSWER_VALUE"))
            responses.append(
                {
                    "submission_id": _strip(row.get("SUBMISSION_ID")),
                    "question_id": _strip(row.get("QUESTION_ID")),
                    "question_text": _strip(row.get("QUESTION_TEXT")),
                    "answer_text": _strip(row.get("ANSWER_TEXT")),
                    "answer_value": answer_value,
                    "submitted_on": _strip(row.get("SUBMITTED_ON")),
                    "heartwarming": _parse_bool(row.get("HEARTWARMING")),
                    "workshop_code": _strip(row.get("WORKSHOP_CODE")),
                    "workshop_sf_id": _strip(row.get("WORKSHOP_SF_ID")),
                    "workshop_topic": _strip(row.get("WORKSHOP_TOPIC")),
                    "workshop_region": _strip(row.get("WORKSHOP_REGION")),
                    "workshop_location": _strip(row.get("WORKSHOP_LOCATION")),
                    "workshop_date": _strip(row.get("WORKSHOP_DATE")),
                    "year_level": _strip(row.get("YEAR_LEVEL")),
                    "school_name": _strip(row.get("SCHOOL_NAME")),
                    "school_state": _strip(row.get("SCHOOL_STATE")),
                    "school_region": _strip(row.get("SCHOOL_REGION")),
                    "school_icsea_percentile": _parse_float(row.get("SCHOOL_ICSEA_PERCENTILE")),
                    "school_enrolments": _parse_int(row.get("SCHOOL_NUMBER_OF_ENROLEMENTS")),
                    "school_agreement_amount": _parse_float(row.get("SCHOOL_AGREEMENT_AMOUNT")),
                    "number_of_students": _parse_int(row.get("NUMBER_OF_STUDENTS")) or 0,
                    "facilitator_rating": _parse_float(row.get("FACILITATOR_WORKSHOP_RATING")),
                    "was_compromised": _parse_bool(row.get("WAS_WORKSHOP_COMPROMISED")),
                    "if_compromised": _strip(row.get("IF_COMPROMISED_WHAT_HAPPENED")),
                    "did_deviate": _parse_bool(row.get("DID_WORKSHOP_DEVIATE")),
                    "if_deviated": _strip(row.get("IF_DEVIATED_WHAT_WAS_DIFFERENT")),
                    "workshop_gems": _strip(row.get("WORKSHOP_GEMS")),
                    "anything_else": _strip(row.get("ANYTHING_ELSE_TO_NOTE")),
                }
            )

    # Workshop-level session records (one per WORKSHOP_CODE) for existing analytics shape
    by_workshop: dict[str, list[dict]] = {}
    for row in responses:
        by_workshop.setdefault(row["workshop_code"], []).append(row)

    sessions: list[dict] = []
    for workshop_code, rows in by_workshop.items():
        first = rows[0]
        answer_values = [r["answer_value"] for r in rows if r["answer_value"] is not None]
        avg_answer = sum(answer_values) / len(answer_values) if answer_values else None
        ratings = [r["facilitator_rating"] for r in rows if r["facilitator_rating"] is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else None
        students = max((r["number_of_students"] for r in rows), default=0)

        feedback_texts = [r["answer_text"] for r in rows if r["answer_text"]]
        if first["workshop_gems"]:
            feedback_texts.append(first["workshop_gems"])
        if first["anything_else"]:
            feedback_texts.append(first["anything_else"])

        term = first["workshop_date"]
        if term and "/" in term:
            parts = term.split("/")
            if len(parts) == 3:
                term = f"{parts[2]}-{parts[1]}"

        survey = {}
        if avg_answer is not None:
            for key in (
                "post_confidence_avg",
                "post_resilience_avg",
                "post_self_awareness_avg",
                "post_stress_management_avg",
                "post_positive_self_image_avg",
                "post_optimism_avg",
                "post_peer_connection_avg",
            ):
                survey[key] = round(avg_answer, 2)

        sessions.append(
            {
                "session_id": workshop_code,
                "program_name": first["workshop_topic"] or workshop_code,
                "school_name": first["school_name"],
                "cohort": f"Year {first['year_level']} · {first['school_name']}",
                "term": term or "unknown",
                "session_date": first["workshop_date"],
                "workshop_region": first["workshop_region"],
                "registered_count": students,
                "attendance_count": students,
                "student_survey": survey,
                "student_feedback": feedback_texts,
                "facilitator_rating": avg_rating,
                "was_compromised": any(r["was_compromised"] for r in rows),
                "did_deviate": any(r["did_deviate"] for r in rows),
                "if_compromised": next((r["if_compromised"] for r in rows if r["if_compromised"]), ""),
                "if_deviated": next((r["if_deviated"] for r in rows if r["if_deviated"]), ""),
                "response_count": len(rows),
            }
        )

    return {
        "format": "lifechanger_csv",
        "dataset_name": path.name,
        "description": (
            "LifeChanger Salesforce-style workshop and feedback export "
            "(response-level rows grouped by workshop for analysis)."
        ),
        "records": sessions,
        "responses": responses,
        "scale_notes": {"survey_scale": "1 to 5 (ANSWER_VALUE where provided)"},
    }
