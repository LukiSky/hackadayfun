from data.analytics import ATTENDANCE_RISK_THRESHOLD, WELLBEING_RISK_THRESHOLD
from data.repository import MockDataRepository

_repo = MockDataRepository()


def get_dashboard_metrics() -> dict:
    a = _repo.get_analytics()
    return {
        "summary": a["summary"],
        "programs": a["programs"],
        "quarterly_trends": a["quarterly_trends"],
        "funder_highlights": a["funder_highlights"],
        "at_risk_programs": a["at_risk_programs"],
        "dataset": a["meta"],
    }


def analyze_program_data() -> dict:
    a = _repo.get_analytics()
    feedback_by_program: dict[str, list] = {}
    for item in a["feedback_samples"]:
        feedback_by_program.setdefault(item["program_id"], []).append(item)

    program_insights = []
    for program in a["programs"]:
        pid = program["id"]
        feedback = feedback_by_program.get(pid, [])
        sentiments = [f["sentiment"] for f in feedback]
        program_insights.append(
            {
                "program_id": pid,
                "name": program["name"],
                "cohort": program["cohort"],
                "attendance_rate": program["attendance_rate"],
                "wellbeing_score_avg": program["wellbeing_score_avg"],
                "sessions_completed": program.get("sessions_completed"),
                "feedback_count": len(feedback),
                "sentiment_breakdown": {
                    "positive": sentiments.count("positive"),
                    "mixed": sentiments.count("mixed"),
                    "negative": sentiments.count("negative"),
                },
                "flagged": program["id"]
                in {p["id"] for p in a["at_risk_programs"]},
            }
        )

    meta = a["meta"]
    summary = a["summary"]
    return {
        "overall_summary": summary,
        "program_insights": program_insights,
        "quarterly_trends": a["quarterly_trends"],
        "question_analysis": a.get("question_analysis", []),
        "citations": [
            f"Loaded {meta['record_count']} feedback responses from {meta['dataset_name']}.",
            f"{meta.get('workshop_count', summary.get('total_sessions', 0))} workshops across {summary.get('unique_schools', 0)} schools.",
            f"{summary['at_risk_count']} topic/workshop group(s) flagged for follow-up.",
        ],
    }
