"""
Format every merged.json under data/markdown_chunks_flat/*/ so each document
carries a normalized set of fields:

  - source  <- "Danh mục"            (danh mục giá)
  - id      <- "Mã tương đương"      (mã tương đương, may be empty)
  - context <- "Dịch vụ kỹ thuật"    (tên dịch vụ kỹ thuật)
  - price   <- primary service price (VNĐ), chosen from the available price field(s)

All original fields are preserved (kept verbatim) and a few extra normalized
fields are added when available:

  - price_bhyt      : "Giá BHYT chi trả tối đa (VNĐ)"
  - price_cs1        : "Giá Cơ sở 1 (VNĐ)"
  - price_cs2        : "Giá Cơ sở 2 (VNĐ)"
  - price_khambenh  : "Giá khám bệnh (VNĐ)"
  - price_yeucau    : "Giá dịch vụ theo yêu cầu (VNĐ)"
  - note            : "Ghi chú"
  - stt             : "STT"
  - raw             : the untouched original fields dict

`price` selection priority (most relevant service price first):
  1. Giá dịch vụ (VNĐ)
  2. Giá Cơ sở 1 (VNĐ)
  3. Giá BHYT chi trả tối đa (VNĐ)
  4. Giá dịch vụ theo yêu cầu (VNĐ)
  5. Giá khám bệnh (VNĐ)
  6. Giá Cơ sở 2 (VNĐ)
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = sorted(glob.glob(str(ROOT / "data" / "markdown_chunks_flat" / "*" / "merged.json")))

PRICE_PRIORITY = [
    "Giá dịch vụ (VNĐ)",
    "Giá Cơ sở 1 (VNĐ)",
    "Giá BHYT chi trả tối đa (VNĐ)",
    "Giá dịch vụ theo yêu cầu (VNĐ)",
    "Giá khám bệnh (VNĐ)",
    "Giá Cơ sở 2 (VNĐ)",
]

EXTRA_MAP = {
    "price_bhyt": "Giá BHYT chi trả tối đa (VNĐ)",
    "price_cs1": "Giá Cơ sở 1 (VNĐ)",
    "price_cs2": "Giá Cơ sở 2 (VNĐ)",
    "price_khambenh": "Giá khám bệnh (VNĐ)",
    "price_yeucau": "Giá dịch vụ theo yêu cầu (VNĐ)",
    "note": "Ghi chú",
    "stt": "STT",
}


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def pick_price(fields: dict) -> str:
    for key in PRICE_PRIORITY:
        if key in fields and clean(fields[key]):
            return clean(fields[key])
    return ""


def format_document(doc: dict) -> dict:
    fields = doc.get("fields", {}) or {}

    normalized: dict = {
        "doc_id": doc.get("doc_id"),
        "source": clean(fields.get("Danh mục")),
        "id": clean(fields.get("Mã tương đương")),
        "context": clean(fields.get("Dịch vụ kỹ thuật")),
        "price": pick_price(fields),
    }

    for out_key, src_key in EXTRA_MAP.items():
        if src_key in fields:
            normalized[out_key] = clean(fields.get(src_key))

    normalized["raw"] = fields
    return normalized


def main() -> None:
    for path in TARGETS:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        documents = data.get("documents", [])
        formatted = [format_document(d) for d in documents]
        missing_context = [d["doc_id"] for d in formatted if not d["context"]]
        missing_price = [d["doc_id"] for d in formatted if not d["price"]]
        missing_id = [d["doc_id"] for d in formatted if not d["id"]]

        out = {
            "source_id": data.get("source_id"),
            "document_count": len(formatted),
            "documents": formatted,
        }
        Path(path).write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            f"{path}\n"
            f"  docs={len(formatted)}  "
            f"missing_context={len(missing_context)}  "
            f"missing_price={len(missing_price)}  "
            f"missing_id={len(missing_id)}"
        )


if __name__ == "__main__":
    main()
