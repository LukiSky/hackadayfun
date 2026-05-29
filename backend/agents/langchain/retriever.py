"""VectorStore-style feedback retriever (keyword + optional FAISS)."""

from __future__ import annotations

import os
import re
from functools import lru_cache

from data.repository import MockDataRepository

_repo = MockDataRepository()

_stop = frozenset(
    "the a an and or but in on at to for of is are was were be been being have has had do does did".split()
)


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in _stop and len(w) > 2}


@lru_cache(maxsize=1)
def _feedback_docs() -> list[dict]:
    samples = _repo.get_analytics().get("feedback_samples", [])
    docs = []
    for i, s in enumerate(samples):
        quote = (s.get("quote") or "").strip()
        if not quote:
            continue
        docs.append(
            {
                "id": f"fb_{i}",
                "text": quote,
                "school_name": s.get("school_name"),
                "theme": s.get("theme"),
                "sentiment": s.get("sentiment"),
                "question_text": s.get("question_text"),
            }
        )
    return docs


def search_feedback(query: str, k: int = 8) -> list[dict]:
    """Fast keyword retriever (instant; no embedding API)."""
    qt = _tokens(query)
    if not qt:
        return _feedback_docs()[:k]

    scored: list[tuple[float, dict]] = []
    for doc in _feedback_docs():
        dt = _tokens(doc["text"])
        if not dt:
            continue
        overlap = len(qt & dt) / max(len(qt), 1)
        if overlap > 0:
            scored.append((overlap, doc))

    scored.sort(key=lambda x: -x[0])
    return [d for _, d in scored[:k]]


def retriever_context(query: str, k: int = 8) -> str:
    docs = search_feedback(query, k=k)
    if not docs:
        return "No matching feedback excerpts found."
    lines = []
    for d in docs:
        lines.append(
            f"- [{d.get('sentiment')}] {d.get('school_name')} / {d.get('theme')}: \"{d['text'][:200]}\""
        )
    return "\n".join(lines)


def build_faiss_retriever():
    """Optional FAISS retriever when langchain-community + faiss are installed."""
    if os.environ.get("LC_USE_FAISS", "0") != "1":
        return None
    try:
        from langchain_community.vectorstores import FAISS
        from langchain_core.embeddings import Embeddings
        import hashlib
        import numpy as np

        class HashEmbeddings(Embeddings):
            def _embed(self, text: str) -> list[float]:
                h = hashlib.sha256(text.encode()).digest()
                return [((b / 255.0) * 2 - 1) for b in h[:64]]

            def embed_documents(self, texts: list[str]) -> list[list[float]]:
                return [self._embed(t) for t in texts]

            def embed_query(self, text: str) -> list[float]:
                return self._embed(text)

        docs = _feedback_docs()
        texts = [d["text"] for d in docs]
        if not texts:
            return None
        store = FAISS.from_texts(texts, HashEmbeddings(), metadatas=docs)
        return store.as_retriever(search_kwargs={"k": 8})
    except Exception:
        return None
