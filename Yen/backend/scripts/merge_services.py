"""
Merge every formatted merged.json under data/markdown_chunks_flat/*/ into a
single simple dataset: data/services_merged.json

Unified item schema (minimal):
  - source_id : which source file the item came from
  - doc_id    : original document id
  - source    : "Danh mục" (danh mục giá)
  - id        : "Mã tương đương" (empty if absent)
  - context   : "Dịch vụ kỹ thuật" (tên dịch vụ)
  - price     : primary service price (VNĐ)
  - price_cs1 : "Giá Cơ sở 1 (VNĐ)"  (only when a second price kind exists)
  - price_cs2 : "Giá Cơ sở 2 (VNĐ)"  (only when both cơ sở prices exist)
  - stt       : "STT"
  - note      : "Ghi chú"

If an item has both "Giá Cơ sở 1" and "Giá Cơ sở 2", the two cơ sở prices are
exposed as `price_cs1` / `price_cs2`. Other price variants are folded into the
single `price` field. "raw" is dropped.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = sorted(glob.glob(str(ROOT / "data" / "markdown_chunks_flat" / "*" / "merged.json")))
OUT = ROOT / "data" / "services_merged.json"


def merge() -> None:
    items: list[dict] = []
    counts: dict[str, int] = {}
    for path in SOURCES:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        source_id = data.get("source_id")
        for doc in data.get("documents", []):
            item: dict = {
                "source_id": source_id,
                "doc_id": doc.get("doc_id", ""),
                "source": doc.get("source", ""),
                "id": doc.get("id", ""),
                "context": doc.get("context", ""),
                "price": doc.get("price", ""),
                "stt": doc.get("stt", ""),
                "note": doc.get("note", ""),
            }
            cs1 = doc.get("price_cs1", "")
            cs2 = doc.get("price_cs2", "")
            if cs1 and cs2:
                item["price_cs1"] = cs1
                item["price_cs2"] = cs2
            items.append(item)
        counts[source_id] = len(data.get("documents", []))
        print(f"merged {source_id}: {counts[source_id]} docs")

    out = {
        "document_count": len(items),
        "sources": counts,
        "documents": items,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT} with {len(items)} items total.")


if __name__ == "__main__":
    merge()
