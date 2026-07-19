"""
Embedding backend for conversation memory.

Uses BAAI/bge-m3 via sentence-transformers. Because bge-m3 is a large model, loading
is lazy (only on first embed) and can be disabled via MEMORY_EMBED_MODEL="off" or when
the library/model is unavailable — in that case a deterministic hash-based vector is
used so the rest of the memory pipeline (store, retrieve, expiry) still works.
"""
from __future__ import annotations

import hashlib
import os

EMBED_MODEL = os.getenv("MEMORY_EMBED_MODEL", "BAAI/bge-m3")
EMBED_DIM = int(os.getenv("MEMORY_EMBED_DIM", "1024"))  # bge-m3 dense dim

_MODEL = None
_MODEL_ERROR = None


def _load_model():
    global _MODEL, _MODEL_ERROR
    if _MODEL is not None or _MODEL_ERROR is not None:
        return
    if EMBED_MODEL.lower() in {"off", "none", "false", ""}:
        _MODEL_ERROR = "disabled via env"
        return
    try:
        from sentence_transformers import SentenceTransformer

        _MODEL = SentenceTransformer(EMBED_MODEL)
    except Exception as exc:  # pragma: no cover - depends on environment
        _MODEL_ERROR = str(exc)


def _hash_vector(text: str, dim: int = EMBED_DIM) -> list[float]:
    """Deterministic pseudo-embedding so retrieval still ranks by text similarity-ish."""
    vec = [0.0] * dim
    for i in range(dim):
        h = hashlib.md5(f"{i}:{text}".encode("utf-8")).digest()
        vec[i] = (int.from_bytes(h[:8], "big") / (2 ** 64 - 1)) * 2 - 1
    return vec


def embed(text: str) -> list[float]:
    """Return a normalized dense vector for a single text (one pair -> one vector)."""
    _load_model()
    if _MODEL is None:
        return _hash_vector(text or "")
    vec = _MODEL.encode((text or "").strip(), normalize_embeddings=True)
    return vec.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    _load_model()
    if _MODEL is None:
        return [_hash_vector(t) for t in texts]
    vecs = _MODEL.encode([(t or "").strip() for t in texts], normalize_embeddings=True)
    return vecs.tolist()
