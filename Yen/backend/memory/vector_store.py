"""
FAISS-backed vector store for conversation memory.

Strategy (per the memory design):
- Each (user_input, system_output) exchange is ONE pair and is stored as ONE vector.
- No reranking: retrieval takes exactly the single nearest neighbour (k=1).
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import numpy as np

from memory.embedder import embed_batch


class VectorStore:
    """A tiny FAISS index of conversation pairs for a single owner (user/session)."""

    def __init__(self, index_path: Path) -> None:
        self.index_path = Path(index_path)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._index = None
        self._records: list[dict[str, Any]] = []
        self._load()

    # ---- persistence -----------------------------------------------------
    def _load(self) -> None:
        try:
            import faiss

            meta = self.index_path.with_suffix(".json")
            if meta.exists():
                self._records = json.loads(meta.read_text(encoding="utf-8"))
            if self.index_path.exists() and self._records:
                self._index = faiss.read_index(str(self.index_path))
            else:
                self._index = faiss.IndexFlatIP(len(self._records[0]["vector"]) if self._records else 1024)
        except Exception:
            self._index = None
            self._records = []

    def _save(self) -> None:
        import faiss

        faiss.write_index(self._index, str(self.index_path))
        self.index_path.with_suffix(".json").write_text(
            json.dumps(self._records, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ---- writes ----------------------------------------------------------
    def add_pairs(self, pairs: list[dict[str, Any]]) -> None:
        """pairs: list of {"user": ..., "assistant": ..., "text": ..., "turn": int, ...}"""
        if not pairs:
            return
        with self._lock:
            import faiss

            if self._index is None:
                dim = len(embed_batch(["probe"])[0])
                self._index = faiss.IndexFlatIP(dim)
            texts = [p.get("text", "") for p in pairs]
            vecs = np.asarray(embed_batch(texts), dtype="float32")
            if vecs.ndim == 1:
                vecs = vecs.reshape(1, -1)
            start = len(self._records)
            for i, p in enumerate(pairs):
                rec = dict(p)
                rec["vector"] = vecs[i].tolist()
                self._records.append(rec)
            self._index.add(vecs)
            self._save()

    # ---- reads -----------------------------------------------------------
    def search(self, query: str, k: int = 1) -> list[dict[str, Any]]:
        """Return the single nearest pair (no reranking). Empty list if empty."""
        with self._lock:
            if self._index is None or len(self._records) == 0:
                return []
            q = np.asarray(embed_batch([query])[0], dtype="float32").reshape(1, -1)
            k = min(k, len(self._records))
            scores, idxs = self._index.search(q, k)
            out: list[dict[str, Any]] = []
            for score, idx in zip(scores[0], idxs[0]):
                if idx < 0:
                    continue
                rec = dict(self._records[idx])
                rec.pop("vector", None)
                rec["score"] = float(score)
                out.append(rec)
            return out

    def clear(self) -> None:
        with self._lock:
            self._records = []
            self._index = None
            for suf in ("", ".json"):
                p = self.index_path.with_suffix(suf)
                if p.exists():
                    p.unlink()

    @property
    def size(self) -> int:
        return len(self._records)
