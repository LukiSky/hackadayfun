"""LangChainCache — in-memory exact + lightweight semantic ask cache."""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from threading import Lock


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def _token_set(text: str) -> set[str]:
    return {t for t in _normalize(text).split() if len(t) > 2}


def _similarity(a: str, b: str) -> float:
    sa, sb = _token_set(a), _token_set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


@dataclass
class CacheEntry:
    answer: str
    metadata: dict
    created_at: float = field(default_factory=time.time)


class LangChainAskCache:
    """In-memory cache with semantic similarity lookup (no Redis required)."""

    def __init__(self, *, max_entries: int = 256, semantic_threshold: float = 0.82, ttl_seconds: int = 3600):
        self.max_entries = max_entries
        self.semantic_threshold = semantic_threshold
        self.ttl_seconds = ttl_seconds
        self._exact: dict[str, CacheEntry] = {}
        self._questions: list[tuple[str, str]] = []  # (normalized_question, exact_key)
        self._lock = Lock()

    def _key(self, question: str, route: str, session_id: str | None) -> str:
        raw = f"{route}|{session_id or ''}|{_normalize(question)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [k for k, v in self._exact.items() if now - v.created_at > self.ttl_seconds]
        for k in expired:
            self._exact.pop(k, None)
        self._questions = [(q, k) for q, k in self._questions if k in self._exact]

    def get(self, question: str, route: str, session_id: str | None = None) -> dict | None:
        with self._lock:
            self._evict_expired()
            exact_key = self._key(question, route, session_id)
            hit = self._exact.get(exact_key)
            if hit:
                return {"answer": hit.answer, **hit.metadata, "cache_hit": "exact"}

            nq = _normalize(question)
            for stored_q, key in self._questions:
                if _similarity(nq, stored_q) >= self.semantic_threshold:
                    entry = self._exact.get(key)
                    if entry:
                        return {"answer": entry.answer, **entry.metadata, "cache_hit": "semantic"}
        return None

    def set(self, question: str, route: str, answer: str, metadata: dict, session_id: str | None = None) -> None:
        with self._lock:
            self._evict_expired()
            if len(self._exact) >= self.max_entries:
                oldest_key = min(self._exact, key=lambda k: self._exact[k].created_at)
                self._exact.pop(oldest_key, None)
                self._questions = [(q, k) for q, k in self._questions if k != oldest_key]

            exact_key = self._key(question, route, session_id)
            meta = {k: v for k, v in metadata.items() if k != "answer"}
            self._exact[exact_key] = CacheEntry(answer=answer, metadata=meta)
            nq = _normalize(question)
            if not any(q == nq for q, _ in self._questions):
                self._questions.append((nq, exact_key))

    def stats(self) -> dict:
        with self._lock:
            return {"entries": len(self._exact), "max_entries": self.max_entries}


_ask_cache = LangChainAskCache()


def get_ask_cache() -> LangChainAskCache:
    return _ask_cache
