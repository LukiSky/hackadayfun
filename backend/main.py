"""
ImpactLens AI + F5-TTS unified FastAPI backend.

Run: uvicorn main:app --host 0.0.0.0 --port 5000 --reload
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Prefer backend/.env so DATASET_FILE points at the LifeChanger CSV, not a stale shell export.
load_dotenv(BACKEND_ROOT / ".env", override=True)

from routers import impact, tts

FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
F5_TTS_ENABLED = os.environ.get("F5_TTS_ENABLED", "1") == "1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Drop any stale singleton (e.g. created with empty F5_TTS_DEVICE before .env load).
    from tts.synthesis.service import F5TtsService

    F5TtsService._instance = None
    app.state.tts_enabled = F5_TTS_ENABLED
    app.state.tts_service = None  # lazy-loaded on first POST /api/tts/speak
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="ImpactLens AI",
        description="Lifechanger impact analytics API with optional F5-TTS speech synthesis.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[FRONTEND_ORIGIN, "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    def index():
        return {
            "service": "ImpactLens AI API",
            "frontend": FRONTEND_ORIGIN,
            "endpoints": {
                "health": "/api/health",
                "dataset": "/api/dataset",
                "dataset_csv": "GET /api/dataset/csv",
                "dashboard": "/api/dashboard",
                "analyze": "/api/analyze",
                "insights": "GET /api/insights · POST /api/insights",
                "chat_message": "POST /api/chat/message",
                "llm_orchestrate": "POST /api/llm/orchestrate",
                "llm_regenerate_story": "POST /api/llm/regenerate-story",
                "dashboard_editor": "Stateful mutations via POST /api/llm/orchestrate (mutations[])",
                "report_export": "Frontend Export to PDF via print CSS (#report-export-root, A4 landscape)",
                "dashboard_execute": "POST /api/dashboard/execute",
                "ask": "POST /api/ask",
                "ask_why": "POST /api/ask-why",
                "report": "POST /api/report",
                "story": "POST /api/story",
                "charts": "GET /api/charts",
                "charts_generate": "POST /api/charts/generate",
                "predictions": "GET /api/predictions",
                "langchain_status": "GET /api/langchain/status",
                "langchain_architecture": "GET /api/langchain/architecture",
                "ask_stream": "POST /api/ask/stream",
                "chat": "POST /api/chat",
                "chat_stream": "POST /api/chat/stream",
                "chat_export_pdf": "POST /api/chat/export-pdf",
                "tts_speak": "POST /api/tts/speak",
                "tts_health": "GET /api/tts/health",
                "tts_speakers": "GET /api/tts/speakers",
            },
        }

    app.include_router(impact.router)
    app.include_router(tts.router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        reload=True,
    )
