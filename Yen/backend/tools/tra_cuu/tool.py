"""Tra cứu quy trình hành chính, chính sách khám chữa bệnh và luật liên quan.

Nguồn: các chunk markdown đã được xử lý sẵn (chunking + front-matter) tại
data/markdown_chunks/{luat_kbcb, huong_dan, youmed_gioi_thieu}/*.md — Luật
Khám bệnh, chữa bệnh 15/2023/QH15, hướng dẫn đặt lịch/chi phí, và bài giới
thiệu quy trình khám tại bệnh viện. Không bao gồm các thư mục bảng giá
(bhyt_2023, dvkt_*) vì việc tra giá đã có tool `tra_gia` riêng.

Tìm bằng keyword-overlap trên nội dung đã fold dấu, không dùng embedding để
tránh thêm một điểm phụ thuộc API bên ngoài.
"""
from __future__ import annotations

import math
import re
from typing import Any

import yaml

from tools._shared import ROOT, err, fold_text, terms

_CHUNK_DIRS = ["luat_kbcb", "huong_dan", "youmed_gioi_thieu"]
_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
_MAX_CONTENT_CHARS = 700

_index: list[dict[str, Any]] | None = None  # each: {meta, body, term_set, folded_body}
_idf: dict[str, float] | None = None


def _parse_chunk(path) -> dict[str, Any] | None:
    raw = path.read_text(encoding="utf-8")
    match = _FRONT_MATTER_RE.match(raw)
    if not match:
        return None
    meta = yaml.safe_load(match.group(1)) or {}
    body = match.group(2).strip()
    return {"meta": meta, "body": body}


def _load_idf() -> dict[str, float]:
    global _idf
    if _idf is None:
        items = _load_index()
        doc_freq: dict[str, int] = {}
        for item in items:
            for term in item["term_set"]:
                doc_freq[term] = doc_freq.get(term, 0) + 1
        n = len(items) or 1
        # Smoothed idf: common words (e.g. "cách", "khám" appearing in nearly every
        # chunk) end up with near-zero weight so they stop drowning out documents
        # that only share those words incidentally, while rare/specific terms (e.g.
        # "lịch", "BHYT") keep strong weight -- found necessary after live-testing
        # showed generic-word overlap burying the actually relevant chunk.
        _idf = {term: math.log((n + 1) / (df + 1)) + 1 for term, df in doc_freq.items()}
    return _idf


def _load_index() -> list[dict[str, Any]]:
    global _index
    if _index is None:
        chunks_root = ROOT / "data" / "markdown_chunks"
        items: list[dict[str, Any]] = []
        for dir_name in _CHUNK_DIRS:
            dir_path = chunks_root / dir_name
            if not dir_path.exists():
                continue
            for md_path in sorted(dir_path.glob("*.md")):
                parsed = _parse_chunk(md_path)
                if not parsed:
                    continue
                meta = parsed["meta"]
                searchable = f"{meta.get('tieu_de_dieu', '')} {meta.get('tieu_de', '')} {meta.get('danh_muc', '')} {parsed['body']}"
                items.append(
                    {
                        "meta": parsed["meta"],
                        "body": parsed["body"],
                        "term_set": terms(searchable),
                        "folded": fold_text(searchable),
                        "source_dir": dir_name,
                    }
                )
        _index = items
    return _index


def _title_of(meta: dict[str, Any]) -> str:
    return (
        meta.get("tieu_de_dieu")
        or meta.get("tieu_de")
        or meta.get("danh_muc")
        or meta.get("doc_id")
        or "Không rõ tiêu đề"
    )


def _reference_of(meta: dict[str, Any], source_dir: str) -> str:
    if source_dir == "luat_kbcb":
        dieu = meta.get("dieu")
        so_hieu = meta.get("so_hieu", "")
        return f"Điều {dieu} - Luật KBCB {so_hieu}".strip()
    if source_dir == "huong_dan":
        return "Hướng dẫn hành chính - Bệnh viện Tim Hà Nội"
    return f"Bài viết bên thứ ba (YouMed) - {meta.get('nguon', '')} - không phải nguồn chính thức từ bệnh viện"


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
        scored: list[tuple[float, dict[str, Any]]] = []
        for item in _load_index():
            score = sum(idf.get(term, 1.0) for term in query_terms & item["term_set"])
            if folded_query and folded_query in item["folded"]:
                score += 3
            if score > 0:
                scored.append((score, item))
        scored.sort(key=lambda pair: -pair[0])

        items = []
        for _, item in scored[:max_results]:
            body = item["body"]
            truncated = body[:_MAX_CONTENT_CHARS] + ("…" if len(body) > _MAX_CONTENT_CHARS else "")
            items.append(
                {
                    "tieu_de": _title_of(item["meta"]),
                    "tham_chieu": _reference_of(item["meta"], item["source_dir"]),
                    "noi_dung": truncated,
                }
            )
        return {"tool": "tra_cuu", "query": query, "so_ket_qua": len(scored), "items": items}
    except Exception as exc:
        return err("tra_cuu", exc)
