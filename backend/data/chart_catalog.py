"""Build Power BI–style chart specs from analytics for API + LLM consumption."""

from __future__ import annotations

from collections import Counter

CHART_PALETTE = [
    "#2563eb",
    "#7c3aed",
    "#059669",
    "#d97706",
    "#dc2626",
    "#0891b2",
    "#db2777",
    "#4f46e5",
]


def _bar_chart(
    chart_id: str,
    title: str,
    data: list[dict],
    *,
    x_key: str = "label",
    value_key: str = "value",
    description: str = "",
    horizontal: bool = False,
) -> dict:
    return {
        "id": chart_id,
        "title": title,
        "type": "horizontalBar" if horizontal else "bar",
        "description": description,
        "xKey": x_key,
        "valueKey": value_key,
        "data": data,
        "palette": CHART_PALETTE,
        "layout": "powerbi",
    }


def _pie_chart(chart_id: str, title: str, data: list[dict], *, description: str = "") -> dict:
    return {
        "id": chart_id,
        "title": title,
        "type": "pie",
        "description": description,
        "xKey": "label",
        "valueKey": "value",
        "data": data,
        "palette": CHART_PALETTE,
        "layout": "powerbi",
    }


def _line_chart(
    chart_id: str,
    title: str,
    data: list[dict],
    *,
    x_key: str = "label",
    series: list[dict] | None = None,
    description: str = "",
) -> dict:
    return {
        "id": chart_id,
        "title": title,
        "type": "line",
        "description": description,
        "xKey": x_key,
        "series": series or [{"key": "value", "name": "Value"}],
        "data": data,
        "palette": CHART_PALETTE,
        "layout": "powerbi",
    }


def _aggregate_csv_dimensions(raw: dict | None) -> dict:
    if not raw or raw.get("format") != "lifechanger_csv":
        return {}
    responses = raw.get("responses", [])
    by_region: Counter = Counter()
    by_year: Counter = Counter()
    by_topic: Counter = Counter()
    for row in responses:
        if row.get("school_region"):
            by_region[row["school_region"]] += 1
        if row.get("year_level"):
            by_year[str(row["year_level"])] += 1
        if row.get("workshop_topic"):
            by_topic[row["workshop_topic"]] += 1
    return {
        "by_region": by_region.most_common(12),
        "by_year": sorted(by_year.items(), key=lambda x: -x[1])[:10],
        "by_topic": by_topic.most_common(10),
    }


