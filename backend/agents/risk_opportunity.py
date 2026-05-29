from data.analytics import ATTENDANCE_RISK_THRESHOLD, WELLBEING_RISK_THRESHOLD
from data.repository import MockDataRepository

_repo = MockDataRepository()


def identify_risks_and_opportunities() -> dict:
    a = _repo.get_analytics()
    risks = []
    opportunities = []

    for program in a["programs"]:
        pid = program["id"]
        if program["attendance_rate"] < ATTENDANCE_RISK_THRESHOLD:
            risks.append(
                {
                    "type": "attendance",
                    "program_id": pid,
                    "program_name": program["name"],
                    "cohort": program["cohort"],
                    "metric": program["attendance_rate"],
                    "threshold": ATTENDANCE_RISK_THRESHOLD,
                    "recommendation": "Review session scheduling and transport barriers with school partner.",
                }
            )
        if program["wellbeing_score_avg"] < WELLBEING_RISK_THRESHOLD:
            risks.append(
                {
                    "type": "wellbeing",
                    "program_id": pid,
                    "program_name": program["name"],
                    "cohort": program["cohort"],
                    "metric": program["wellbeing_score_avg"],
                    "threshold": WELLBEING_RISK_THRESHOLD,
                    "recommendation": "Increase mentor check-in cadence and wellbeing-focused activities.",
                }
            )
        if (
            program["attendance_rate"] >= 0.88
            and program["wellbeing_score_avg"] >= 4.0
        ):
            opportunities.append(
                {
                    "type": "scale_candidate",
                    "program_id": pid,
                    "program_name": program["name"],
                    "cohort": program["cohort"],
                    "note": "Strong attendance and wellbeing — candidate for case study or expansion.",
                }
            )

    meta = a["meta"]
    return {
        "risks": risks,
        "opportunities": opportunities,
        "citations": [
            f"Risk thresholds: attendance < {ATTENDANCE_RISK_THRESHOLD:.0%}, wellbeing < {WELLBEING_RISK_THRESHOLD}.",
            f"Evaluated {meta['record_count']} session records across {a['summary']['total_programs']} programs.",
        ],
    }
