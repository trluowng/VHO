"""
Memory manager: registry of live conversation stores + background sweeper.

Public API used by server.py / chat.py:
    from memory import MemoryManager
    mm = MemoryManager()                 # starts sweeper thread
    mm.record_turn(session_id, user, assistant)
    mm.end_session(session_id)           # user left / disconnected
    mm.retrieve(session_id, query)       # top-1 past pair from vector store
    mm.sweep_once()                       # delete expired conversations + vectors
"""
from __future__ import annotations

import threading
from pathlib import Path

from memory.store import ConversationStore, TTL_SECONDS

ROOT = Path(__file__).resolve().parent.parent
LIVE_DIR = ROOT / "memory" / "conversations"
VECTOR_DIR = ROOT / "memory" / "vectors"


class MemoryManager:
    def __init__(
        self,
        live_dir: Path = LIVE_DIR,
        vector_dir: Path = VECTOR_DIR,
        sweep_interval: float = 300.0,
        autostart_sweeper: bool = True,
    ) -> None:
        self.live_dir = Path(live_dir)
        self.vector_dir = Path(vector_dir)
        self.sweep_interval = sweep_interval
        self._stores: dict[str, ConversationStore] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        if autostart_sweeper:
            self.start_sweeper()

    # ---- live stores -----------------------------------------------------
    def _store(self, session_id: str) -> ConversationStore:
        with self._lock:
            st = self._stores.get(session_id)
            if st is None:
                st = ConversationStore(session_id, self.live_dir, self.vector_dir)
                self._stores[session_id] = st
            return st

    def record_turn(self, session_id: str, user: str, assistant: str, *, turn: int | None = None) -> None:
        self._store(session_id).add_turn(user, assistant, turn=turn)

    def end_session(self, session_id: str) -> dict:
        with self._lock:
            st = self._stores.pop(session_id, None)
        if st is None:
            # Nothing live; maybe it was already ended. Still allow re-embed from disk.
            st = ConversationStore(session_id, self.live_dir, self.vector_dir)
        return st.end_session()

    def retrieve(self, session_id: str, query: str, k: int = 1) -> list[dict]:
        # Search the live store's vectors (includes persisted pairs from this session).
        st = self._store(session_id)
        return st.retrieve(query, k=k)

    def live_count(self, session_id: str) -> int:
        with self._lock:
            st = self._stores.get(session_id)
        return st.live_count() if st else 0

    # ---- sweeper ---------------------------------------------------------
    def sweep_once(self) -> int:
        """Delete every persisted conversation whose expiry has passed. Returns count deleted."""
        deleted = 0
        for path in self.live_dir.glob("*.json"):
            sid = path.stem
            st = ConversationStore(sid, self.live_dir, self.vector_dir)
            if st.is_expired():
                st.delete()
                deleted += 1
        return deleted

    def start_sweeper(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        def _run() -> None:
            while not self._stop.wait(self.sweep_interval):
                try:
                    self.sweep_once()
                except Exception:
                    pass

        self._thread = threading.Thread(target=_run, name="memory-sweeper", daemon=True)
        self._thread.start()

    def stop_sweeper(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)


# Convenience singleton for import-as-module usage.
_default: MemoryManager | None = None


def default() -> MemoryManager:
    global _default
    if _default is None:
        _default = MemoryManager()
    return _default
