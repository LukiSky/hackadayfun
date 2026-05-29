from agents.langchain_service import ask_data_question_langchain


def ask_data_question(user_question: str, *, session_id: str | None = None) -> dict:
    return ask_data_question_langchain(user_question, session_id=session_id)
