# -*- coding: utf-8 -*-
"""Add the standardized cross-corpus metadata fields to every chunk in the 11
non-law folders, as 3 distinct ID concepts (not merged into one):
  - doc_id: constant per source document/folder (e.g. "bhyt_2023" for every chunk
    in that folder)
  - chunk_id: unique per chunk (the original per-file id, e.g. "bhyt_001")
  - parent_id: chunk_id of the parent chunk, or "" (no hierarchy in these folders)
plus source_doc, section, category, effective_date, approved_by. Existing fields
are kept as-is; new fields are inserted first."""
import re
import os
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.dirname(SCRIPT_DIR)
CHUNKS_DIR = os.path.join(DATA_DIR, "markdown_chunks")

# per-folder defaults; a field left as None means "derive from the file's own
# front-matter if possible, else leave blank"
FOLDER_DEFAULTS = {
    "bhyt_2023": {
        "source_doc": "Thông tư 22/2023/TT-BYT",
        "category": "bao_hiem_y_te",
        "approved_by": "Bộ Y tế",
    },
    "dvkt_2025": {
        "source_doc": "Phụ lục số 06 Nghị quyết số 45/2024/NQ-HĐND",
        "category": "gia_dich_vu",
        "approved_by": "HĐND TP Hà Nội",
    },
    "dvkt_thuong": {
        "source_doc": "Thông tư 14/2019/TT-BYT",
        "category": "gia_dich_vu",
        "approved_by": "Bộ Y tế",
    },
    "dvkt_yeu_cau": {
        "source_doc": "Quyết định 2823/QĐ-BVT; Quyết định 3165/QĐ-BVT",
        "category": "gia_dich_vu",
        "approved_by": "Bệnh viện Tim Hà Nội",
    },
    "huong_dan": {
        "source_doc": None,  # derive from each file's own `nguon`
        "category": "huong_dan_benh_nhan",
        "approved_by": "",
    },
    "khoa_phong": {
        "source_doc": "benhvientimhanoi.vn",
        "category": "to_chuc_khoa_phong",
        "approved_by": "",
    },
    "youmed_gioi_thieu": {
        "source_doc": "youmed.vn",
        "category": "gioi_thieu_benh_vien",
        "approved_by": "",
    },
    "quy_trinh": {
        "source_doc": "Quy trình QT.25.01 - Bệnh viện Tim Hà Nội",
        "category": "quy_trinh_noi_bo",
        "approved_by": None,  # derive from nguoi_phe_duyet
    },
    "lich_su_phat_trien": {
        "source_doc": "benhvientimhanoi.vn",
        "category": "gioi_thieu_benh_vien",
        "approved_by": "",
    },
    "bookingcare_gioi_thieu": {
        "source_doc": "bookingcare.vn",
        "category": "gioi_thieu_benh_vien",
        "approved_by": "",
    },
    "dich_vu": {
        "source_doc": "benhvientimhanoi.vn",
        "category": "dich_vu_y_te",
        "approved_by": "",
    },
}

def unquote(v):
    v = v.strip()
    if v.startswith('"') and v.endswith('"'):
        return v[1:-1].replace('\\"', '"')
    return v

def quote_if_needed(v):
    v = str(v)
    if any(c in v for c in [":", '"']) or v == "":
        return '"' + v.replace('"', '\\"') + '"'
    return v

def parse_front_matter(text):
    m = re.match(r"^---\n(.*?)\n---\n\n(.*)$", text, re.DOTALL)
    fm_text, body = m.group(1), m.group(2)
    fm = {}
    order = []
    for line in fm_text.split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip()
            fm[k] = unquote(v)
            order.append(k)
    return fm, order, body

def derive_section(fm):
    if "tieu_de" in fm and fm["tieu_de"]:
        return fm["tieu_de"]
    if "danh_muc" in fm and fm["danh_muc"]:
        s = fm["danh_muc"]
        if fm.get("nhom_con"):
            s += f" — {fm['nhom_con']}"
        if fm.get("stt_tu") and fm.get("stt_den"):
            s += f" (STT {fm['stt_tu']}-{fm['stt_den']})"
        return s
    if "muc" in fm and fm["muc"]:
        return fm["muc"]
    return ""

def derive_effective_date(fm):
    for k in ("ngay_hieu_luc", "ngay_ban_hanh", "ngay_cap_nhat", "ngay_dang"):
        if fm.get(k):
            return fm[k]
    return ""

def process_folder(rel_folder):
    folder = os.path.join(CHUNKS_DIR, rel_folder)
    defaults = FOLDER_DEFAULTS[rel_folder]
    files = sorted(f for f in os.listdir(folder) if f.endswith(".md"))
    for fname in files:
        path = os.path.join(folder, fname)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        fm, order, body = parse_front_matter(text)

        # chunk_id = this chunk's own unique identifier, from whichever earlier
        # field carried it (chunk_id > id > doc_id, in case of repeated runs)
        chunk_id = fm.get("chunk_id", fm.get("id", fm.get("doc_id", "")))
        source_doc = defaults["source_doc"] if defaults["source_doc"] is not None else fm.get("nguon", "")
        category = defaults["category"]
        effective_date = derive_effective_date(fm)
        approved_by = defaults["approved_by"] if defaults["approved_by"] is not None else fm.get("nguoi_phe_duyet", "")
        section = derive_section(fm)

        new_fm = {
            "doc_id": rel_folder,   # constant: every chunk in this folder shares one source doc
            "chunk_id": chunk_id,
            "parent_id": "",
            "source_doc": source_doc,
            "category": category,
            "effective_date": effective_date,
            "approved_by": approved_by,
            "section": section,
        }
        standard_keys = {"doc_id", "chunk_id", "parent_id", "id", "source_doc",
                          "category", "effective_date", "approved_by", "section",
                          "parent_chunk_id"}
        for k in order:
            if k in standard_keys:
                continue
            new_fm[k] = fm[k]

        yaml_lines = ["---"]
        for k, v in new_fm.items():
            yaml_lines.append(f"{k}: {quote_if_needed(v)}")
        yaml_lines.append("---")

        new_text = "\n".join(yaml_lines) + "\n\n" + body
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_text)

    # rebuild _index.json
    index = []
    for fname in files:
        path = os.path.join(folder, fname)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        fm, _, _ = parse_front_matter(text)
        index.append({
            "doc_id": fm.get("doc_id", ""),
            "chunk_id": fm.get("chunk_id", ""),
            "parent_id": fm.get("parent_id", ""),
            "path": f"markdown_chunks/{rel_folder}/{fname}",
            "section": fm.get("section", ""),
            "source_doc": fm.get("source_doc", ""),
            "category": fm.get("category", ""),
            "effective_date": fm.get("effective_date", ""),
            "approved_by": fm.get("approved_by", ""),
            "danh_muc": fm.get("danh_muc", ""),
            "nhom_con": fm.get("nhom_con", ""),
            "stt_tu": fm.get("stt_tu", ""),
            "stt_den": fm.get("stt_den", ""),
            "so_dong": fm.get("so_dong", ""),
            "chars": len(text),
        })
    with open(os.path.join(folder, "_index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"{rel_folder}: {len(index)} chunks updated")

if __name__ == "__main__":
    for rel_folder in FOLDER_DEFAULTS:
        process_folder(rel_folder)
