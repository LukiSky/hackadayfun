"""Rule-based answers from analytics when HF_TOKEN is unavailable."""

from __future__ import annotations

import re

from data.repository import MockDataRepository

_repo = MockDataRepository()


def answer_from_analytics(question: str, analytics: dict | None = None) -> str:
    a = analytics or _repo.get_analytics()
    q = question.lower().strip()
    summary = a.get("summary") or {}
    programs = a.get("programs") or []
    meta = a.get("meta") or {}

    if re.search(r"\b(how many|count|number of)\b.*\b(participant|student|young people)\b", q):
        return (
            f"The dataset has **{summary.get('total_participants', 0):,}** registered participants "
            f"across **{summary.get('total_sessions', 0):,}** session records "
            f"({meta.get('record_count', 0):,} rows in {meta.get('dataset_name', 'dataset')})."
        )

    if re.search(r"\b(how many|count)\b.*\b(session|record)\b", q):
        return f"There are **{summary.get('total_sessions', 0):,}** session records in the loaded dataset."

    if re.search(r"\b(school|schools)\b", q):
        return f"**{summary.get('unique_schools', 0)}** unique partner schools appear in the data."

    if re.search(r"\b(at[- ]?risk|risk|flagged)\b", q):
        at_risk = a.get("at_risk_programs") or []
        names = ", ".join(p["name"] for p in at_risk[:5]) or "none flagged"
        return (
            f"**{summary.get('at_risk_count', 0)}** program(s) are below attendance or wellbeing thresholds. "
            f"Examples: {names}."
        )

    if re.search(r"\b(lowest|worst|minimum)\b.*\b(attendance)\b", q) or "lowest attendance" in q:
        if not programs:
            return "No program rows available in analytics."
        worst = min(programs, key=lambda p: p.get("attendance_rate", 1))
        pct = round((worst.get("attendance_rate") or 0) * 100)
        return (
            f"**{worst['name']}** has the lowest attendance at **{pct}%** "
            f"({worst.get('sessions_completed', 0)} sessions in the aggregate)."
        )

    if re.search(r"\b(highest|best|maximum)\b.*\b(attendance)\b", q):
        if not programs:
            return "No program rows available."
        best = max(programs, key=lambda p: p.get("attendance_rate", 0))
        pct = round((best.get("attendance_rate") or 0) * 100)
        return f"**{best['name']}** has the highest attendance at **{pct}%.**"

    if re.search(r"\b(theme|themes|feedback)\b", q):
        themes = a.get("top_themes") or []
        if not themes:
            return "No feedback themes aggregated."
        lines = [f"- {t[0]}: {t[1]} mentions" for t in themes[:6]]
        return "Top feedback themes:\n" + "\n".join(lines)

    if re.search(r"\b(sentiment|positive|negative|mixed)\b", q):
        dist = a.get("sentiment_distribution") or {}
        parts = [f"- {k}: {v}" for k, v in dist.items()]
        return "Feedback sentiment breakdown:\n" + ("\n".join(parts) if parts else "No sentiment data.")

    if re.search(r"\b(average|avg|mean)\b.*\b(attendance)\b", q):
        pct = round((summary.get("avg_attendance") or 0) * 100)
        return f"Average attendance across all sessions is **{pct}%**."

    if re.search(r"\b(wellbeing|well-being)\b", q):
        return f"Average post-program wellbeing score is **{summary.get('avg_wellbeing', '—')}** (scale from student surveys)."

    # Default summary
    return (
        f"Loaded **{meta.get('record_count', 0):,}** records · "
        f"**{summary.get('total_programs', 0)}** programs · "
        f"**{summary.get('unique_schools', 0)}** schools · "
        f"avg attendance **{round((summary.get('avg_attendance') or 0) * 100)}%** · "
        f"**{summary.get('at_risk_count', 0)}** at-risk. "
        f"Ask about attendance, themes, sentiment, or say «add a bar chart of attendance by program» on the Dashboard tab."
    )


def ask_locally(user_question: str) -> dict:
    answer = answer_from_analytics(user_question)
    return {
        "question": user_question,
        "answer": answer,
        "citations": ["Local analytics engine (no LLM). Set HF_TOKEN for richer answers."],
        "source": "local",
    }
