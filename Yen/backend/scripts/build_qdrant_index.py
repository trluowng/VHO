# -*- coding: utf-8 -*-
"""Embed every RAG chunk with BGE-M3 (dense + sparse) and upsert into an
embedded (local-mode, no server) Qdrant collection, enabling hybrid search
(dense cosine + sparse lexical) over the Benh vien Tim Ha Noi knowledge base.

The single source of truth for chunks is data/markdown_chunks/services_merged.json
(built by data/scripts/merge_all_into_services.py, which consolidates the 8
narrative/legal merge.json folders plus the price-table rows into one
{document_count, sources, documents} file). Nothing else under
data/markdown_chunks/ is read here.

Run: python build_qdrant_index.py
First run downloads the BGE-M3 weights (~2.3GB) from Hugging Face and caches them.
"""
import json
import os
import uuid

from FlagEmbedding import BGEM3FlagModel
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, SparseVectorParams, PointStruct, SparseVector,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(BACKEND_DIR, "data")
SERVICES_PATH = os.path.join(DATA_DIR, "markdown_chunks", "services_merged.json")
QDRANT_PATH = os.path.join(DATA_DIR, "qdrant_storage")
COLLECTION = "benhvientimhanoi_rag"
BATCH_SIZE = 16
MAX_LENGTH = 512


def load_points():
    """Load every chunk from the single consolidated services_merged.json."""
    with open(SERVICES_PATH, encoding="utf-8") as f:
        data = json.load(f)

    points = []
    for row in data["documents"]:
        is_service_row = "price" in row or "stt" in row
        if is_service_row:
            parts = [row.get("source", ""), row.get("context", "")]
            if row.get("note"):
                parts.append(row["note"])
            if row.get("price"):
                parts.append(f"Gia: {row['price']} VND")
            text = " - ".join(p for p in parts if p)
            key = row["doc_id"]
            source_type = "service_row"
        else:
            text = row.get("context", "") or row.get("title", "")
            key = row["chunk_id"]
            source_type = "markdown_chunk"

        payload = dict(row)
        payload["source_type"] = source_type
        payload["text"] = text
        points.append((key, text, payload))
    return points


def stable_id(key: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def main():
    all_points = load_points()
    print(f"Loaded {len(all_points)} chunks from services_merged.json")

    print("Loading BGE-M3 model (first run downloads ~2.3GB)...")
    model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False)

    client = QdrantClient(path=QDRANT_PATH)
    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config={"dense": VectorParams(size=1024, distance=Distance.COSINE)},
        sparse_vectors_config={"sparse": SparseVectorParams()},
    )

    total = len(all_points)
    for i in range(0, total, BATCH_SIZE):
        batch = all_points[i:i + BATCH_SIZE]
        texts = [t for _, t, _ in batch]
        out = model.encode(
            texts, batch_size=BATCH_SIZE, max_length=MAX_LENGTH,
            return_dense=True, return_sparse=True, return_colbert_vecs=False,
        )
        dense_vecs = out["dense_vecs"]
        lexical_weights = out["lexical_weights"]

        qdrant_points = []
        for (key, _text, payload), dvec, sw in zip(batch, dense_vecs, lexical_weights):
            indices = [int(k) for k in sw.keys()]
            values = [float(v) for v in sw.values()]
            qdrant_points.append(PointStruct(
                id=stable_id(key),
                vector={
                    "dense": dvec.tolist(),
                    "sparse": SparseVector(indices=indices, values=values),
                },
                payload=payload,
            ))
        client.upsert(collection_name=COLLECTION, points=qdrant_points)
        print(f"  upserted {min(i + BATCH_SIZE, total)}/{total}")

    info = client.get_collection(COLLECTION)
    print("Done. points_count =", info.points_count)


if __name__ == "__main__":
    main()
