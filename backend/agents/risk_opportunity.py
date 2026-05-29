from data.analytics import ATTENDANCE_RISK_THRESHOLD, WELLBEING_RISK_THRESHOLD
from data.repository import MockDataRepository

_repo = MockDataRepository()
FACILITATOR_RISK_THRESHOLD = 3.0


def identify_risks_and_opportunities() -> dict:
    a = _repo.get_analytics()
    risks = []
    opportunities = []
    is_csv = a.get("meta", {}).get("source_format") == "csv"

    for program in a["programs"]:
        pid = program["id"]
        if program.get("attendance_rate", 1) < ATTENDANCE_RISK_THRESHOLD:
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
        if program.get("wellbeing_score_avg", 5) < WELLBEING_RISK_THRESHOLD:
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
        rating = program.get("mentor_rating_avg")
        if rating is not None and rating < FACILITATOR_RISK_THRESHOLD:
            risks.append(
                {
                    "type": "facilitator_rating",
                    "program_id": pid,
                    "program_name": program["name"],
                    "cohort": program["cohort"],
                    "metric": rating,
                    "threshold": FACILITATOR_RISK_THRESHOLD,
                    "recommendation": "Review facilitator assignment and workshop delivery support.",
                }
            )
        if (
            program.get("attendance_rate", 0) >= 0.88
            and program.get("wellbeing_score_avg", 0) >= 4.0
        ):
            opportunities.append(
                {
                    "type": "scale_candidate",
                    "program_id": pid,
                    "program_name": program["name"],
                    "cohort": program["cohort"],
                    "note": "Strong outcomes — candidate for case study or expansion.",
                }
            )

    if is_csv:
        raw = _repo.load_dataset()
        for session in raw.get("records", []):
            wc = session.get("workshop_code") or session.get("session_id")
            if session.get("was_compromised"):
                risks.append(
                    {
                        "type": "compromised_workshop",
                        "program_id": wc,
                        "program_name": session.get("program_name", wc),
                        "cohort": session.get("school_name", ""),
                        "metric": True,
                        "threshold": True,
                        "recommendation": session.get("if_compromised")
                        or "Follow up on compromised delivery with school partner.",
                    }
                )
            if session.get("did_deviate"):
                risks.append(
                    {
                        "type": "deviated_workshop",
                        "program_id": wc,
                        "program_name": session.get("program_name", wc),
                        "cohort": session.get("school_name", ""),
                        "metric": True,
                        "threshold": True,
                        "recommendation": session.get("if_deviated")
                        or "Review whether deviation affected learning outcomes.",
                    }
                )

    meta = a["meta"]
    return {
        "risks": risks,
        "opportunities": opportunities,
        "citations": [
            "Risk signals from LifeChanger CSV fields (facilitator rating, compromised, deviated, answer values)."
            if is_csv
            else f"Risk thresholds: attendance < {ATTENDANCE_RISK_THRESHOLD:.0%}, wellbeing < {WELLBEING_RISK_THRESHOLD}.",
            f"Evaluated {meta.get('record_count', 0)} records across {meta.get('workshop_count', a['summary'].get('total_workshops', 0))} workshops.",
        ],
    }
