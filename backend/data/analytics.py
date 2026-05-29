"""Aggregate Lifechanger school-partner session records for API agents."""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean

ATTENDANCE_RISK_THRESHOLD = 0.75
WELLBEING_RISK_THRESHOLD = 3.3

POST_SURVEY_KEYS = (
    "post_confidence_avg",
    "post_resilience_avg",
    "post_self_awareness_avg",
    "post_stress_management_avg",
    "post_positive_self_image_avg",
    "post_optimism_avg",
    "post_peer_connection_avg",
)

POSITIVE_WORDS = frozenset(
    {
        "confident",
        "optimistic",
        "helped",
        "liked",
        "meaningful",
        "engaged",
        "calm",
        "good",
        "better",
        "more",
        "feel",
        "learning",
    }
)
NEGATIVE_WORDS = frozenset(
    {
        "difficult",
        "hard",
        "boring",
        "unsure",
        "worse",
        "anxious",
        "stress",
        "disconnected",
        "unmotivated",
    }
)


def _session_attendance_rate(record: dict) -> float:
    registered = record.get("registered_count") or 0
    if registered <= 0:
        return 0.0
    return record["attendance_count"] / registered


def _session_wellbeing(record: dict) -> float | None:
    survey = record.get("student_survey") or {}
    values = [survey[k] for k in POST_SURVEY_KEYS if survey.get(k) is not None]
    return mean(values) if values else None


def _classify_feedback(text: str) -> str:
    lower = text.lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in lower)
    neg = sum(1 for w in NEGATIVE_WORDS if w in lower)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "mixed"


def build_analytics(raw: dict) -> dict:
    records = raw["records"]
    by_program: dict[str, list] = defaultdict(list)
    by_term: dict[str, list] = defaultdict(list)
    feedback_samples: list[dict] = []

    for record in records:
        program = record["program_name"]
        by_program[program].append(record)
        by_term[record.get("term", "unknown")].append(record)

        for quote in record.get("student_feedback") or []:
            sentiment = _classify_feedback(quote)
            feedback_samples.append(
                {
                    "program_id": program,
                    "program_name": program,
                    "session_id": record["session_id"],
                    "school_name": record["school_name"],
                    "theme": record.get("workshop_topic") or record.get("lifechanger_pillar"),
                    "sentiment": sentiment,
                    "quote": quote,
                }
            )

    programs = []
    at_risk_programs = []
    for program_name, sessions in sorted(by_program.items()):
        attendance_rates = [_session_attendance_rate(s) for s in sessions]
        wellbeing_scores = [
            w for s in sessions if (w := _session_wellbeing(s)) is not None
        ]
        attendance_rate = mean(attendance_rates) if attendance_rates else 0.0
        wellbeing_score_avg = mean(wellbeing_scores) if wellbeing_scores else 0.0
        participants = sum(s.get("registered_count", 0) for s in sessions)

        program_row = {
            "id": program_name,
            "name": program_name,
            "cohort": f"{len({s['school_name'] for s in sessions})} schools · {len(sessions)} sessions",
            "participants": participants,
            "sessions_completed": len(sessions),
            "attendance_rate": round(attendance_rate, 3),
            "wellbeing_score_avg": round(wellbeing_score_avg, 2),
            "mentor_rating_avg": None,
            "status": "at_risk"
            if attendance_rate < ATTENDANCE_RISK_THRESHOLD
            or wellbeing_score_avg < WELLBEING_RISK_THRESHOLD
            else "active",
        }
        programs.append(program_row)
        if program_row["status"] == "at_risk":
            at_risk_programs.append(
                {
                    "id": program_name,
                    "name": program_name,
                    "cohort": program_row["cohort"],
                }
            )

    term_attendance = []
    term_wellbeing = []
    term_positive_pct = []
    for term in sorted(by_term.keys()):
        sessions = by_term[term]
        session_ids = {s["session_id"] for s in sessions}
        term_attendance.append(
            round(mean(_session_attendance_rate(s) for s in sessions), 3)
        )
        wb = [w for s in sessions if (w := _session_wellbeing(s)) is not None]
        term_wellbeing.append(round(mean(wb), 2) if wb else 0)
        term_feedback = [f for f in feedback_samples if f["session_id"] in session_ids]
        if term_feedback:
            pos = sum(1 for f in term_feedback if f["sentiment"] == "positive")
            term_positive_pct.append(round(pos / len(term_feedback), 2))
        else:
            term_positive_pct.append(0)

    sentiments = Counter(f["sentiment"] for f in feedback_samples)
    theme_counts = Counter(f["theme"] for f in feedback_samples)

    unique_schools = len({r["school_name"] for r in records})
    total_registered = sum(r.get("registered_count", 0) for r in records)
    total_attended = sum(r.get("attendance_count", 0) for r in records)
    mentor_sessions = sum(r.get("mentor_count", 0) for r in records)

    summary = {
        "total_programs": len(programs),
        "total_participants": total_registered,
        "total_sessions": len(records),
        "unique_schools": unique_schools,
        "avg_attendance": round(
            mean(_session_attendance_rate(r) for r in records), 2
        ),
        "avg_wellbeing": round(
            mean(w for r in records if (w := _session_wellbeing(r)) is not None), 2
        ),
        "at_risk_count": len(at_risk_programs),
    }

    return {
        "meta": {
            "dataset_name": raw.get("dataset_name"),
            "description": raw.get("description"),
            "export_date": records[0].get("session_date") if records else None,
            "record_count": len(records),
            "scale_notes": raw.get("scale_notes"),
        },
        "summary": summary,
        "programs": programs,
        "feedback_samples": feedback_samples,
        "quarterly_trends": {
            "terms": sorted(by_term.keys()),
            "overall_attendance": term_attendance,
            "wellbeing_avg": term_wellbeing,
            "positive_feedback_pct": term_positive_pct,
        },
        "funder_highlights": {
            "total_participants_ytd": total_registered,
            "total_attendance": total_attended,
            "programs_delivered": len(programs),
            "schools_partnered": unique_schools,
            "session_records": len(records),
            "mentor_assignments_total": mentor_sessions,
        },
        "at_risk_programs": at_risk_programs,
        "sentiment_distribution": dict(sentiments),
        "top_themes": theme_counts.most_common(10),
    }


def llm_context_summary(raw: dict, analytics: dict, *, max_quotes: int = 40) -> str:
    """Compact dataset summary for LLM prompts (not full 10k records)."""
    import json

    quotes = analytics["feedback_samples"][:max_quotes]
    payload = {
        "dataset_name": analytics["meta"]["dataset_name"],
        "description": raw.get("description"),
        "record_count": analytics["meta"]["record_count"],
        "workshop_count": analytics["meta"].get("workshop_count"),
        "scale_notes": raw.get("scale_notes"),
        "summary": analytics["summary"],
        "programs": analytics["programs"][:20],
        "question_analysis": analytics.get("question_analysis", [])[:10],
        "quarterly_trends": analytics["quarterly_trends"],
        "funder_highlights": analytics["funder_highlights"],
        "at_risk_programs": analytics["at_risk_programs"],
        "sentiment_distribution": analytics["sentiment_distribution"],
        "top_themes": analytics["top_themes"],
        "quarterly_trends": analytics.get("quarterly_trends"),
        "emerging_themes": analytics.get("emerging_themes", [])[:6],
        "correlations": analytics.get("correlations", [])[:5],
        "early_warnings": analytics.get("early_warnings", [])[:6],
        "workshop_outcomes": analytics.get("workshop_outcomes"),
        "sample_student_feedback": quotes,
    }
    return json.dumps(payload, indent=2)
