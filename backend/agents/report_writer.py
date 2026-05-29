from agents.langchain_service import generate_report_langchain


def generate_report(audience: str) -> dict:
    return generate_report_langchain(audience)
