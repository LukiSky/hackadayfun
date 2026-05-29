"""Traditional ML predictions for workshop wellbeing, at-risk flags, and sentiment."""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    r2_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from data.analytics import (
    ATTENDANCE_RISK_THRESHOLD,
    WELLBEING_RISK_THRESHOLD,
    _classify_feedback,
    _session_attendance_rate,
    _session_wellbeing,
)
from data.chart_catalog import CHART_PALETTE, _bar_chart, _line_chart, _pie_chart

NUMERIC_FEATURES = (
    "icsea",
    "students",
    "facilitator_rating",
    "response_count",
    "positive_ratio",
    "was_compromised",
    "did_deviate",
)
CATEGORICAL_FEATURES = ("topic", "year_level", "school_region")
MIN_WORKSHOPS = 24
MIN_SENTIMENT_SAMPLES = 80


def _workshop_is_at_risk(record: dict, wellbeing: float, attendance: float) -> bool:
    low_rating = record.get("facilitator_rating") is not None and record["facilitator_rating"] < 3.0
    return (
        attendance < ATTENDANCE_RISK_THRESHOLD
        or wellbeing < WELLBEING_RISK_THRESHOLD
        or bool(record.get("was_compromised"))
        or bool(record.get("did_deviate"))
        or low_rating
    )


def _build_workshop_rows(raw: dict) -> list[dict]:
    if raw.get("format") != "lifechanger_csv":
        return []

    records = raw.get("records") or []
    responses = raw.get("responses") or []
    by_workshop: dict[str, list[dict]] = defaultdict(list)
    for row in responses:
        by_workshop[row["workshop_code"]].append(row)

    rows: list[dict] = []
    for record in records:
        workshop_code = record["session_id"]
        workshop_responses = by_workshop.get(workshop_code, [])
        first = workshop_responses[0] if workshop_responses else {}

        wellbeing = _session_wellbeing(record)
        if wellbeing is None:
            continue

        attendance = _session_attendance_rate(record)
        sentiments = [
            _classify_feedback(r["answer_text"])
            for r in workshop_responses
            if r.get("answer_text")
        ]
        positive_ratio = sentiments.count("positive") / len(sentiments) if sentiments else 0.5

        rows.append(
            {
                "workshop_code": workshop_code,
                "school_name": record.get("school_name") or first.get("school_name") or "Unknown",
                "topic": record.get("program_name") or first.get("workshop_topic") or "unknown",
                "year_level": str(first.get("year_level") or "unknown"),
                "school_region": first.get("school_region") or "unknown",
                "icsea": float(first.get("school_icsea_percentile") or 50.0),
                "students": float(record.get("registered_count") or first.get("number_of_students") or 0),
                "facilitator_rating": float(record.get("facilitator_rating") or 3.5),
                "response_count": float(record.get("response_count") or len(workshop_responses)),
                "positive_ratio": positive_ratio,
                "was_compromised": int(bool(record.get("was_compromised"))),
                "did_deviate": int(bool(record.get("did_deviate"))),
                "wellbeing_actual": float(wellbeing),
                "at_risk_actual": int(
                    _workshop_is_at_risk(record, wellbeing, attendance)
                ),
            }
        )
    return rows


def _matrix_from_rows(rows: list[dict]) -> np.ndarray:
    numeric = np.array([[r[name] for name in NUMERIC_FEATURES] for r in rows], dtype=float)
    categorical = np.array(
        [[r[name] for name in CATEGORICAL_FEATURES] for r in rows],
        dtype=str,
    )
    return np.hstack([numeric, categorical])


def _feature_matrix(rows: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    y_wellbeing = np.array([r["wellbeing_actual"] for r in rows])
    y_risk = np.array([r["at_risk_actual"] for r in rows])
    return _matrix_from_rows(rows), y_wellbeing, y_risk


def _build_preprocessor() -> ColumnTransformer:
    n_num = len(NUMERIC_FEATURES)
    n_cat = len(CATEGORICAL_FEATURES)
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), list(range(n_num))),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                list(range(n_num, n_num + n_cat)),
            ),
        ]
    )


