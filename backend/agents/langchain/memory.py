"""ConversationBufferWindowMemory — last k turns per session."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class Turn:
    role: str
    content: str


@dataclass
class SessionMemory:
    turns: deque[Turn] = field(default_factory=deque)
    k: int = 6

    def add(self, role: str, content: str) -> None:
        self.turns.append(Turn(role=role, content=content))
        while len(self.turns) > self.k * 2:
            self.turns.popleft()

    def as_text(self) -> str:
        if not self.turns:
            return ""
        lines = []
        for t in self.turns:
            label = "User" if t.role == "human" else "Assistant"
            lines.append(f"{label}: {t.content[:500]}")
        return "\n".join(lines)


class ConversationWindowMemory:
    def __init__(self, *, window_k: int = 6):
        self.window_k = window_k
        self._sessions: dict[str, SessionMemory] = {}
        self._lock = Lock()

    def get(self, session_id: str) -> SessionMemory:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionMemory(k=self.window_k)
            return self._sessions[session_id]

    def append_exchange(self, session_id: str, question: str, answer: str) -> None:
        mem = self.get(session_id)
        mem.add("human", question)
        mem.add("ai", answer)

    def context_block(self, session_id: str | None) -> str:
        if not session_id:
            return ""
        text = self.get(session_id).as_text()
        if not text:
            return ""
        return f"Recent conversation (last {self.window_k} exchanges):\n{text}\n\n"


_memory = ConversationWindowMemory(window_k=int(__import__("os").environ.get("LC_MEMORY_WINDOW", "6")))


def get_memory() -> ConversationWindowMemory:
    return _memory
