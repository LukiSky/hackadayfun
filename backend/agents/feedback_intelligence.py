from collections import Counter

from data.repository import MockDataRepository

_repo = MockDataRepository()


def get_sentiment_trends() -> dict:
    a = _repo.get_analytics()
    samples = a["feedback_samples"]

    by_program: dict[str, dict] = {}
    for sample in samples:
        pid = sample["program_id"]
        entry = by_program.setdefault(
            pid, {"positive": 0, "mixed": 0, "negative": 0, "themes": []}
        )
        entry[sample["sentiment"]] += 1
        entry["themes"].append(sample.get("theme"))

    return {
        "total_feedback_samples": len(samples),
        "sentiment_distribution": a["sentiment_distribution"],
        "top_themes": a["top_themes"],
        "by_program": by_program,
        "quarterly_trends": a["quarterly_trends"],
        "citations": [
            f"Based on {len(samples)} de-identified student feedback quotes from {a['meta']['record_count']} sessions.",
            f"Top themes: {', '.join(t[0] for t in a['top_themes'][:5])}.",
        ],
    }