def _train_wellbeing_model(rows: list[dict]) -> dict:
    X, y, _ = _feature_matrix(rows)
    if len(rows) < MIN_WORKSHOPS:
        return {"trained": False, "reason": f"Need at least {MIN_WORKSHOPS} workshops"}

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42
    )
    pipeline = Pipeline(
        [
            ("prep", _build_preprocessor()),
            ("model", RandomForestRegressor(n_estimators=120, random_state=42, max_depth=8)),
        ]
    )
    pipeline.fit(X_train, y_train)
    preds = pipeline.predict(X_test)
    metrics = {
        "r2": round(float(r2_score(y_test, preds)), 3),
        "mae": round(float(mean_absolute_error(y_test, preds)), 3),
        "samples_train": len(y_train),
        "samples_test": len(y_test),
    }

    all_preds = pipeline.predict(X)
    workshop_predictions = []
    for row, pred in zip(rows, all_preds, strict=False):
        workshop_predictions.append(
            {
                "workshop_code": row["workshop_code"],
                "school_name": row["school_name"],
                "topic": row["topic"],
                "wellbeing_actual": round(row["wellbeing_actual"], 2),
                "wellbeing_predicted": round(float(pred), 2),
                "residual": round(float(pred) - row["wellbeing_actual"], 2),
            }
        )

    numeric_model = Pipeline(
        [
            ("scale", StandardScaler()),
            ("model", RandomForestRegressor(n_estimators=80, random_state=42, max_depth=6)),
        ]
    )
    X_num = np.array([[r[name] for name in NUMERIC_FEATURES] for r in rows])
    numeric_model.fit(X_num, y)
    importances = numeric_model.named_steps["model"].feature_importances_
    feature_importance = [
        {"label": name.replace("_", " ").title(), "value": round(float(score), 3)}
        for name, score in sorted(
            zip(NUMERIC_FEATURES, importances, strict=False),
            key=lambda item: item[1],
            reverse=True,
        )
    ]

    return {
        "trained": True,
        "algorithm": "RandomForestRegressor",
        "target": "wellbeing_score",
        "metrics": metrics,
        "feature_importance": feature_importance,
        "workshop_predictions": workshop_predictions,
        "pipeline": pipeline,
    }


def _train_at_risk_model(rows: list[dict]) -> dict:
    X, _, y = _feature_matrix(rows)
    if len(rows) < MIN_WORKSHOPS:
        return {"trained": False, "reason": f"Need at least {MIN_WORKSHOPS} workshops"}

    positive_rate = float(y.mean())
    if positive_rate in (0.0, 1.0):
        return {"trained": False, "reason": "At-risk labels are all the same class"}

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    pipeline = Pipeline(
        [
            ("prep", _build_preprocessor()),
            (
                "model",
                GradientBoostingClassifier(random_state=42, max_depth=4, n_estimators=100),
            ),
        ]
    )
    pipeline.fit(X_train, y_train)
    preds = pipeline.predict(X_test)
    prob = pipeline.predict_proba(X_test)[:, 1]
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, preds)), 3),
        "f1": round(float(f1_score(y_test, preds, zero_division=0)), 3),
        "avg_predicted_risk": round(float(prob.mean()), 3),
        "samples_train": len(y_train),
        "samples_test": len(y_test),
    }

    all_probs = pipeline.predict_proba(X)[:, 1]
    by_topic: dict[str, list[float]] = defaultdict(list)
    for row, p in zip(rows, all_probs, strict=False):
        by_topic[row["topic"]].append(float(p))

    topic_risk = [
        {
            "topic": topic,
            "avg_risk_probability": round(mean(values), 3),
            "workshop_count": len(values),
        }
        for topic, values in sorted(by_topic.items(), key=lambda item: -mean(item[1]))
    ]

    return {
        "trained": True,
        "algorithm": "GradientBoostingClassifier",
        "target": "at_risk_flag",
        "metrics": metrics,
        "topic_risk": topic_risk,
        "pipeline": pipeline,
    }


def _train_sentiment_model(raw: dict) -> dict:
    responses = raw.get("responses") or []
    samples = [
        (r["answer_text"], _classify_feedback(r["answer_text"]))
        for r in responses
        if len((r.get("answer_text") or "").strip()) >= 20
    ]
    if len(samples) < MIN_SENTIMENT_SAMPLES:
        return {
            "trained": False,
            "reason": f"Need at least {MIN_SENTIMENT_SAMPLES} text responses",
        }

    texts, labels = zip(*samples, strict=False)
    label_counts = Counter(labels)
    if len(label_counts) < 2:
        return {"trained": False, "reason": "Sentiment labels lack class diversity"}

    y = np.array([1 if label == "positive" else 0 for label in labels])
    if y.mean() in (0.0, 1.0):
        return {"trained": False, "reason": "Sentiment labels are all one class"}

    X_train, X_test, y_train, y_test = train_test_split(
        list(texts), y, test_size=0.25, random_state=42, stratify=y
    )
    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(max_features=4000, ngram_range=(1, 2), min_df=2)),
            ("clf", LogisticRegression(max_iter=400, random_state=42)),
        ]
    )
    pipeline.fit(X_train, y_train)
    preds = pipeline.predict(X_test)
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, preds)), 3),
        "f1_positive": round(float(f1_score(y_test, preds, zero_division=0)), 3),
        "samples_train": len(y_train),
        "samples_test": len(y_test),
        "baseline_keyword_positive_rate": round(float(y.mean()), 3),
    }

    confusion = {
        "true_positive": int(((preds == 1) & (y_test == 1)).sum()),
        "false_positive": int(((preds == 1) & (y_test == 0)).sum()),
        "true_negative": int(((preds == 0) & (y_test == 0)).sum()),
        "false_negative": int(((preds == 0) & (y_test == 1)).sum()),
    }

    return {
        "trained": True,
        "algorithm": "TfidfVectorizer + LogisticRegression",
        "target": "positive_sentiment",
        "metrics": metrics,
        "label_distribution": dict(label_counts),
        "confusion": confusion,
    }


