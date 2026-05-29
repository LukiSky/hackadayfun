"""Pre-compiled ChatPromptTemplates with few-shot examples."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate

from agents.personas import (
    persona_for_ask,
    persona_for_ask_why,
    persona_for_chat,
    persona_for_insights,
    persona_for_report,
    persona_for_story,
)

# --- Chat (storytelling, human) ---
CHAT_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", persona_for_chat()),
        (
            "human",
            "{memory_block}"
            "Chat mode: {chat_mode}\n"
            "User message: {question}\n\n"
            "Retrieved student voice & context:\n{context}\n\n"
            "Dataset summary:\n{dataset_context}\n\n"
            "{chart_hint}"
            "Reply in warm, conversational prose (2–4 short paragraphs). "
            "Embed specific numbers naturally. End with a gentle invitation to explore further.",
        ),
    ]
)

CHAT_TOOL_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", persona_for_chat()),
        (
            "human",
            "User message: {question}\n\n"
            "Factual tool output:\n{tool_output}\n\n"
            "Tell the story behind these facts in a human, warm voice. No bullet-only lists.",
        ),
    ]
)

CHAT_CHART_NARRATIVE_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", persona_for_chat()),
        (
            "human",
            "User asked for visual insight: {question}\n\n"
            "Charts being shown:\n{chart_summaries}\n\n"
            "Write a short, warm introduction (2–3 paragraphs) explaining what these visuals reveal "
            "about LifeChanger workshops — invite the user to explore the charts below.",
        ),
    ]
)

# --- Ask (general / RAG) ---
ASK_FEW_SHOT = [
    {
        "question": "How is sentiment across HEALTH workshops?",
        "context": "sentiment_distribution: 62% positive on HEALTH topic",
        "answer": (
            "Answer: HEALTH workshops show predominantly positive student voice (about 62% positive classifications).\n"
            "Evidence:\n- Sentiment distribution weighted toward positive on HEALTH pillar\n"
            "- Top themes include HEALTH in the top 3 response volumes\n"
            "Confidence: medium — based on classified feedback text, not clinical outcomes."
        ),
    },
]

ask_example_prompt = ChatPromptTemplate.from_messages(
    [
        ("human", "Question: {question}\nContext snippets:\n{context}"),
        ("ai", "{answer}"),
    ]
)

ask_few_shot_prompt = FewShotChatMessagePromptTemplate(
    example_prompt=ask_example_prompt,
    examples=ASK_FEW_SHOT,
)

ASK_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", persona_for_ask() + "\n\nUse the retrieved context and tool outputs. Never invent metrics."),
        ask_few_shot_prompt,
        (
            "human",
            "{memory_block}"
            "Question: {question}\n\n"
            "Tool / retrieval context:\n{context}\n\n"
            "Dataset summary:\n{dataset_context}\n\n"
            "Respond with Answer, Evidence bullets, Confidence, and optional Suggested follow-up.",
        ),
    ]
)

# --- Fast synthesis after tools ---
TOOL_SYNTH_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", persona_for_ask()),
        (
            "human",
            "Question: {question}\n\n"
            "Deterministic tool output (facts only):\n{tool_output}\n\n"
            "Write a concise Answer + Evidence + Confidence. Do not add numbers not in the tool output.",
        ),
    ]
)

# --- Report / Story / Insights / Ask-why (pre-compiled) ---
REPORT_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", persona_for_report()),
        (
            "human",
            "Audience: {audience}\nFocus: {audience_focus}\n\n"
            "Dataset context:\n{dataset_context}\n\n"
            "Format: Title, Summary, Key evidence (3-6 bullets), Recommended next steps (3), Data honesty note if needed.",
        ),
    ]
)

STORY_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", persona_for_story()),
        (
            "human",
            "Theme: {theme}\n\nFeedback sample:\n{feedback_sample}\n\n"
            "Dataset context:\n{dataset_context}\n\n"
            "Output: Impact story (2-4 paragraphs) then Source evidence bullets.",
        ),
    ]
)

INSIGHTS_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", persona_for_insights()),
        (
            "human",
            "Analytics:\n{analytics_summary}\n\nThemes:\n{top_themes}\n\n"
            "Sentiment:\n{sentiment}\n\nRisks:\n{risks}\n\n"
            'Return STRICT JSON: {{"cards":[...]}}',
        ),
    ]
)

ASK_WHY_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", persona_for_ask_why()),
        (
            "human",
            "Subject: {subject}\nEvidence:\n{evidence}\n\n"
            "Return Explanation, Reasoning steps, What to do next.",
        ),
    ]
)
