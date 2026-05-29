"""Analytics for LifeChanger CSV (PRD-aligned metrics)."""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean

from data.analytics import (
    ATTENDANCE_RISK_THRESHOLD,
    WELLBEING_RISK_THRESHOLD,
    _classify_feedback,
    _session_attendance_rate,
    _session_wellbeing,
)


def _question_analysis(responses: list[dict]) -> list[dict]:
    by_question: dict[str, list[dict]] = defaultdict(list)
    for row in responses:
        by_question[row["question_text"]].append(row)

    results = []
    for question, rows in sorted(by_question.items(), key=lambda x: -len(x[1]))[:15]:
        values = [r["answer_value"] for r in rows if r["answer_value"] is not None]
        sentiments = Counter(_classify_feedback(r["answer_text"]) for r in rows)
        results.append(
            {
                "question_text": question,
                "response_count": len(rows),
                "avg_answer_value": round(mean(values), 2) if values else None,
                "sentiment": dict(sentiments),
                "sample_answers": [r["answer_text"] for r in rows[:3]],
            }
        )
    return results


def build_analytics_csv(raw: dict) -> dict:
    records = raw["records"]
    responses = raw["responses"]

    feedback_samples = []
    for row in responses:
        sentiment = _classify_feedback(row["answer_text"])
        feedback_samples.append(
            {
                "program_id": row["workshop_topic"],
                "program_name": row["workshop_topic"],
                "session_id": row["workshop_code"],
                "school_name": row["school_name"],
                "theme": row["workshop_topic"],
                "sentiment": sentiment,
                "quote": row["answer_text"],
                "question_text": row["question_text"],
                "heartwarming": row["heartwarming"],
            }
        )

    by_program: dict[str, list] = defaultdict(list)
    for record in records:
        by_program[record["program_name"]].append(record)

    programs = []
    at_risk_programs = []
    for program_name, sessions in sorted(by_program.items()):
        attendance_rates = [_session_attendance_rate(s) for s in sessions]
        wellbeing_scores = [w for s in sessions if (w := _session_wellbeing(s)) is not None]
        ratings = [
            s["facilitator_rating"]
            for s in sessions
            if s.get("facilitator_rating") is not None
        ]
        attendance_rate = mean(attendance_rates) if attendance_rates else 1.0
        wellbeing_score_avg = mean(wellbeing_scores) if wellbeing_scores else 3.5
        avg_facilitator = mean(ratings) if ratings else None

        compromised = any(s.get("was_compromised") for s in sessions)
        deviated = any(s.get("did_deviate") for s in sessions)
        low_rating = avg_facilitator is not None and avg_facilitator < 3.0

        status = "at_risk"
        if (
            attendance_rate < ATTENDANCE_RISK_THRESHOLD
            or wellbeing_score_avg < WELLBEING_RISK_THRESHOLD
            or compromised
            or deviated
            or low_rating
        ):
            status = "at_risk"

        program_row = {
            "id": program_name,
            "name": program_name,
            "cohort": f"{len({s['school_name'] for s in sessions})} schools · {len(sessions)} workshops",
            "participants": sum(s.get("registered_count", 0) for s in sessions),
            "sessions_completed": len(sessions),
            "attendance_rate": round(attendance_rate, 3),
            "wellbeing_score_avg": round(wellbeing_score_avg, 2),
            "mentor_rating_avg": round(avg_facilitator, 2) if avg_facilitator is not None else None,
            "status": status,
        }
        programs.append(program_row)
        if status == "at_risk":
            at_risk_programs.append(
                {"id": program_name, "name": program_name, "cohort": program_row["cohort"]}
            )

    answer_values = [r["answer_value"] for r in responses if r["answer_value"] is not None]
    facilitator_ratings = [
        s.get("facilitator_rating")
        for s in records
        if s.get("facilitator_rating") is not None
    ]
    heartwarming_count = sum(1 for r in responses if r.get("heartwarming"))
    compromised_workshops = sum(1 for s in records if s.get("was_compromised"))
    deviated_workshops = sum(1 for s in records if s.get("did_deviate"))

    topic_counts = Counter(r["workshop_topic"] for r in responses)
    region_counts = Counter(r["school_region"] for r in responses)
    year_counts = Counter(r["year_level"] for r in responses)

    summary = {
        "valid_responses": len(responses),
        "total_workshops": len(records),
        "total_schools": len({r["school_name"] for r in responses}),
        "total_programs": len(programs),
        "total_participants": sum(s.get("registered_count", 0) for s in records),
        "total_sessions": len(records),
        "unique_schools": len({r["school_name"] for r in responses}),
        "avg_answer_value": round(mean(answer_values), 2) if answer_values else None,
        "avg_facilitator_rating": round(mean(facilitator_ratings), 2)
        if facilitator_ratings
        else None,
        "heartwarming_count": heartwarming_count,
        "compromised_workshops": compromised_workshops,
        "deviated_workshops": deviated_workshops,
        "avg_attendance": round(mean(_session_attendance_rate(r) for r in records), 2)
        if records
        else 0,
        "avg_wellbeing": round(
            mean(w for r in records if (w := _session_wellbeing(r)) is not None), 2
        )
        if records
        else 0,
        "at_risk_count": len(at_risk_programs),
        "top_workshop_topic": topic_counts.most_common(1)[0][0] if topic_counts else None,
        "top_school_region": region_counts.most_common(1)[0][0] if region_counts else None,
        "top_year_level": str(year_counts.most_common(1)[0][0]) if year_counts else None,
    }

    sentiments = Counter(f["sentiment"] for f in feedback_samples)
    theme_counts = Counter(f["theme"] for f in feedback_samples)

    return {
        "meta": {
            "dataset_name": raw.get("dataset_name"),
            "description": raw.get("description"),
            "export_date": records[0].get("session_date") if records else None,
            "record_count": len(responses),
            "workshop_count": len(records),
            "scale_notes": raw.get("scale_notes"),
            "source_format": "csv",
        },
        "summary": summary,
        "programs": programs,
        "feedback_samples": feedback_samples,
        "question_analysis": _question_analysis(responses),
        "quarterly_trends": {},
        "funder_highlights": {
            "valid_responses": len(responses),
            "workshops_delivered": len(records),
            "schools_partnered": summary["total_schools"],
            "heartwarming_responses": heartwarming_count,
            "total_students_reached": summary["total_participants"],
        },
        "at_risk_programs": at_risk_programs,
        "sentiment_distribution": dict(sentiments),
        "top_themes": theme_counts.most_common(10),
    }
