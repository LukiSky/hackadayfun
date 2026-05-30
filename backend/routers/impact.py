"""ImpactLens AI analytics and LLM routes."""

import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from agents.ask_agent import ask_data_question
from agents.chart_service import generate_charts_for_request, list_all_charts
from agents.dashboard_chat import handle_chat_message
from agents.dashboard_insights import generate_dashboard_insight
from agents.dashboard_supervisor import regenerate_story_for_detail
from agents.llm_orchestrator import orchestrate_llm_command
from agents.data_analyst import analyze_program_data, get_dashboard_metrics
from agents.feedback_intelligence import get_sentiment_trends
from agents.langchain_service import (
    ask_stream_finalize,
    ask_stream_tokens,
    ask_why_langchain,
    chat_message,
    chat_stream_finalize,
    chat_stream_tokens,
    generate_insight_cards_langchain,
    langchain_architecture_status,
    langchain_status,
)
from agents.pdf_export import build_chat_pdf
from agents.report_writer import generate_report
from agents.risk_opportunity import identify_risks_and_opportunities
from agents.storytelling import generate_impact_story
from agents.success_vision import get_success_vision_status
from data.repository import MockDataRepository
from data.prediction import build_prediction_charts

router = APIRouter(tags=["impact"])


class AskBody(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: str | None = Field(default=None, description="Conversation window memory id")


class ChatBody(BaseModel):
    message: str = Field(..., min_length=1)
    mode: str = Field(
        default="both",
        description="qa = storytelling Q&A only; charts = visuals + narrative; both = Q&A with charts when relevant",
    )
    session_id: str | None = None


class ChatMessageItem(BaseModel):
    role: str
    content: str = ""
    charts: list[dict] = Field(default_factory=list)


class ChatExportPdfBody(BaseModel):
    messages: list[ChatMessageItem] = Field(..., min_length=1)
    mode: str = "both"
    session_id: str | None = None


class ReportBody(BaseModel):
    audience: str = "internal"


class StoryBody(BaseModel):
    theme: str | None = None


class AskWhyBody(BaseModel):
    subject: str = Field(..., min_length=3)
    evidence: list[str] = Field(default_factory=list)


class ChartGenerateBody(BaseModel):
    question: str = Field(..., min_length=1)
    chart_type: str | None = Field(
        default=None,
        description="Optional filter: bar, pie, line, horizontalBar",
    )


class DashboardInsightBody(BaseModel):
    question: str = ""
    mode: str = "chat"
    activeFilters: dict = Field(default_factory=dict)
    aggregates: dict = Field(default_factory=dict)
    evidenceRows: list[dict] = Field(default_factory=list)
    availableFields: dict = Field(default_factory=dict)


class ChatMessageBody(BaseModel):
    text: str = Field(..., min_length=1)
    useSpeaker: bool = True
    session_id: str | None = None
    activeFilters: dict = Field(default_factory=dict)
    aggregates: dict = Field(default_factory=dict)
    evidenceRows: list[dict] = Field(default_factory=list)
    availableFields: dict = Field(default_factory=dict)
    pendingDashboardCommands: list[dict] = Field(default_factory=list)


class DashboardExecuteBody(BaseModel):
    action: str = Field(..., min_length=1)
    targetWidgetId: str | None = None
    value: dict | list | str | int | float | bool | None = None


class RegenerateStoryBody(BaseModel):
    detailLevel: str = "Standard"
    aggregates: dict = Field(default_factory=dict)
    activeContext: dict = Field(default_factory=dict)
    chartConfig: dict | None = None
    userPrompt: str | None = None


class OrchestrateBody(BaseModel):
    userPrompt: str = Field(..., min_length=1)
    currentDashboardState: dict = Field(default_factory=dict)
    activeFilters: dict = Field(default_factory=dict)
    aggregates: dict = Field(default_factory=dict)
    evidenceRows: list[dict] = Field(default_factory=list)
    availableFields: dict = Field(default_factory=dict)
    dynamicWidgetIds: list[str] = Field(default_factory=list)
    useSpeaker: bool = True
    storyMode: bool = Field(
        default=False,
        description="Force DataVisualization + Storytelling + Audio chains",
    )
    questionMode: bool = Field(
        default=False,
        description="Plain analytical question — detailed evidence-backed answer, no dashboard rebuild",
    )
    currentDashboardWidgets: list[dict] = Field(
        default_factory=list,
        description="CURRENT_DASHBOARD_STATE injected into DashboardEditorChain",
    )
    session_id: str | None = Field(
        default=None,
        description="Conversation session for multi-turn chat memory",
    )


_ALLOWED_DASHBOARD_ACTIONS = frozenset(
    {
        "filter-table",
        "focus-widget",
        "switch-tab",
        "update-data",
        "scroll-to",
        "clear-all-widgets",
        "update-state",
        "update-title",
        "render-widget",
        "render-chart",
        "remove-element",
    }
)


@router.get("/api/health")
def health():
    repo = MockDataRepository()
    row_count = None
    try:
        analytics = repo.get_analytics()
        summary = analytics.get("summary") or {}
        row_count = summary.get("valid_responses") or analytics.get("meta", {}).get("record_count")
    except Exception:
        pass
    return {
        "status": "ok",
        "service": "ImpactLens AI",
        "llm_configured": bool(os.environ.get("HF_TOKEN")),
        "dataset_file": repo.filename.name,
        "row_count": row_count,
    }


@router.get("/api/dataset/csv")
def dataset_csv():
    """Stream the canonical LifeChanger CSV used by analytics and LLM."""
    repo = MockDataRepository()
    path = repo.filename
    if path.suffix.lower() != ".csv":
        raise HTTPException(status_code=404, detail="Dataset is not a CSV file")
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Dataset file not found: {path}")
    return FileResponse(
        path,
        media_type="text/csv",
        filename=path.name,
        headers={"Content-Disposition": f'inline; filename="{path.name}"'},
    )


@router.get("/api/dataset")
def dataset_info():
    try:
        repo = MockDataRepository()
        analytics = repo.get_analytics()
        return {
            "success": True,
            "data": {
                "file": repo.filename.name,
                "path": str(repo.filename),
                "meta": analytics["meta"],
                "summary": analytics["summary"],
            },
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/dashboard")
def get_dashboard():
    try:
        return {"success": True, "data": get_dashboard_metrics()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/analyze")
def analyze():
    try:
        repo = MockDataRepository()
        analytics = repo.get_analytics()
        return {
            "success": True,
            "data": {
                "analysis": analyze_program_data(),
                "sentiment": get_sentiment_trends(),
                "risks_and_opportunities": identify_risks_and_opportunities(),
                "emerging_themes": analytics.get("emerging_themes", []),
                "correlations": analytics.get("correlations", []),
                "early_warnings": analytics.get("early_warnings", []),
                "quarterly_trends": analytics.get("quarterly_trends", {}),
                "workshop_outcomes": analytics.get("workshop_outcomes", {}),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/insights")
def insights():
    """LangChain insight cards (legacy tab UI)."""
    try:
        return {"success": True, "data": generate_insight_cards_langchain()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/llm/regenerate-story")
def llm_regenerate_story(body: RegenerateStoryBody):
    """Re-run StorytellingChain when detail level or data grouping changes."""
    try:
        return regenerate_story_for_detail(
            body.detailLevel,
            body.aggregates,
            chart_config=body.chartConfig,
            user_prompt=body.userPrompt,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/llm/orchestrate")
def llm_orchestrate(body: OrchestrateBody):
    """
    Process a natural-language command and return bot text plus dashboard UI mutations.
    """
    try:
        return orchestrate_llm_command(body.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/chat/message")
def chat_message_dashboard(body: ChatMessageBody):
    """
    Dashboard assistant message — returns botReply and dashboardCommands for the UI.
    """
    try:
        result = handle_chat_message(body.model_dump())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/dashboard/execute")
def dashboard_execute(body: DashboardExecuteBody):
    """Validate and acknowledge a dashboard command (client applies UI changes)."""
    action = body.action.strip().lower()
    if action not in _ALLOWED_DASHBOARD_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action '{body.action}'. Allowed: {sorted(_ALLOWED_DASHBOARD_ACTIONS)}",
        )
    return {
        "success": True,
        "action": action,
        "targetWidgetId": body.targetWidgetId,
        "value": body.value,
    }


@router.post("/api/insights")
def dashboard_insights(body: DashboardInsightBody):
    """
    Dashboard chat insight — returns flat JSON matching the hackathon frontend contract:
    answer, summaryBullets, evidenceReferences, linkedDataPoints, followUpQuestions.
    """
    try:
        return generate_dashboard_insight(body.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/success-vision")
def success_vision():
    """Product Success Vision criteria — capability checklist vs live dataset."""
    try:
        return {"success": True, "data": get_success_vision_status()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/charts")
def charts_catalog():
    """All predefined charts with data (Power BI–style catalog)."""
    try:
        return {"success": True, "data": list_all_charts()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/predictions")
def predictions():
    """Traditional ML predictions: wellbeing, at-risk, sentiment, and forecast charts."""
    try:
        repo = MockDataRepository()
        result = repo.get_predictions()
        charts = build_prediction_charts(result)
        return {
            "success": True,
            "data": {
                **result,
                "charts": charts,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/charts/generate")
def charts_generate(body: ChartGenerateBody):
    """Generate charts for a natural-language request (used by Ask + Visualizations tab)."""
    try:
        result = generate_charts_for_request(
            body.question.strip(),
            body.chart_type.strip() if body.chart_type else None,
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/langchain/status")
def lc_status():
    try:
        return {"success": True, "data": langchain_status()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/langchain/architecture")
def lc_architecture():
    try:
        return {"success": True, "data": langchain_architecture_status()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/ask")
def ask(body: AskBody):
    try:
        result = ask_data_question(
            body.question.strip(),
            session_id=body.session_id,
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/chat")
def chat(body: ChatBody):
    """Storytelling chatbot — Q&A, charts, or both."""
    try:
        mode = body.mode.lower().strip()
        if mode not in {"qa", "charts", "both"}:
            raise HTTPException(status_code=400, detail="mode must be qa, charts, or both")
        result = chat_message(
            body.message.strip(),
            mode=mode,
            session_id=body.session_id,
        )
        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/chat/stream")
def chat_stream(body: ChatBody):
    """SSE streaming for the storytelling chatbot."""
    mode = body.mode.lower().strip()
    if mode not in {"qa", "charts", "both"}:
        raise HTTPException(status_code=400, detail="mode must be qa, charts, or both")
    message = body.message.strip()
    session_id = body.session_id

    def event_generator():
        parts: list[str] = []
        try:
            for token in chat_stream_tokens(message, mode=mode, session_id=session_id):
                parts.append(token)
                yield f"data: {json.dumps({'token': token})}\n\n"
            full = "".join(parts)
            final = chat_stream_finalize(message, full, mode=mode, session_id=session_id)
            yield f"data: {json.dumps({'done': True, 'data': final})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/api/chat/export-pdf")
def chat_export_pdf(body: ChatExportPdfBody):
    """Download conversation as PDF (server-generated; fast, no frontend jspdf)."""
    try:
        pdf_bytes = build_chat_pdf(
            [m.model_dump() for m in body.messages],
            mode=body.mode.lower().strip(),
            session_id=body.session_id,
        )
        filename = f"impact-guide-chat-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/ask/stream")
def ask_stream(body: AskBody):
    """SSE token streaming for Ask-the-Data (StreamingCallbacks)."""
    question = body.question.strip()
    session_id = body.session_id

    def event_generator():
        parts: list[str] = []
        try:
            for token in ask_stream_tokens(question, session_id=session_id):
                parts.append(token)
                yield f"data: {json.dumps({'token': token})}\n\n"
            full = "".join(parts)
            final = ask_stream_finalize(question, full, session_id)
            yield f"data: {json.dumps({'done': True, 'data': final})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/api/ask-why")
def ask_why(body: AskWhyBody):
    try:
        return {"success": True, "data": ask_why_langchain(body.subject, body.evidence)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/report")
def report(body: ReportBody):
    try:
        result = generate_report(body.audience.strip())
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/story")
def story(body: StoryBody):
    try:
        result = generate_impact_story(body.theme)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
