"""Tra cứu quy trình hành chính, chính sách khám chữa bệnh và luật liên quan.

Nguồn: data/markdown_chunks/services_merged.json -- cùng file gộp mà `tra_gia`
dùng (xem tools/tra_gia/tool.py), lọc theo `source_id` thuộc nhóm "nội dung
tường thuật" (luật, quy trình, giới thiệu khoa/dịch vụ...) thay vì nhóm bảng
giá (bhyt_2023, dvkt_*) -- bảng giá đã có tool `tra_gia` riêng.

Trước đây tool này đọc từ các file .md rời trong data/markdown_chunks/{luat_kbcb,
huong_dan, youmed_gioi_thieu}/ -- nhưng các thư mục đó không tồn tại trên đĩa
(đã được gộp hết vào services_merged.json bởi data/scripts/merge_all_into_services.py
mà không cập nhật lại tool này), khiến tra_cuu luôn trả về 0 kết quả bất kể môi
trường nào (xác nhận qua live test). Đọc thẳng từ services_merged.json để khớp
với dữ liệu thật đang có.

Tìm bằng keyword-overlap trên nội dung đã fold dấu, không dùng embedding để
tránh thêm một điểm phụ thuộc API bên ngoài.
"""
from __future__ import annotations

import json
import math
from typing import Any

from tools._shared import ROOT, err, fold_text, terms

_SERVICES_PATH = ROOT / "data" / "markdown_chunks" / "services_merged.json"

# Mọi source_id "tường thuật" (không phải bảng giá) trong services_merged.json --
# xem data/scripts/merge_all_into_services.py:NARRATIVE_FOLDERS.
_NARRATIVE_SOURCES = {
    "luat_kbcb", "quy_trinh", "youmed_gioi_thieu", "lich_su_phat_trien",
    "khoa_phong", "huong_dan", "dich_vu", "bookingcare_gioi_thieu",
}
_MAX_CONTENT_CHARS = 700

_index: list[tuple[dict, set[str], str]] | None = None  # (doc, term_set, folded_context)
_idf: dict[str, float] | None = None


def _load_index() -> list[tuple[dict, set[str], str]]:
    global _index
    if _index is None:
        data = json.loads(_SERVICES_PATH.read_text(encoding="utf-8"))
        _index = [
            (doc, terms(f"{doc.get('title', '')} {doc.get('context', '')}"), fold_text(doc.get("context", "")))
            for doc in data.get("documents", [])
            if doc.get("source_id") in _NARRATIVE_SOURCES
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
        # Smoothed idf: common words (e.g. "cách", "khám" appearing in nearly every
        # chunk) end up with near-zero weight so they stop drowning out documents
        # that only share those words incidentally, while rare/specific terms (e.g.
        # "lịch", "BHYT") keep strong weight -- found necessary after live-testing
        # showed generic-word overlap burying the actually relevant chunk.
        _idf = {term: math.log((n + 1) / (df + 1)) + 1 for term, df in doc_freq.items()}
    return _idf


def _title_of(doc: dict[str, Any]) -> str:
    return doc.get("title") or doc.get("section") or doc.get("doc_id") or "Không rõ tiêu đề"


def _reference_of(doc: dict[str, Any]) -> str:
    source_id = doc.get("source_id")
    if source_id == "luat_kbcb":
        dieu = doc.get("dieu")
        so_hieu = doc.get("so_hieu", "")
        return f"Điều {dieu} - Luật KBCB {so_hieu}".strip()
    if source_id in {"quy_trinh", "huong_dan", "khoa_phong", "dich_vu", "lich_su_phat_trien"}:
        return "Bệnh viện Tim Hà Nội"
    if source_id == "youmed_gioi_thieu":
        return "Bài viết bên thứ ba (YouMed) - không phải nguồn chính thức từ bệnh viện"
    if source_id == "bookingcare_gioi_thieu":
        return "Bài viết bên thứ ba (BookingCare) - không phải nguồn chính thức từ bệnh viện"
    return "Không rõ nguồn"


def search_policy(query: str = "", max_results: int = 3) -> dict[str, Any]:
    try:
        query = (query or "").strip()
        if not query:
            return {
                "tool": "tra_cuu", "query": query, "items": [],
                "error": "missing_query",
                "note": "LỖI: tham số 'query' bị để trống. Hãy GỌI LẠI tool tra_cuu ngay với query = nội dung khách vừa hỏi (vd: 'cách đặt lịch khám').",
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

        items = []
        for _, doc in scored[:max_results]:
            body = doc.get("context", "")
            truncated = body[:_MAX_CONTENT_CHARS] + ("…" if len(body) > _MAX_CONTENT_CHARS else "")
            items.append({
                "tieu_de": _title_of(doc),
                "tham_chieu": _reference_of(doc),
                "noi_dung": truncated,
            })
        return {"tool": "tra_cuu", "query": query, "so_ket_qua": len(scored), "items": items}
    except Exception as exc:
        return err("tra_cuu", exc)
