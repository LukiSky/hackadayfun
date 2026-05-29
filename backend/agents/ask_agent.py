import os

from agents.llm_client import complete_with_context
from agents.local_insights import ask_locally
from data.repository import MockDataRepository

_repo = MockDataRepository()


def ask_data_question(user_question: str) -> dict:
    if not os.environ.get("HF_TOKEN"):
        return ask_locally(user_question)

    context = _repo.dataset_context()
    system = (
        "You are the Ask-the-Data Agent for ImpactLens AI. "
        "Answer questions concisely using ONLY the provided dataset context. "
        "If the data cannot answer the question, say so explicitly. "
        "Always reference key supporting evidence with numbers from the dataset."
    )
    user = f"Dataset:\n{context}\n\nQuestion: {user_question}"
    try:
        answer = complete_with_context(system, user)
        return {
            "question": user_question,
            "answer": answer,
            "citations": ["Response grounded in loaded mock dataset only."],
            "source": "langchain",
        }
    except Exception:
        return ask_locally(user_question)
