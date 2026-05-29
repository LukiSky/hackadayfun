from agents.llm_client import complete_with_context
from data.repository import MockDataRepository

_repo = MockDataRepository()

AUDIENCE_PROMPTS = {
    "funders": "Write a concise impact report for funders emphasizing outcomes, scale, and ROI-style evidence.",
    "schools": "Write a partner-facing report for schools emphasizing student wellbeing, attendance, and collaboration opportunities.",
    "board": "Write a strategic board report with risks, opportunities, and quarterly trend commentary.",
    "internal": "Write an internal operations report with cohort flags and recommended follow-up actions for program staff.",
}


def generate_report(audience: str) -> dict:
    audience_key = audience.lower().strip()
    if audience_key not in AUDIENCE_PROMPTS:
        raise ValueError(
            f"Unknown audience '{audience}'. Use: {', '.join(AUDIENCE_PROMPTS)}"
        )

    context = _repo.dataset_context()
    system = (
        "You are the Report Writer Agent for ImpactLens AI (Lifechanger nonprofit). "
        "Use ONLY the provided dataset. Cite specific numbers from the data. "
        "Do not invent participants, schools, or metrics. "
        "Use clear headings and bullet points. Keep under 500 words."
    )
    user = (
        f"{AUDIENCE_PROMPTS[audience_key]}\n\n"
        f"Dataset:\n{context}"
    )

    report_text = complete_with_context(system, user)
    return {
        "audience": audience_key,
        "report": report_text,
        "citations": ["Generated from mock dataset export; all figures must match provided JSON."],
    }
