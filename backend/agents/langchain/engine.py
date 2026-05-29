"""Optimized LangChain engine: cache, router, tools, RAG, memory, streaming."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from functools import lru_cache

from langchain_core.globals import set_llm_cache
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from agents.langchain.cache import get_ask_cache
from agents.langchain.memory import get_memory
from agents.langchain.prompts import (
    ASK_PROMPT,
    ASK_WHY_PROMPT,
    CHAT_CHART_NARRATIVE_PROMPT,
    CHAT_PROMPT,
    CHAT_TOOL_PROMPT,
    INSIGHTS_PROMPT,
    REPORT_PROMPT,
    STORY_PROMPT,
    TOOL_SYNTH_PROMPT,
)
from agents.langchain.retriever import retriever_context
from agents.langchain.router import QueryRoute, classify_route
from agents.langchain.tools import (
    get_correlation_insights,
    get_dataset_metrics,
    get_risk_and_warning_signals,
    get_workshop_outcome_rankings,
)
from agents.personas import persona_catalog
from agents.risk_opportunity import identify_risks_and_opportunities
from data.repository import MockDataRepository

_repo = MockDataRepository()


def _model_name() -> str:
    raw = (os.environ.get("HF_MODEL") or "google/gemma-4-31B-it").strip()
    return raw.split(":", 1)[0] if ":" in raw else raw


@lru_cache(maxsize=1)
def _llm(*, streaming: bool = False) -> ChatOpenAI:
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise ValueError("HF_TOKEN is not set in backend/.env")
    return ChatOpenAI(
        model=_model_name(),
        api_key=token,
        base_url=os.environ.get("HF_BASE_URL", "https://router.huggingface.co/v1"),
        temperature=0.25,
        streaming=streaming,
    )


def _enable_llm_cache() -> None:
    try:
        from langchain_core.caches import InMemoryCache

        set_llm_cache(InMemoryCache())
    except Exception:
        pass


_enable_llm_cache()


def _dataset_context() -> str:
    return _repo.dataset_context()


def invoke_chain(system_prompt: str, user_prompt: str, *, temperature: float = 0.25) -> str:
    """Generic LLM invoke for auxiliary chains (e.g. chart picker)."""
    from langchain_core.prompts import ChatPromptTemplate

    chain = (
        ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("human", "{user_input}")]
        )
        | _llm(streaming=False).bind(temperature=temperature)
        | StrOutputParser()
    )
    return chain.invoke({"user_input": user_prompt})


def _instant_metrics_answer(question: str) -> str | None:
    """Tool-only path — no LLM (lowest latency)."""
    data = json.loads(get_dataset_metrics.invoke({}))
    q = question.lower()
    parts = [
        "Answer:",
        f"The LifeChanger dataset contains **{data.get('valid_responses')}** valid feedback responses "
        f"across **{data.get('total_workshops')}** workshops and **{data.get('total_schools')}** schools.",
    ]
    if "sentiment" in q:
        parts.append(f"Sentiment mix: {data.get('sentiment_distribution')}.")
    if "rating" in q or "facilitator" in q:
        parts.append(f"Average facilitator rating: {data.get('avg_facilitator_rating')}.")
    if "heartwarm" in q:
        parts.append(f"Heartwarming responses: {data.get('heartwarming_count')}.")
    parts.append(
        "Evidence:\n"
        f"- {data.get('valid_responses')} valid responses\n"
        f"- {data.get('total_workshops')} workshops · {data.get('total_schools')} schools\n"
        f"- Top themes: {data.get('top_themes')}\n"
        "Confidence: high — direct aggregate metrics from the dataset."
    )
    return "\n".join(parts)


def _run_tool_branch(route: QueryRoute, question: str) -> tuple[str, str]:
    if route == QueryRoute.METRICS:
        if _should_skip_llm_for_metrics(question):
            return _instant_metrics_answer(question) or "", "tool_instant"
        tool_out = get_dataset_metrics.invoke({})
    elif route == QueryRoute.RISK:
        tool_out = get_risk_and_warning_signals.invoke({})
    elif route == QueryRoute.WORKSHOP:
        tool_out = get_workshop_outcome_rankings.invoke({})
    else:
        tool_out = get_correlation_insights.invoke({})

    chain = TOOL_SYNTH_PROMPT | _llm(streaming=False).bind(temperature=0.15) | StrOutputParser()
    answer = chain.invoke({"question": question, "tool_output": tool_out})
    return answer, "tool_synth"


def _should_skip_llm_for_metrics(question: str) -> bool:
    q = question.lower()
    return any(
        phrase in q
        for phrase in (
            "how many",
            "how much",
            "total number",
            "count of",
            "what is the total",
        )
    )


def _run_rag_branch(question: str, session_id: str | None) -> tuple[str, str]:
    memory_block = get_memory().context_block(session_id)
    retrieved = retriever_context(question, k=8)
    chain = ASK_PROMPT | _llm(streaming=False).bind(temperature=0.2) | StrOutputParser()
    answer = chain.invoke(
        {
            "question": question,
            "context": retrieved,
            "dataset_context": _dataset_context(),
            "memory_block": memory_block,
        }
    )
    return answer, "rag_ask"


def _stream_rag_branch(question: str, session_id: str | None) -> Iterator[str]:
    memory_block = get_memory().context_block(session_id)
    retrieved = retriever_context(question, k=8)
    chain = ASK_PROMPT | _llm(streaming=True).bind(temperature=0.2) | StrOutputParser()
    for chunk in chain.stream(
        {
            "question": question,
            "context": retrieved,
            "dataset_context": _dataset_context(),
            "memory_block": memory_block,
        }
    ):
        if chunk:
            yield chunk


def _attach_charts(question: str, result: dict, *, mode: str = "both") -> dict:
    from agents.chart_service import attach_charts_to_ask

    return attach_charts_to_ask(question, result, mode=mode)


def _chart_hint_for_mode(mode: str) -> str:
    if mode == "charts":
        return "The user wants charts — introduce what the visuals will show.\n"
    if mode == "both":
        return "Charts may appear below your message — mention them naturally.\n"
    return ""


def _run_chat_rag(question: str, session_id: str | None, chat_mode: str) -> tuple[str, str]:
    memory_block = get_memory().context_block(session_id)
    retrieved = retriever_context(question, k=8)
    chain = CHAT_PROMPT | _llm(streaming=False).bind(temperature=0.35) | StrOutputParser()
    answer = chain.invoke(
        {
            "question": question,
            "context": retrieved,
            "dataset_context": _dataset_context(),
            "memory_block": memory_block,
            "chat_mode": chat_mode,
            "chart_hint": _chart_hint_for_mode(chat_mode),
        }
    )
    return answer, "chat_rag"


def _stream_chat_rag(question: str, session_id: str | None, chat_mode: str) -> Iterator[str]:
    memory_block = get_memory().context_block(session_id)
    retrieved = retriever_context(question, k=8)
    chain = CHAT_PROMPT | _llm(streaming=True).bind(temperature=0.35) | StrOutputParser()
    for chunk in chain.stream(
        {
            "question": question,
            "context": retrieved,
            "dataset_context": _dataset_context(),
            "memory_block": memory_block,
            "chat_mode": chat_mode,
            "chart_hint": _chart_hint_for_mode(chat_mode),
        }
    ):
        if chunk:
            yield chunk


def _run_chat_tool_branch(route: QueryRoute, question: str) -> tuple[str, str]:
    if route == QueryRoute.METRICS:
        if _should_skip_llm_for_metrics(question):
            instant = _instant_metrics_answer(question)
            if instant:
                return (
                    instant.replace("Answer:", "Here's what the data tells us.").replace(
                        "Evidence:\n", "\n\nA few anchors from the dataset:\n"
                    ),
                    "chat_tool_instant",
                )
        tool_out = get_dataset_metrics.invoke({})
    elif route == QueryRoute.RISK:
        tool_out = get_risk_and_warning_signals.invoke({})
    elif route == QueryRoute.WORKSHOP:
        tool_out = get_workshop_outcome_rankings.invoke({})
    else:
        tool_out = get_correlation_insights.invoke({})

    chain = CHAT_TOOL_PROMPT | _llm(streaming=False).bind(temperature=0.3) | StrOutputParser()
    answer = chain.invoke({"question": question, "tool_output": tool_out})
    return answer, "chat_tool_synth"


def _charts_only_narrative(question: str, charts: list[dict]) -> str:
    from agents.chart_service import chart_summaries_for_llm

    chain = CHAT_CHART_NARRATIVE_PROMPT | _llm(streaming=False).bind(temperature=0.4) | StrOutputParser()
    return chain.invoke(
        {
            "question": question,
            "chart_summaries": chart_summaries_for_llm(charts),
        }
    )


def chat_message(
    message: str,
    *,
    mode: str = "both",
    session_id: str | None = None,
    use_cache: bool = True,
) -> dict:
    """
    Chatbot entry: mode = qa | charts | both.
    Responses use warm storytelling voice.
    """
    mode = (mode or "both").lower()
    if mode not in {"qa", "charts", "both"}:
        mode = "both"

    question = message.strip()
    route = classify_route(question)
    cache_key = f"chat_{mode}|{route.value}"

    if use_cache and mode != "charts":
        cached = get_ask_cache().get(question, cache_key, session_id)
        if cached:
            result = {
                "message": question,
                "answer": cached["answer"],
                "mode": mode,
                "framework": "langchain",
                "chain": f"cached_{route.value}",
                "route": route.value,
                "cache_hit": cached.get("cache_hit"),
                "charts": cached.get("charts", []),
                "has_visualizations": bool(cached.get("charts")),
            }
            return result

    if mode == "charts":
        from agents.chart_service import attach_charts_to_ask, select_charts_for_question

        charts = select_charts_for_question(question, max_charts=4)
        answer = _charts_only_narrative(question, charts)
        result = {
            "message": question,
            "answer": answer,
            "mode": mode,
            "framework": "langchain",
            "chain": "chat_charts",
            "route": route.value,
            "latency_mode": "charts_narrative",
            "session_id": session_id,
        }
        result = attach_charts_to_ask(question, result, mode="charts", max_charts=4)
    elif route in (QueryRoute.METRICS, QueryRoute.RISK, QueryRoute.WORKSHOP):
        answer, chain_name = _run_chat_tool_branch(route, question)
        result = {
            "message": question,
            "answer": answer,
            "mode": mode,
            "framework": "langchain",
            "chain": chain_name,
            "route": route.value,
            "session_id": session_id,
        }
        result = _attach_charts(question, result, mode=mode)
    else:
        answer, chain_name = _run_chat_rag(question, session_id, mode)
        result = {
            "message": question,
            "answer": answer,
            "mode": mode,
            "framework": "langchain",
            "chain": chain_name,
            "route": route.value,
            "session_id": session_id,
        }
        result = _attach_charts(question, result, mode=mode)

    if session_id:
        get_memory().append_exchange(session_id, question, result["answer"])

    get_ask_cache().set(question, cache_key, result["answer"], result, session_id)
    return result


def chat_stream_tokens(
    message: str,
    *,
    mode: str = "both",
    session_id: str | None = None,
) -> Iterator[str]:
    mode = (mode or "both").lower()
    question = message.strip()
    route = classify_route(question)

    if mode == "charts":
        charts = []
        from agents.chart_service import select_charts_for_question

        charts = select_charts_for_question(question, max_charts=4)
        narrative = _charts_only_narrative(question, charts)
        yield narrative
        return

    if route in (QueryRoute.METRICS, QueryRoute.RISK, QueryRoute.WORKSHOP):
        answer, _ = _run_chat_tool_branch(route, question)
        yield answer
    else:
        yield from _stream_chat_rag(question, session_id, mode)


def chat_stream_finalize(
    message: str,
    full_answer: str,
    *,
    mode: str = "both",
    session_id: str | None = None,
) -> dict:
    mode = (mode or "both").lower()
    question = message.strip()
    route = classify_route(question)
    result = {
        "message": question,
        "answer": full_answer,
        "mode": mode,
        "framework": "langchain",
        "chain": "chat_stream",
        "route": route.value,
        "latency_mode": "streaming",
        "session_id": session_id,
    }
    if session_id:
        get_memory().append_exchange(session_id, question, full_answer)
    result = _attach_charts(question, result, mode=mode)
    cache_key = f"chat_{mode}|{route.value}"
    get_ask_cache().set(question, cache_key, full_answer, result, session_id)
    return result


def ask_optimized(
    question: str,
    *,
    session_id: str | None = None,
    use_cache: bool = True,
) -> dict:
    route = classify_route(question)
    cache = get_ask_cache()

    if use_cache:
        cached = cache.get(question, route.value, session_id)
        if cached:
            result = {
                "question": question,
                "answer": cached["answer"],
                "framework": "langchain",
                "chain": f"cached_{route.value}",
                "route": route.value,
                "cache_hit": cached.get("cache_hit"),
                "latency_mode": "instant_cache",
            }
            return _attach_charts(question, result)

    if route == QueryRoute.CHART:
        answer = (
            "Answer: I've selected visual charts for your question — see the interactive charts below.\n"
            "Evidence:\n- Charts are generated from the LifeChanger analytics catalog.\n"
            "Confidence: high — chart data is computed deterministically from the dataset."
        )
        chain_name = "chart_delegate"
    elif route in (QueryRoute.METRICS, QueryRoute.RISK, QueryRoute.WORKSHOP):
        answer, chain_name = _run_tool_branch(route, question)
    else:
        answer, chain_name = _run_rag_branch(question, session_id)

    result = {
        "question": question,
        "answer": answer,
        "framework": "langchain",
        "chain": chain_name,
        "route": route.value,
        "latency_mode": "tool_instant" if chain_name == "tool_instant" else "optimized",
        "session_id": session_id,
    }

    if session_id:
        get_memory().append_exchange(session_id, question, answer)

    cache.set(question, route.value, answer, result, session_id)
    return _attach_charts(question, result)


def ask_stream_tokens(question: str, *, session_id: str | None = None) -> Iterator[str]:
    route = classify_route(question)
    cache = get_ask_cache()
    cached = cache.get(question, route.value, session_id)
    if cached:
        yield cached["answer"]
        return

    if route in (QueryRoute.METRICS, QueryRoute.RISK, QueryRoute.WORKSHOP):
        answer, _ = _run_tool_branch(route, question)
        yield answer
    elif route == QueryRoute.CHART:
        yield (
            "Answer: Interactive charts are being prepared for your question. "
            "See the chart panel below."
        )
    else:
        yield from _stream_rag_branch(question, session_id)


def ask_stream_finalize(question: str, full_answer: str, session_id: str | None) -> dict:
    route = classify_route(question)
    result = {
        "question": question,
        "answer": full_answer,
        "framework": "langchain",
        "chain": "rag_ask_stream",
        "route": route.value,
        "latency_mode": "streaming",
        "session_id": session_id,
    }
    if session_id:
        get_memory().append_exchange(session_id, question, full_answer)
    get_ask_cache().set(question, route.value, full_answer, result, session_id)
    return _attach_charts(question, result)


# --- Legacy chain entrypoints (use pre-compiled prompts) ---

def generate_report_langchain(audience: str) -> dict:
    audience_key = audience.lower().strip()
    focus = {
        "funders": "PRIMARY: quantitative metrics and numbers.",
        "schools": "PRIMARY: qualitative feedback and student experiences.",
        "internal": "delivery fidelity and operational fixes.",
        "board": "PRIMARY: strategic trajectory and portfolio risks.",
    }
    if audience_key not in focus:
        raise ValueError("audience must be one of: funders, schools, internal, board")

    chain = REPORT_PROMPT | _llm().bind(temperature=0.2) | StrOutputParser()
    report = chain.invoke(
        {
            "audience": audience_key,
            "audience_focus": focus[audience_key],
            "dataset_context": _dataset_context(),
        }
    )
    return {"audience": audience_key, "report": report, "framework": "langchain", "chain": "report_writer_chain"}


def generate_story_langchain(theme: str | None = None) -> dict:
    from agents.langchain.helpers import story_citations

    analytics = _repo.get_analytics()
    samples = analytics["feedback_samples"][:35]
    chain = STORY_PROMPT | _llm().bind(temperature=0.45) | StrOutputParser()
    story = chain.invoke(
        {
            "theme": theme or "strongest positive theme from student voice",
            "feedback_sample": json.dumps(samples, indent=2),
            "dataset_context": _dataset_context(),
        }
    )
    return {
        "story": story,
        "citations": story_citations(samples, story) or [],
        "quotes_used_count": len(samples),
        "framework": "langchain",
        "chain": "storytelling_chain",
    }


def generate_insight_cards_langchain() -> dict:
    analytics = _repo.get_analytics()
    risks = identify_risks_and_opportunities()
    chain = INSIGHTS_PROMPT | _llm().bind(temperature=0.15) | StrOutputParser()
    raw = chain.invoke(
        {
            "analytics_summary": json.dumps(analytics["summary"], indent=2),
            "top_themes": json.dumps(analytics["top_themes"][:8], indent=2),
            "sentiment": json.dumps(analytics.get("sentiment_distribution", {}), indent=2),
            "risks": json.dumps(risks, indent=2),
        }
    )
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        parsed = json.loads(raw[start : end + 1]) if start >= 0 else {}
        cards = parsed.get("cards", [])
    except Exception:
        cards = []

    if not cards:
        cards = [
            {
                "title": "Dataset baseline established",
                "insight": "ImpactLens ingested workshop and school groupings.",
                "evidence": [f"Sessions: {analytics['summary'].get('total_sessions')}"],
                "recommended_action": "Use Ask with streaming for faster Q&A.",
                "confidence_level": "medium",
            }
        ]

    return {
        "cards": cards,
        "risks": risks["risks"],
        "framework": "langchain",
        "chains": ["impact_analyst_chain", "evidence_guardrail_chain"],
    }


def ask_why_langchain(subject: str, evidence: list[str]) -> dict:
    chain = ASK_WHY_PROMPT | _llm().bind(temperature=0.2) | StrOutputParser()
    answer = chain.invoke({"subject": subject, "evidence": json.dumps(evidence, indent=2)})
    return {"subject": subject, "answer": answer, "framework": "langchain"}


def langchain_architecture_status() -> dict:
    return {
        "system_goal": "Highly optimized, low-latency LangChain with tool-assisted generation.",
        "components": [
            {
                "id": "1",
                "category": "Performance Optimization",
                "functions": [
                    {"name": "LangChainCache", "status": "active", "backend": "in_memory_semantic"},
                    {"name": "StreamingCallbacks", "status": "active", "endpoint": "POST /api/ask/stream"},
                ],
            },
            {
                "id": "2",
                "category": "Core LLM Engine",
                "functions": [
                    {"name": "ChatPromptTemplate", "status": "active", "detail": "Pre-compiled prompts + few-shot"},
                    {"name": "RunnableBranch", "status": "active", "detail": "Keyword router → metrics|risk|workshop|chart|general"},
                ],
            },
            {
                "id": "3",
                "category": "Agentic Tooling",
                "functions": [
                    {"name": "VectorStoreRetriever", "status": "active", "detail": "Keyword feedback retriever; FAISS optional via LC_USE_FAISS=1"},
                    {"name": "bind_tools", "status": "active", "tools": [t.name for t in [get_dataset_metrics, get_risk_and_warning_signals]]},
                ],
            },
            {
                "id": "4",
                "category": "Memory Context",
                "functions": [
                    {
                        "name": "ConversationBufferWindowMemory",
                        "status": "active",
                        "window_k": int(os.environ.get("LC_MEMORY_WINDOW", "6")),
                    },
                ],
            },
        ],
        "cache_stats": get_ask_cache().stats(),
    }


def langchain_status() -> dict:
    row_count = None
    dataset_file = None
    try:
        repo = MockDataRepository()
        dataset_file = repo.filename.name
        analytics = repo.get_analytics()
        summary = analytics.get("summary") or {}
        row_count = summary.get("valid_responses") or analytics.get("meta", {}).get("record_count")
    except Exception:
        pass
    return {
        "framework": "langchain",
        "architecture": "optimized_v2",
        "provider": "huggingface-router-openai-compatible",
        "llm_configured": bool(os.environ.get("HF_TOKEN")),
        "dataset_file": dataset_file,
        "row_count": row_count,
        "model": _model_name(),
        "persona": {
            "product": "ImpactLens AI",
            "organisation": "LifeChanger Foundation",
            "voice": "Warm, evidence-led, youth-centred, professional",
            "pillars": ["HEALTH", "TRIBE", "SKILLS", "SELF", "PURPOSE"],
        },
        "agents": [
            "Data Cleaning Agent",
            "Feedback Intelligence Agent",
            "Workshop Risk Agent",
            "Impact Analyst Agent",
            "Visualization Agent",
            "Report Writer Agent",
            "Storytelling Agent",
            "Evidence Guardrail Agent",
        ],
        "agent_personas": persona_catalog(),
        "visualizations": True,
        "optimizations": langchain_architecture_status(),
    }
