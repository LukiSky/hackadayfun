"""Shared helpers for LangChain chains."""


def story_citations(samples: list[dict], story_text: str) -> list[str]:
    citations: list[str] = []
    if "Source evidence:" in story_text:
        _, _, tail = story_text.partition("Source evidence:")
        for line in tail.splitlines():
            line = line.strip().lstrip("-•").strip()
            if line:
                citations.append(line)
    if not citations:
        for sample in samples[:5]:
            quote = (sample.get("quote") or "").strip()
            if not quote:
                continue
            school = sample.get("school_name") or sample.get("program_name") or "Workshop"
            snippet = quote if len(quote) <= 140 else f"{quote[:137]}…"
            citations.append(f'{school}: "{snippet}"')
    return citations
