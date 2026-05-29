"""Project Success Vision analytics: trends, correlations, patterns, early warnings."""

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


def build_csv_quarterly_trends(
    records: list[dict],
    feedback_samples: list[dict],
) -> dict:
    """Longitudinal tracking by workshop term (from CSV session dates)."""
    by_term: dict[str, list] = defaultdict(list)
    for session in records:
        by_term[session.get("term") or "unknown"].append(session)

    terms = sorted(t for t in by_term.keys() if t != "unknown")
    if not terms:
        terms = sorted(by_term.keys())

    term_attendance: list[float] = []
    term_wellbeing: list[float] = []
    term_positive_pct: list[float] = []

    for term in terms:
        sessions = by_term[term]
        term_attendance.append(
            round(mean(_session_attendance_rate(s) for s in sessions), 3)
        )
        wb = [w for s in sessions if (w := _session_wellbeing(s)) is not None]
        term_wellbeing.append(round(mean(wb), 2) if wb else 0.0)
        session_ids = {s["session_id"] for s in sessions}
        term_feedback = [f for f in feedback_samples if f["session_id"] in session_ids]
        if term_feedback:
            pos = sum(1 for f in term_feedback if f["sentiment"] == "positive")
            term_positive_pct.append(round(pos / len(term_feedback), 2))
        else:
            term_positive_pct.append(0.0)

    return {
        "terms": terms,
        "overall_attendance": term_attendance,
        "wellbeing_avg": term_wellbeing,
        "positive_feedback_pct": term_positive_pct,
    }


def detect_emerging_themes(
    responses: list[dict],
    top_themes: list[tuple[str, int]],
    quarterly_trends: dict,
) -> list[dict]:
    """Pattern recognition: dominant themes and sentiment shift across terms."""
    emerging: list[dict] = []
    for theme, count in top_themes[:5]:
        theme_responses = [r for r in responses if r.get("workshop_topic") == theme]
        sentiments = Counter(_classify_feedback(r["answer_text"]) for r in theme_responses)
        emerging.append(
            {
                "theme": theme,
                "response_count": count,
                "sentiment_mix": dict(sentiments),
                "note": "Dominant workshop pillar in student voice sample.",
            }
        )

    terms = quarterly_trends.get("terms") or []
    pos_pct = quarterly_trends.get("positive_feedback_pct") or []
    if len(terms) >= 2 and len(pos_pct) >= 2:
        delta = pos_pct[-1] - pos_pct[0]
        direction = "improving" if delta > 0.05 else "declining" if delta < -0.05 else "stable"
        emerging.append(
            {
                "theme": "_longitudinal_sentiment",
                "response_count": None,
                "sentiment_mix": {"first_term_positive_pct": pos_pct[0], "latest_term_positive_pct": pos_pct[-1]},
                "note": f"Positive feedback share is {direction} from {terms[0]} to {terms[-1]} ({delta:+.0%}).",
            }
        )
    return emerging


def compute_correlations(records: list[dict], responses: list[dict]) -> list[dict]:
    """Condition–outcome associations (not causal claims)."""
    insights: list[dict] = []

    by_topic: dict[str, dict] = defaultdict(
        lambda: {"ratings": [], "answers": [], "workshops": 0, "compromised": 0}
    )
    for rec in records:
        topic = rec.get("program_name") or "unknown"
        by_topic[topic]["workshops"] += 1
        if rec.get("facilitator_rating") is not None:
            by_topic[topic]["ratings"].append(rec["facilitator_rating"])
        if rec.get("was_compromised"):
            by_topic[topic]["compromised"] += 1
    for row in responses:
        topic = row.get("workshop_topic") or "unknown"
        if row.get("answer_value") is not None:
            by_topic[topic]["answers"].append(row["answer_value"])

    for topic, data in sorted(by_topic.items(), key=lambda x: -x[1]["workshops"]):
        if len(data["ratings"]) < 2 or len(data["answers"]) < 5:
            continue
        avg_rating = mean(data["ratings"])
        avg_answer = mean(data["answers"])
        compromise_rate = data["compromised"] / max(data["workshops"], 1)
        strength = "strong" if avg_rating >= 4.0 and avg_answer >= 3.8 else "moderate"
        insights.append(
            {
                "topic": topic,
                "avg_facilitator_rating": round(avg_rating, 2),
                "avg_student_answer_value": round(avg_answer, 2),
                "compromised_workshop_rate": round(compromise_rate, 2),
                "workshop_count": data["workshops"],
                "association": (
                    f"Higher facilitator ratings ({avg_rating:.1f}) co-occur with "
                    f"stronger student scale scores ({avg_answer:.1f}) on {topic} workshops."
                ),
                "strength": strength,
            }
        )

    high_rating = [i for i in insights if i["avg_facilitator_rating"] >= 4.0]
    if high_rating:
        best = max(high_rating, key=lambda x: x["avg_student_answer_value"])
        insights.insert(
            0,
            {
                "topic": "_portfolio",
                "association": (
                    f"Workshops with facilitator ratings ≥4.0 most often align with "
                    f"strong student outcomes on {best['topic']} pillar."
                ),
                "strength": "portfolio",
                "related_topic": best["topic"],
            },
        )

    return insights[:8]


