"""
Conversation memory for Yên (Bệnh viện Tim Hà Nội assistant).

Strategy
--------
- Turns are kept in live memory ONLY while the user is talking.
- On disconnect / leave (end_session), the conversation is persisted to disk with a
  1-hour TTL, and every (user_input, system_output) pair is embedded and stored as ONE
  vector in a FAISS index (bge-m3).
- Retrieval returns the single nearest past pair (k=1), no reranking.

Public API:
    from memory import MemoryManager, default
    mm = default()                       # singleton, starts sweeper
    mm.record_turn(session_id, user, assistant)
    mm.end_session(session_id)           # user left / disconnected
    mm.retrieve(session_id, query)       # top-1 past pair
    mm.sweep_once()                       # drop expired conversations + vectors
"""
from __future__ import annotations

from memory.manager import MemoryManager, default
from memory.store import ConversationStore, TTL_SECONDS
from memory.vector_store import VectorStore

__all__ = ["MemoryManager", "default", "ConversationStore", "VectorStore", "TTL_SECONDS"]