def _build_wellbeing_forecast(analytics: dict) -> dict:
    trends = analytics.get("quarterly_trends") or {}
    terms = trends.get("terms") or []
    wellbeing = trends.get("wellbeing_avg") or []
    if len(terms) < 3 or len(wellbeing) < 3:
        return {"trained": False, "reason": "Need at least 3 terms of wellbeing history"}

    X = np.arange(len(wellbeing)).reshape(-1, 1)
    y = np.array(wellbeing, dtype=float)
    model = LinearRegression()
    model.fit(X, y)

    future_terms = [f"Forecast +{i}" for i in range(1, 3)]
    future_X = np.arange(len(wellbeing), len(wellbeing) + 2).reshape(-1, 1)
    forecast_values = model.predict(future_X)

    history = [
        {"label": term, "actual": round(float(val), 2), "predicted": None}
        for term, val in zip(terms, wellbeing, strict=False)
    ]
    fitted = model.predict(X)
    for row, fit in zip(history, fitted, strict=False):
        row["predicted"] = round(float(fit), 2)

    forecast_rows = [
        {"label": term, "actual": None, "predicted": round(float(val), 2)}
        for term, val in zip(future_terms, forecast_values, strict=False)
    ]

    return {
        "trained": True,
        "algorithm": "LinearRegression",
        "target": "wellbeing_by_term",
        "metrics": {"r2": round(float(r2_score(y, fitted)), 3)},
        "series": [
            {"label": row["label"], "actual": row["actual"], "predicted": row["predicted"]}
            for row in history + forecast_rows
        ],
    }


def run_ml_predictions(raw: dict, analytics: dict) -> dict:
    """Train lightweight sklearn models and return metrics + workshop-level predictions."""
    rows = _build_workshop_rows(raw)
    wellbeing = _train_wellbeing_model(rows)
    at_risk = _train_at_risk_model(rows)
    sentiment = _train_sentiment_model(raw)
    forecast = _build_wellbeing_forecast(analytics)

    models = []
    for item in (wellbeing, at_risk, sentiment, forecast):
        entry = {k: v for k, v in item.items() if k != "pipeline"}
        models.append(entry)

    high_risk_workshops = []
    if at_risk.get("trained") and wellbeing.get("trained"):
        prob_by_code = {}
        if at_risk.get("pipeline") is not None:
            X, _, _ = _feature_matrix(rows)
            probs = at_risk["pipeline"].predict_proba(X)[:, 1]
            prob_by_code = {
                row["workshop_code"]: float(p) for row, p in zip(rows, probs, strict=False)
            }
        for pred in wellbeing.get("workshop_predictions", []):
            code = pred["workshop_code"]
            risk_prob = prob_by_code.get(code)
            if risk_prob is None:
                continue
            if risk_prob >= 0.55 or pred["wellbeing_predicted"] < WELLBEING_RISK_THRESHOLD:
                high_risk_workshops.append(
                    {
                        **pred,
                        "risk_probability": round(risk_prob, 3),
                    }
                )
        high_risk_workshops.sort(key=lambda row: row.get("risk_probability", 0), reverse=True)

    return {
        "available": True,
        "workshop_count": len(rows),
        "models": models,
        "wellbeing": {k: v for k, v in wellbeing.items() if k != "pipeline"},
        "at_risk": {k: v for k, v in at_risk.items() if k != "pipeline"},
        "sentiment": sentiment,
        "forecast": forecast,
        "high_risk_workshops": high_risk_workshops[:12],
        "summary": {
            "models_trained": sum(1 for m in models if m.get("trained")),
            "high_risk_workshops": len(high_risk_workshops),
            "avg_wellbeing_actual": round(mean(r["wellbeing_actual"] for r in rows), 2)
            if rows
            else None,
        },
    }


