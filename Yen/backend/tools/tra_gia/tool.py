"""Tra cứu giá dịch vụ kỹ thuật/khám bệnh tại Bệnh viện Tim Hà Nội.

Nguồn: data/services_merged.json — 4.674 dòng gộp từ 4 bảng giá chính thức
(BHYT 2023, DVKT 2025, DVKT thường, DVKT theo yêu cầu). Tìm theo từ khóa trên
tên dịch vụ (`context`), không cần embedding vì đây là tra cứu tên chính xác/
gần đúng, không phải câu hỏi ngữ nghĩa mở.
"""
from __future__ import annotations

import json
import math
from typing import Any

from tools._shared import ROOT, err, fold_text, terms

_SERVICES_PATH = ROOT / "data" / "markdown_chunks" / "services_merged.json"
_index: list[tuple[dict, set[str], str]] | None = None  # (doc, term_set, folded_context)
_idf: dict[str, float] | None = None


def _load_index() -> list[tuple[dict, set[str], str]]:
    global _index
    if _index is None:
        data = json.loads(_SERVICES_PATH.read_text(encoding="utf-8"))
        _index = [
            (doc, terms(doc.get("context", "")), fold_text(doc.get("context", "")))
            for doc in data.get("documents", [])
        ]
    return _index


def _load_idf() -> dict[str, float]:
    global _idf
    if _idf is None:
        items = _load_index()
        doc_freq: dict[str, int] = {}
        for _, doc_terms, _folded in items:
            for term in doc_terms:
                doc_freq[term] = doc_freq.get(term, 0) + 1
        n = len(items) or 1
        # Flat term-overlap scoring weighted generic words (e.g. "khám", "chụp")
        # the same as specific ones, so queries could rank unrelated services
        # above the intended match just because they shared a common word --
        # confirmed by live testing. Smoothed idf makes rare/specific terms
        # dominate the score instead. This does not fix pure vocabulary gaps
        # (e.g. "điện tâm đồ" vs. the price sheet's "Điện tim" for the same
        # test share no terms at all) -- that would need a synonym table.
        _idf = {term: math.log((n + 1) / (df + 1)) + 1 for term, df in doc_freq.items()}
    return _idf


def _format_price(price: Any) -> str:
    if isinstance(price, dict):
        parts = [f"{label}: {value} VNĐ" for label, value in price.items() if value]
        return "; ".join(parts) if parts else "—"
    return f"{price} VNĐ" if price else "—"


def search_price(query: str = "", max_results: int = 8) -> dict[str, Any]:
    try:
        query = (query or "").strip()
        if not query:
            return {
                "tool": "tra_gia", "query": query, "items": [],
                "error": "missing_query",
                "note": "LỖI: tham số 'query' bị để trống. Hãy GỌI LẠI tool tra_gia ngay với query = tên dịch vụ khách vừa hỏi (vd: 'siêu âm tim').",
            }

        query_terms = terms(query)
        folded_query = fold_text(query)
        idf = _load_idf()
        scored: list[tuple[float, dict]] = []
        for doc, doc_terms, folded_context in _load_index():
            score = sum(idf.get(term, 1.0) for term in query_terms & doc_terms)
            if folded_query and folded_query in folded_context:
                score += 3
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda pair: -pair[0])

        items = [
            {
                "danh_muc": doc.get("source"),
                "ten_dich_vu": doc.get("context"),
                "gia": _format_price(doc.get("price")),
                "ghi_chu": doc.get("note") or None,
                "nguon": doc.get("source_id"),
            }
            for _, doc in scored[:max_results]
        ]
        return {"tool": "tra_gia", "query": query, "so_ket_qua": len(scored), "items": items}
    except Exception as exc:
        return err("tra_gia", exc)
