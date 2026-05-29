from agents.langchain_service import generate_story_langchain


def generate_impact_story(theme: str | None = None) -> dict:
    return generate_story_langchain(theme)
