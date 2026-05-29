"""Map Product Success Vision criteria to implemented platform capabilities."""

from __future__ import annotations

from data.repository import MockDataRepository

_repo = MockDataRepository()

CRITERIA = [
    {
        "id": "1",
        "category": "Data Analysis",
        "objective": "Analyse both quantitative numbers and qualitative text feedback.",
        "capabilities": [
            {"type": "Pattern Recognition", "feature": "emerging_themes", "endpoint": "/api/analyze"},
            {"type": "Sentiment Analysis", "feature": "sentiment_distribution", "endpoint": "/api/analyze"},
            {"type": "Longitudinal Tracking", "feature": "quarterly_trends", "endpoint": "/api/analyze"},
        ],
    },
    {
        "id": "2",
        "category": "Performance Tracking",
        "objective": "Identify program conditions correlating with good outcomes and flag early warning signs.",
        "capabilities": [
            {"type": "Correlation", "feature": "correlations", "endpoint": "/api/analyze"},
            {"type": "Proactive Alerting", "feature": "early_warnings", "endpoint": "/api/analyze"},
        ],
    },
    {
        "id": "3",
        "category": "Automated Reporting",
        "objective": "Auto-generate reports tailored to different stakeholder audiences.",
        "audiences": [
            {
                "type": "Funders",
                "primary_requirement": "Quantitative data, metrics, and numbers",
                "endpoint": "POST /api/report",
                "audience_key": "funders",
            },
            {
                "type": "Schools",
                "primary_requirement": "Qualitative feedback, experiences, and stories",
                "endpoint": "POST /api/report",
                "audience_key": "schools",
            },
            {
                "type": "Board of Directors",
                "primary_requirement": "Strategic insight and high-level trajectory",
                "endpoint": "POST /api/report",
                "audience_key": "board",
            },
        ],
    },
    {
        "id": "4",
        "category": "User Accessibility",
        "objective": "Empower staff to query data using plain-English questions.",
        "example_queries": [
            "Which workshops had the best outcomes last term?",
            "Which schools are underperforming?",
            "Show a chart of sentiment across workshop topics",
        ],
        "endpoint": "POST /api/ask",
    },
    {
        "id": "5",
        "category": "Storytelling",
        "objective": "Compile participant stories into compelling impact narratives.",
        "capabilities": [
            {"type": "Aggregation", "feature": "feedback_samples + citations"},
            {"type": "Content Creation", "feature": "impact_story"},
        ],
        "endpoint": "POST /api/story",
    },
]


def _capability_status(analytics: dict, feature: str) -> dict:
    if feature == "emerging_themes":
        items = analytics.get("emerging_themes") or []
        return {"implemented": len(items) > 0, "count": len(items)}
    if feature == "sentiment_distribution":
        dist = analytics.get("sentiment_distribution") or {}
        return {"implemented": bool(dist), "keys": list(dist.keys())}
    if feature == "quarterly_trends":
        trends = analytics.get("quarterly_trends") or {}
        terms = trends.get("terms") or []
        return {"implemented": len(terms) > 0, "term_count": len(terms)}
    if feature == "correlations":
        items = analytics.get("correlations") or []
        return {"implemented": len(items) > 0, "count": len(items)}
    if feature == "early_warnings":
        items = analytics.get("early_warnings") or []
        return {"implemented": len(items) > 0, "count": len(items)}
    if feature == "feedback_samples + citations":
        return {
            "implemented": len(analytics.get("feedback_samples") or []) > 0,
            "sample_count": len(analytics.get("feedback_samples") or []),
        }
    if feature == "impact_story":
        return {"implemented": True, "note": "Generated via LangChain storytelling agent"}
    return {"implemented": False}


def get_success_vision_status() -> dict:
    analytics = _repo.get_analytics()
    criteria_out = []

    for criterion in CRITERIA:
        entry = {
            "id": criterion["id"],
            "category": criterion["category"],
            "objective": criterion["objective"],
            "status": "implemented",
        }

        if "capabilities" in criterion:
            caps = []
            for cap in criterion["capabilities"]:
                st = _capability_status(analytics, cap["feature"])
                caps.append({**cap, **st})
                if not st.get("implemented"):
                    entry["status"] = "partial"
            entry["capabilities"] = caps

        if "audiences" in criterion:
            entry["audiences"] = criterion["audiences"]
            entry["status"] = "implemented"

        if "example_queries" in criterion:
            entry["example_queries"] = criterion["example_queries"]
            entry["endpoint"] = criterion["endpoint"]
            wo = analytics.get("workshop_outcomes") or {}
            entry["data_hints"] = {
                "best_workshops": wo.get("best_workshops", [])[:3],
                "early_warning_schools": [
                    w["entity_name"]
                    for w in (analytics.get("early_warnings") or [])
                    if w.get("entity_type") == "school"
                ][:3],
            }

        if "endpoint" in criterion and criterion.get("id") == "5":
            entry["capabilities"] = [
                {**c, **_capability_status(analytics, c["feature"])} for c in criterion["capabilities"]
            ]
            entry["endpoint"] = criterion["endpoint"]

        criteria_out.append(entry)

    all_implemented = all(c["status"] == "implemented" for c in criteria_out)
    return {
        "title": "What Success Looks Like",
        "overall_status": "implemented" if all_implemented else "partial",
        "criteria": criteria_out,
        "summary": analytics.get("summary", {}),
    }
