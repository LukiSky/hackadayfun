"""LangChain facade — delegates to optimized engine."""

from __future__ import annotations

from agents.langchain.engine import (
    ask_optimized,
    ask_stream_finalize,
    ask_stream_tokens,
    ask_why_langchain,
    chat_message,
    chat_stream_finalize,
    chat_stream_tokens,
    generate_insight_cards_langchain,
    generate_report_langchain,
    generate_story_langchain,
    invoke_chain,
    langchain_architecture_status,
    langchain_status,
)

_invoke_chain = invoke_chain
from agents.langchain.helpers import story_citations as _story_citations


def ask_data_question_langchain(question: str, *, session_id: str | None = None) -> dict:
    return ask_optimized(question, session_id=session_id)


__all__ = [
    "ask_data_question_langchain",
    "ask_optimized",
    "ask_stream_tokens",
    "ask_stream_finalize",
    "chat_message",
    "chat_stream_tokens",
    "chat_stream_finalize",
    "generate_report_langchain",
    "generate_story_langchain",
    "generate_insight_cards_langchain",
    "ask_why_langchain",
    "langchain_status",
    "langchain_architecture_status",
    "invoke_chain",
    "_story_citations",
]
