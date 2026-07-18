"""
Conversation memory store.

Lifetime / strategy:
- While a user is talking, turns are kept ONLY in live memory (no disk write per message).
- When the user leaves / disconnects (end_session), the conversation is:
    * persisted to disk with `expires_at = now + MEMORY_TTL_SECONDS` (default 1 hour),
    * embedded pair-by-pair into the owner's vector store (1 pair -> 1 vector).
- A sweeper deletes conversations once they pass `expires_at`, and clears their vectors.

A "pair" is exactly one (user_input, system_output) exchange.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from memory.vector_store import VectorStore

TTL_SECONDS = int(__import__("os").getenv("MEMORY_TTL_SECONDS", "3600"))


def _now() -> datetime:
    return datetime.now()


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


class ConversationStore:
    def __init__(self, session_id: str, live_dir: Path, vector_dir: Path) -> None:
        self.session_id = session_id
        self.live_dir = Path(live_dir)
        self.live_dir.mkdir(parents=True, exist_ok=True)
        self.vector_dir = Path(vector_dir)
        self.vector_dir.mkdir(parents=True, exist_ok=True)
        self.vectors = VectorStore(self.vector_dir / f"{session_id}.faiss")
        self._lock = threading.Lock()
        self.pairs: list[dict[str, Any]] = []  # live, in-memory only

    # ---- live recording (no persistence yet) -----------------------------
    def add_turn(self, user: str, assistant: str, *, turn: int | None = None) -> None:
        """Record one exchange. Kept in memory until the session ends."""
        if not user and not assistant:
            return
        with self._lock:
            self.pairs.append({
                "user": user,
                "assistant": assistant,
                "turn": turn if turn is not None else len(self.pairs) + 1,
                "text": f"User: {user}\nAssistant: {assistant}",
                "created_at": _iso(_now()),
            })

    def live_count(self) -> int:
        return len(self.pairs)

    # ---- end of session: persist + embed ---------------------------------
    def end_session(self) -> dict[str, Any]:
        """Persist to disk (with 1h expiry) and embed all pairs into the vector store."""
        with self._lock:
            pairs = list(self.pairs)
            if not pairs:
                return {"persisted": 0, "embedded": 0, "expires_at": None}
            now = _now()
            expires_at = now + timedelta(seconds=TTL_SECONDS)
            snapshot = {
                "session_id": self.session_id,
                "created_at": pairs[0].get("created_at"),
                "ended_at": _iso(now),
                "expires_at": _iso(expires_at),
                "pairs": pairs,
            }
            live_path = self.live_dir / f"{self.session_id}.json"
            live_path.write_text(
                json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            self.vectors.add_pairs(pairs)
            return {
                "persisted": len(pairs),
                "embedded": len(pairs),
                "expires_at": _iso(expires_at),
                "path": str(live_path),
            }

    # ---- expiry ----------------------------------------------------------
    def is_expired(self, now: datetime | None = None) -> bool:
        live_path = self.live_dir / f"{self.session_id}.json"
        if not live_path.exists():
            return True
        try:
            data = json.loads(live_path.read_text(encoding="utf-8"))
        except Exception:
            return True
        exp = data.get("expires_at")
        if not exp:
            return True
        try:
            exp_dt = datetime.fromisoformat(exp)
        except Exception:
            return True
        return (now or _now()) >= exp_dt

    def delete(self) -> None:
        with self._lock:
            live_path = self.live_dir / f"{self.session_id}.json"
            if live_path.exists():
                live_path.unlink()
            self.vectors.clear()
            self.pairs = []

    def retrieve(self, query: str, k: int = 1) -> list[dict[str, Any]]:
        """Retrieve the single best matching past pair (no reranking)."""
        return self.vectors.search(query, k=k)
