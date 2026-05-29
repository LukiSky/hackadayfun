from agents.llm_client import complete_with_context
from data.repository import MockDataRepository

_repo = MockDataRepository()


def generate_impact_story(theme: str | None = None) -> dict:
    analytics = _repo.get_analytics()
    positive_quotes = [
        f["quote"]
        for f in analytics["feedback_samples"]
        if f["sentiment"] == "positive"
    ][:30]

    context = _repo.dataset_context()
    theme_line = f"Focus theme: {theme}." if theme else "Choose the strongest positive theme from the data."
    meta = analytics["meta"]

    system = (
        "You are the Storytelling Agent for ImpactLens AI. "
        "Create an ethical, human-centred impact narrative using ONLY de-identified quotes and aggregate metrics. "
        "Never use real names or identifying details. "
        "Paraphrase quotes if needed. End with 2-3 cited data points from the dataset."
    )
    user = (
        f"{theme_line}\n\n"
        f"Available positive quotes (de-identified, sample):\n{positive_quotes}\n\n"
        f"Dataset summary for metrics:\n{context}"
    )

    story = complete_with_context(system, user, temperature=0.5)
    return {
        "story": story,
        "quotes_used_count": len(positive_quotes),
        "citations": [
            "Narrative built from de-identified student feedback in Lifechanger session data.",
            f"Source: {meta['dataset_name']} ({meta['record_count']} sessions).",
        ],
    }