def build_chart_catalog(analytics: dict, raw: dict | None = None) -> list[dict]:
    """Return all predefined charts with embedded data."""
    summary = analytics.get("summary", {})
    programs = analytics.get("programs", [])
    sentiments = analytics.get("sentiment_distribution", {})
    themes = analytics.get("top_themes", [])
    questions = analytics.get("question_analysis", [])
    trends = analytics.get("quarterly_trends", {})
    risks = analytics.get("at_risk_programs", [])
    dims = _aggregate_csv_dimensions(raw)

    charts: list[dict] = []

    if sentiments:
        charts.append(
            _pie_chart(
                "sentiment_distribution",
                "Feedback sentiment mix",
                [{"label": k.replace("_", " ").title(), "value": v} for k, v in sentiments.items()],
                description="Share of classified student feedback by sentiment.",
            )
        )

    if themes:
        charts.append(
            _bar_chart(
                "top_themes",
                "Top workshop themes (feedback volume)",
                [{"label": t[0], "value": t[1]} for t in themes[:10]],
                horizontal=True,
                description="Most frequent workshop topics in student responses.",
            )
        )

    if programs:
        charts.append(
            _bar_chart(
                "programs_attendance",
                "Attendance rate by program / topic",
                [
                    {
                        "label": p["name"],
                        "value": round((p.get("attendance_rate") or 0) * 100, 1),
                    }
                    for p in programs
                ],
                description="Average attendance rate per workshop topic (%).",
            )
        )
        charts.append(
            _bar_chart(
                "programs_wellbeing",
                "Wellbeing score by program / topic",
                [
                    {"label": p["name"], "value": p.get("wellbeing_score_avg") or 0}
                    for p in programs
                ],
                description="Average wellbeing proxy score (1–5 scale) by topic.",
            )
        )
        mentor_vals = [
            {"label": p["name"], "value": p["mentor_rating_avg"]}
            for p in programs
            if p.get("mentor_rating_avg") is not None
        ]
        if mentor_vals:
            charts.append(
                _bar_chart(
                    "programs_facilitator_rating",
                    "Facilitator rating by program / topic",
                    mentor_vals,
                    description="Average facilitator workshop rating by topic.",
                )
            )

    if questions:
        charts.append(
            _bar_chart(
                "question_response_volume",
                "Responses per survey question",
                [
                    {"label": (q["question_text"][:48] + "…") if len(q["question_text"]) > 48 else q["question_text"], "value": q["response_count"]}
                    for q in questions[:12]
                ],
                horizontal=True,
                description="Number of valid responses per question text.",
            )
        )
        avg_vals = [
            {
                "label": (q["question_text"][:40] + "…") if len(q["question_text"]) > 40 else q["question_text"],
                "value": q["avg_answer_value"],
            }
            for q in questions
            if q.get("avg_answer_value") is not None
        ][:12]
        if avg_vals:
            charts.append(
                _bar_chart(
                    "question_avg_scores",
                    "Average answer value by question",
                    avg_vals,
                    horizontal=True,
                    description="Mean ANSWER_VALUE (typically 1–5) per question.",
                )
            )

    if dims.get("by_region"):
        charts.append(
            _bar_chart(
                "responses_by_region",
                "Responses by school region",
                [{"label": r[0], "value": r[1]} for r in dims["by_region"]],
                description="Geographic distribution of feedback rows.",
            )
        )

    if dims.get("by_year"):
        charts.append(
            _bar_chart(
                "responses_by_year_level",
                "Responses by year level",
                [{"label": f"Year {y[0]}", "value": y[1]} for y in dims["by_year"]],
                description="Student year level breakdown.",
            )
        )

    if dims.get("by_topic"):
        charts.append(
            _bar_chart(
                "workshop_topics_volume",
                "Workshop topics (response count)",
                [{"label": t[0], "value": t[1]} for t in dims["by_topic"]],
                description="Volume of feedback tied to each workshop topic pillar.",
            )
        )

    valid = summary.get("valid_responses") or summary.get("total_sessions") or 0
    hw = summary.get("heartwarming_count", 0)
    if valid and hw is not None:
        charts.append(
            _pie_chart(
                "heartwarming_share",
                "Heartwarming responses",
                [
                    {"label": "Heartwarming", "value": hw},
                    {"label": "Other", "value": max(valid - hw, 0)},
                ],
                description="Share of responses flagged as heartwarming.",
            )
        )

    compromised = summary.get("compromised_workshops", 0)
    deviated = summary.get("deviated_workshops", 0)
    total_w = summary.get("total_workshops") or summary.get("total_sessions") or 0
    if total_w:
        charts.append(
            _bar_chart(
                "workshop_delivery_flags",
                "Workshop delivery flags",
                [
                    {"label": "Compromised", "value": compromised},
                    {"label": "Deviated", "value": deviated},
                    {
                        "label": "On plan",
                        "value": max(total_w - compromised - deviated, 0),
                    },
                ],
                description="Workshops flagged as compromised or deviated from plan.",
            )
        )

    terms = trends.get("terms") or []
    if terms and trends.get("overall_attendance"):
        charts.append(
            _line_chart(
                "attendance_over_time",
                "Attendance trend by term",
                [
                    {"label": t, "value": round(v * 100, 1)}
                    for t, v in zip(terms, trends["overall_attendance"], strict=False)
                ],
                description="Overall attendance rate across terms (%).",
            )
        )
    if terms and trends.get("wellbeing_avg"):
        charts.append(
            _line_chart(
                "wellbeing_over_time",
                "Wellbeing trend by term",
                [
                    {"label": t, "value": round(v, 2)}
                    for t, v in zip(terms, trends["wellbeing_avg"], strict=False)
                ],
                description="Average wellbeing score by term.",
            )
        )

    # KPI strip as a simple bar for dashboard-style view
    kpi_data = [
        {"label": "Valid responses", "value": summary.get("valid_responses") or 0},
        {"label": "Workshops", "value": summary.get("total_workshops") or summary.get("total_sessions") or 0},
        {"label": "Schools", "value": summary.get("total_schools") or summary.get("unique_schools") or 0},
        {"label": "At-risk topics", "value": summary.get("at_risk_count") or len(risks)},
    ]
    charts.append(
        _bar_chart(
            "kpi_overview",
            "Program reach overview",
            kpi_data,
            description="High-level counts from the LifeChanger dataset.",
        )
    )

    return charts


def chart_catalog_index(charts: list[dict]) -> list[dict]:
    """Lightweight index for LLM chart picker (no full data)."""
    return [
        {
            "id": c["id"],
            "title": c["title"],
            "type": c["type"],
            "description": c.get("description", ""),
            "sample_labels": [row.get("label") for row in (c.get("data") or [])[:3]],
        }
        for c in charts
    ]


def get_charts_by_ids(charts: list[dict], chart_ids: list[str]) -> list[dict]:
    by_id = {c["id"]: c for c in charts}
    return [by_id[cid] for cid in chart_ids if cid in by_id]
