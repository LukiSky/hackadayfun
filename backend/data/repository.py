import json
import os
from pathlib import Path

from dotenv import load_dotenv

from data.analytics import build_analytics, llm_context_summary

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_ROOT / ".env", override=True)
from data.analytics_csv import build_analytics_csv
from data.csv_loader import load_lifechanger_csv
from data.success_analytics import enrich_analytics_with_success_vision

_DATA_DIR = Path(__file__).resolve().parent
_DEFAULT_CSV = _DATA_DIR / "LifeChanger_Sample_Data_Populated_10000.csv"
_DEFAULT_JSON = _DATA_DIR / "lifechanger_school_partner_input_data_10000.json"
_LEGACY_FILE = _DATA_DIR / "sample_programs.json"

_analytics_cache: dict[str, dict] = {}
_predictions_cache: dict[str, dict] = {}


def _resolve_dataset_path(filename: str | None = None) -> Path:
    """Resolve LifeChanger CSV/JSON for local dev and Vercel serverless layouts."""
    if filename:
        path = Path(filename)
        return path if path.is_absolute() else (_DATA_DIR.parent / path).resolve()

    env_path = os.environ.get("DATASET_FILE")
    if env_path:
        path = Path(env_path)
        if path.is_absolute():
            return path
        backend_root = _DATA_DIR.parent
        candidates = [
            path,
            backend_root / path,
            _DATA_DIR / path.name,
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()
        return (_DATA_DIR / path.name).resolve()

    if _DEFAULT_CSV.is_file():
        return _DEFAULT_CSV.resolve()
    if _DEFAULT_JSON.is_file():
        return _DEFAULT_JSON.resolve()
    return _LEGACY_FILE.resolve()


class MockDataRepository:
    def __init__(self, filename: str | None = None):
        self.filename = _resolve_dataset_path(filename)

    def load_dataset(self) -> dict:
        if not self.filename.is_file():
            raise FileNotFoundError(
                f"Dataset not found: {self.filename}. "
                f"Set DATASET_FILE or commit backend/data/LifeChanger_Sample_Data_Populated_10000.csv."
            )
        if self.filename.suffix.lower() == ".csv":
            return load_lifechanger_csv(self.filename)
        with open(self.filename, "r", encoding="utf-8") as file:
            return json.load(file)

    def get_analytics(self) -> dict:
        key = str(self.filename.resolve())
        if key in _analytics_cache:
            return _analytics_cache[key]

        raw = self.load_dataset()
        if raw.get("format") == "lifechanger_csv":
            analytics = build_analytics_csv(raw)
            analytics = enrich_analytics_with_success_vision(analytics, raw)
        elif "records" in raw:
            analytics = build_analytics(raw)
        else:
            analytics = _legacy_to_analytics(raw)

        _analytics_cache[key] = analytics
        return analytics

    def dataset_context(self) -> str:
        raw = self.load_dataset()
        analytics = self.get_analytics()
        if raw.get("format") == "lifechanger_csv" or "records" in raw:
            return llm_context_summary(raw, analytics)
        return json.dumps(raw, indent=2)

    def is_lifechanger_dataset(self) -> bool:
        raw = self.load_dataset()
        return raw.get("format") == "lifechanger_csv" or "records" in raw

    def get_predictions(self) -> dict:
        key = str(self.filename.resolve())
        if key in _predictions_cache:
            return _predictions_cache[key]

        raw = self.load_dataset()
        if raw.get("format") != "lifechanger_csv":
            result = {
                "available": False,
                "reason": "ML predictions require the LifeChanger CSV dataset.",
            }
            _predictions_cache[key] = result
            return result

        from data.prediction import run_ml_predictions

        analytics = self.get_analytics()
        result = run_ml_predictions(raw, analytics)
        _predictions_cache[key] = result
        return result


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