def build_prediction_charts(predictions: dict) -> list[dict]:
    """Turn ML outputs into chart specs compatible with ChartPanel."""
    if not predictions.get("available"):
        return []

    charts: list[dict] = []
    wellbeing = predictions.get("wellbeing") or {}
    at_risk = predictions.get("at_risk") or {}
    sentiment = predictions.get("sentiment") or {}
    forecast = predictions.get("forecast") or {}

    if wellbeing.get("trained"):
        by_topic: dict[str, list[dict]] = defaultdict(list)
        for row in wellbeing.get("workshop_predictions") or []:
            by_topic[row["topic"]].append(row)

        topic_compare = []
        for topic, items in sorted(by_topic.items()):
            topic_compare.append(
                {
                    "label": topic,
                    "actual": round(mean(i["wellbeing_actual"] for i in items), 2),
                    "predicted": round(mean(i["wellbeing_predicted"] for i in items), 2),
                }
            )
        if topic_compare:
            charts.append(
                {
                    "id": "ml_predicted_vs_actual",
                    "title": "Predicted vs actual wellbeing by topic",
                    "type": "bar",
                    "description": "RandomForest workshop wellbeing model — topic averages.",
                    "xKey": "label",
                    "valueKey": "actual",
                    "series": [
                        {"key": "actual", "name": "Actual"},
                        {"key": "predicted", "name": "Predicted"},
                    ],
                    "data": topic_compare,
                    "palette": CHART_PALETTE,
                    "layout": "powerbi",
                }
            )

        importances = wellbeing.get("feature_importance") or []
        if importances:
            charts.append(
                _bar_chart(
                    "ml_feature_importance",
                    "Wellbeing model — feature importance",
                    importances,
                    horizontal=True,
                    description="RandomForest importances on numeric workshop features.",
                )
            )

    if at_risk.get("trained"):
        topic_risk = at_risk.get("topic_risk") or []
        if topic_risk:
            charts.append(
                _bar_chart(
                    "ml_risk_probability_by_topic",
                    "Predicted at-risk probability by topic",
                    [
                        {
                            "label": row["topic"],
                            "value": round(row["avg_risk_probability"] * 100, 1),
                        }
                        for row in topic_risk[:10]
                    ],
                    horizontal=True,
                    description="GradientBoosting average probability of at-risk delivery (%).",
                )
            )

    if sentiment.get("trained"):
        confusion = sentiment.get("confusion") or {}
        if confusion:
            charts.append(
                _bar_chart(
                    "ml_sentiment_confusion",
                    "Sentiment classifier — test set breakdown",
                    [
                        {"label": "True positive", "value": confusion.get("true_positive", 0)},
                        {"label": "False positive", "value": confusion.get("false_positive", 0)},
                        {"label": "True negative", "value": confusion.get("true_negative", 0)},
                        {"label": "False negative", "value": confusion.get("false_negative", 0)},
                    ],
                    description="TF-IDF + LogisticRegression vs keyword sentiment labels.",
                )
            )
        label_dist = sentiment.get("label_distribution") or {}
        if label_dist:
            charts.append(
                _pie_chart(
                    "ml_sentiment_label_mix",
                    "Training label mix (keyword baseline)",
                    [{"label": k.title(), "value": v} for k, v in label_dist.items()],
                    description="Distribution of keyword-classified sentiment used as ML labels.",
                )
            )

    if forecast.get("trained"):
        series_rows = forecast.get("series") or []
        charts.append(
            {
                "id": "ml_wellbeing_forecast",
                "title": "Wellbeing trend + linear forecast",
                "type": "line",
                "description": "Historical wellbeing by term with 2-term linear forecast.",
                "xKey": "label",
                "series": [
                    {"key": "actual", "name": "Actual"},
                    {"key": "predicted", "name": "Model / forecast"},
                ],
                "data": series_rows,
                "palette": CHART_PALETTE,
                "layout": "powerbi",
            }
        )

    high_risk = predictions.get("high_risk_workshops") or []
    if high_risk:
        charts.append(
            _bar_chart(
                "ml_high_risk_workshops",
                "Workshops flagged by ML ensemble",
                [
                    {
                        "label": f"{row['topic']} · {row['school_name'][:18]}",
                        "value": round(row.get("risk_probability", 0) * 100, 1),
                    }
                    for row in high_risk[:8]
                ],
                horizontal=True,
                description="Combined wellbeing + at-risk probability signals.",
            )
        )

    return charts