def build_early_warnings(records: list[dict], programs: list[dict]) -> list[dict]:
    """Proactive alerting: schools and topics showing underperformance signals."""
    warnings: list[dict] = []

    for program in programs:
        if program.get("status") == "at_risk":
            warnings.append(
                {
                    "level": "high",
                    "entity_type": "workshop_topic",
                    "entity_name": program["name"],
                    "signal": "topic_at_risk",
                    "metrics": {
                        "attendance_rate": program.get("attendance_rate"),
                        "wellbeing_score_avg": program.get("wellbeing_score_avg"),
                        "mentor_rating_avg": program.get("mentor_rating_avg"),
                    },
                    "message": f"Topic '{program['name']}' is flagged at-risk across delivery metrics.",
                }
            )

    by_school: dict[str, list] = defaultdict(list)
    for rec in records:
        by_school[rec.get("school_name") or "unknown"].append(rec)

    school_scores: list[tuple[str, float, dict]] = []
    for school, sessions in by_school.items():
        if school == "unknown" or len(sessions) < 2:
            continue
        ratings = [s["facilitator_rating"] for s in sessions if s.get("facilitator_rating") is not None]
        wellbeing = [w for s in sessions if (w := _session_wellbeing(s)) is not None]
        attendance = [_session_attendance_rate(s) for s in sessions]
        score = mean(attendance) * 0.3 + (mean(wellbeing) / 5 if wellbeing else 0.5) * 0.4
        if ratings:
            score += (mean(ratings) / 5) * 0.3
        compromised = any(s.get("was_compromised") for s in sessions)
        school_scores.append((school, score, {"sessions": len(sessions), "compromised": compromised}))

    school_scores.sort(key=lambda x: x[1])
    for school, score, meta in school_scores[:5]:
        if score < 0.72 or meta["compromised"]:
            warnings.append(
                {
                    "level": "medium" if score >= 0.6 else "high",
                    "entity_type": "school",
                    "entity_name": school,
                    "signal": "underperforming_school",
                    "metrics": {"composite_score": round(score, 2), **meta},
                    "message": (
                        f"School '{school}' shows weaker composite delivery/outcome signals "
                        f"(score {score:.2f} across {meta['sessions']} workshops)."
                    ),
                }
            )

    return warnings[:12]


def rank_workshop_outcomes(records: list[dict]) -> dict:
    """Best/worst workshops for natural-language 'best outcomes' queries."""
    scored: list[dict] = []
    for rec in records:
        wb = _session_wellbeing(rec)
        rating = rec.get("facilitator_rating")
        score = _session_attendance_rate(rec) * 0.25
        if wb is not None:
            score += (wb / 5) * 0.45
        if rating is not None:
            score += (rating / 5) * 0.3
        if rec.get("was_compromised") or rec.get("did_deviate"):
            score *= 0.7
        scored.append(
            {
                "workshop_code": rec.get("session_id"),
                "school_name": rec.get("school_name"),
                "topic": rec.get("program_name"),
                "term": rec.get("term"),
                "composite_score": round(score, 3),
                "facilitator_rating": rating,
            }
        )
    scored.sort(key=lambda x: x["composite_score"], reverse=True)
    return {
        "best_workshops": scored[:5],
        "lowest_workshops": list(reversed(scored[-5:])),
    }


def enrich_analytics_with_success_vision(
    analytics: dict,
    raw: dict,
) -> dict:
    """Attach Success Vision fields to analytics payload."""
    records = raw.get("records", [])
    responses = raw.get("responses", [])
    feedback_samples = analytics.get("feedback_samples", [])

    trends = build_csv_quarterly_trends(records, feedback_samples)
    if not analytics.get("quarterly_trends"):
        analytics["quarterly_trends"] = trends

    analytics["emerging_themes"] = detect_emerging_themes(
        responses,
        analytics.get("top_themes", []),
        analytics["quarterly_trends"],
    )
    analytics["correlations"] = compute_correlations(records, responses)
    analytics["early_warnings"] = build_early_warnings(records, analytics.get("programs", []))
    analytics["workshop_outcomes"] = rank_workshop_outcomes(records)
    return analytics
