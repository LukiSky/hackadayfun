import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

# Ensure backend root is on path when running app.py directly
BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

load_dotenv(BACKEND_ROOT / ".env")

from data.repository import MockDataRepository

from agents.ask_agent import ask_data_question
from agents.dashboard_orchestrator import orchestrate_dashboard_command
from agents.data_analyst import analyze_program_data, get_dashboard_metrics
from agents.feedback_intelligence import get_sentiment_trends
from agents.report_writer import generate_report
from agents.risk_opportunity import identify_risks_and_opportunities
from agents.storytelling import generate_impact_story

app = Flask(__name__)
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
CORS(app, resources={r"/api/*": {"origins": FRONTEND_ORIGIN}})


@app.route("/", methods=["GET"])
def index():
    return jsonify(
        {
            "service": "ImpactLens AI API",
            "message": "Use the React app for the UI, or call /api/* endpoints below.",
            "frontend": FRONTEND_ORIGIN,
            "endpoints": {
                "health": "/api/health",
                "dataset": "/api/dataset",
                "dashboard": "/api/dashboard",
                "analyze": "/api/analyze",
                "ask": "POST /api/ask",
                "orchestrate": "POST /api/llm/orchestrate",
                "report": "POST /api/report",
                "story": "POST /api/story",
            },
        }
    )


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "ImpactLens AI"})


@app.route("/api/langchain/status", methods=["GET"])
def langchain_status():
    token = bool(os.environ.get("HF_TOKEN"))
    return jsonify(
        {
            "success": True,
            "llm_configured": token,
            "model": os.environ.get("HF_MODEL", "google/gemma-2-9b-it:novita"),
            "mode": "huggingface_router" if token else "local_analytics_fallback",
            "orchestrate": "/api/llm/orchestrate",
        }
    )


@app.route("/api/dataset", methods=["GET"])
def dataset_info():
    try:
        repo = MockDataRepository()
        analytics = repo.get_analytics()
        return jsonify(
            {
                "success": True,
                "data": {
                    "file": repo.filename.name,
                    "path": str(repo.filename),
                    "meta": analytics["meta"],
                    "summary": analytics["summary"],
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/dashboard", methods=["GET"])
def get_dashboard():
    try:
        metrics = get_dashboard_metrics()
        return jsonify({"success": True, "data": metrics})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analyze", methods=["GET"])
def analyze():
    try:
        analysis = analyze_program_data()
        sentiment = get_sentiment_trends()
        risks = identify_risks_and_opportunities()
        return jsonify(
            {
                "success": True,
                "data": {
                    "analysis": analysis,
                    "sentiment": sentiment,
                    "risks_and_opportunities": risks,
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/llm/orchestrate", methods=["POST"])
def llm_orchestrate():
    body = request.get_json(silent=True) or {}
    user_prompt = (body.get("userPrompt") or body.get("prompt") or "").strip()
    if not user_prompt:
        return jsonify({"success": False, "error": "userPrompt is required"}), 400
    try:
        result = orchestrate_dashboard_command(
            user_prompt=user_prompt,
            current_widgets=body.get("currentDashboardWidgets") or [],
            dashboard_state=body.get("dashboardState") or {},
            interactive=body.get("interactive", True),
        )
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ask", methods=["POST"])
def ask():
    body = request.get_json(silent=True) or {}
    question = (body.get("question") or "").strip()
    if not question:
        return jsonify({"success": False, "error": "question is required"}), 400
    try:
        result = ask_data_question(question)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/report", methods=["POST"])
def report():
    body = request.get_json(silent=True) or {}
    audience = (body.get("audience") or "internal").strip()
    try:
        result = generate_report(audience)
        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/story", methods=["POST"])
def story():
    body = request.get_json(silent=True) or {}
    theme = body.get("theme")
    try:
        result = generate_impact_story(theme)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5000)), debug=True)
