import json
import os
from functools import lru_cache
from pathlib import Path

from data.analytics import build_analytics, llm_context_summary

_DATA_DIR = Path(__file__).resolve().parent
_DEFAULT_FILE = _DATA_DIR / "lifechanger_school_partner_input_data_10000.json"
_LEGACY_FILE = _DATA_DIR / "sample_programs.json"


class MockDataRepository:
    def __init__(self, filename: str | None = None):
        env_path = os.environ.get("DATASET_FILE")
        if filename:
            self.filename = Path(filename)
        elif env_path:
            path = Path(env_path)
            if path.is_absolute():
                self.filename = path
            else:
                backend_root = _DATA_DIR.parent
                candidates = [path, backend_root / path, _DATA_DIR / path.name]
                self.filename = next((c for c in candidates if c.exists()), backend_root / path)
        else:
            self.filename = _DEFAULT_FILE if _DEFAULT_FILE.exists() else _LEGACY_FILE

    def load_dataset(self) -> dict:
        with open(self.filename, "r", encoding="utf-8") as file:
            return json.load(file)

    @lru_cache(maxsize=1)
    def get_analytics(self) -> dict:
        raw = self.load_dataset()
        if "records" in raw:
            return build_analytics(raw)
        return _legacy_to_analytics(raw)

    def dataset_context(self) -> str:
        raw = self.load_dataset()
        if "records" in raw:
            return llm_context_summary(raw, self.get_analytics())
        return json.dumps(raw, indent=2)

    def is_lifechanger_dataset(self) -> bool:
        raw = self.load_dataset()
        return "records" in raw


def _legacy_to_analytics(data: dict) -> dict:
    """Map small sample_programs.json shape to analytics dict."""
    programs = data.get("programs", [])
    at_risk = [
        {"id": p["id"], "name": p["name"], "cohort": p["cohort"]}
        for p in programs
        if p.get("status") == "at_risk"
        or p.get("attendance_rate", 1) < 0.75
        or p.get("wellbeing_score_avg", 5) < 3.3
    ]
    samples = data.get("feedback_samples", [])
    from collections import Counter

    sentiments = Counter(s.get("sentiment") for s in samples)
    themes = Counter(s.get("theme") for s in samples)
    return {
        "meta": {
            "dataset_name": "sample_programs",
            "description": "Legacy mock export",
            "export_date": data.get("export_date"),
            "record_count": len(programs),
            "scale_notes": None,
        },
        "summary": {
            "total_programs": len(programs),
            "total_participants": sum(p.get("participants", 0) for p in programs),
            "total_sessions": sum(p.get("sessions_completed", 0) for p in programs),
            "unique_schools": None,
            "avg_attendance": round(
                sum(p["attendance_rate"] for p in programs) / max(len(programs), 1), 2
            ),
            "avg_wellbeing": round(
                sum(p["wellbeing_score_avg"] for p in programs) / max(len(programs), 1),
                2,
            ),
            "at_risk_count": len(at_risk),
        },
        "programs": [
            {
                "id": p["id"],
                "name": p["name"],
                "cohort": p["cohort"],
                "participants": p.get("participants", 0),
                "sessions_completed": p.get("sessions_completed", 0),
                "attendance_rate": p.get("attendance_rate", 0),
                "wellbeing_score_avg": p.get("wellbeing_score_avg", 0),
                "mentor_rating_avg": p.get("mentor_rating_avg"),
                "status": p.get("status", "active"),
            }
            for p in programs
        ],
        "feedback_samples": samples,
        "quarterly_trends": data.get("quarterly_trends", {}),
        "funder_highlights": data.get("funder_highlights", {}),
        "at_risk_programs": at_risk,
        "sentiment_distribution": dict(sentiments),
        "top_themes": themes.most_common(10),
    }
