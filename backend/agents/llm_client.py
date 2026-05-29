import os
from openai import OpenAI

BASE_URL = os.environ.get("HF_BASE_URL", "https://router.huggingface.co/v1")
# Must match a model id from GET https://router.huggingface.co/v1/models (no :provider suffix)
DEFAULT_MODEL = "google/gemma-4-31B-it"


def get_model() -> str:
    raw = (os.environ.get("HF_MODEL") or DEFAULT_MODEL).strip()
    # Router uses bare model ids (e.g. google/gemma-4-31B-it), not model:provider
    return raw.split(":", 1)[0] if ":" in raw else raw


def get_ai_client() -> OpenAI:
    api_key = os.environ.get("HF_TOKEN")
    if not api_key:
        raise ValueError(
            "HF_TOKEN is not set. Add it to your environment or backend/.env file."
        )
    return OpenAI(base_url=BASE_URL, api_key=api_key)


def complete_with_context(
    system_prompt: str,
    user_content: str,
    *,
    temperature: float = 0.3,
) -> str:
    client = get_ai_client()
    completion = client.chat.completions.create(
        model=get_model(),
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    return completion.choices[0].message.content or ""
