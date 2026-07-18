# -*- coding: utf-8 -*-
import csv
import json
import os
import math

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.dirname(SCRIPT_DIR)  # scripts/ -> data/
STRUCTURED_DIR = os.path.join(DATA_DIR, "structured")
CHUNKS_DIR = os.path.join(DATA_DIR, "markdown_chunks")

CHAR_BUDGET = 2800   # ~ under 1024 tokens for Vietnamese text incl. markdown table syntax
MAX_ROWS_PER_CHUNK = 60

def fmt_price(v):
    v = (v or "").strip()
    if not v:
        return ""
    try:
        return f"{int(v):,}".replace(",", ".")
    except ValueError:
        return v

def esc(v):
    v = (v or "").strip()
    return v.replace("|", "\\|").replace("\n", " ")

def yaml_val(v):
    if isinstance(v, str) and (":" in v or '"' in v or v == ""):
        return '"' + v.replace('"', '\\"') + '"'
    return v

def write_chunk(out_dir, doc_prefix, chunk_idx, meta, header_cols, rows_data):
    fname = f"{doc_prefix}_{chunk_idx:03d}.md"
    path = os.path.join(out_dir, fname)
    lines = ["---"]
    for k, v in meta.items():
        lines.append(f"{k}: {yaml_val(v)}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {meta['danh_muc']}" + (f" — {meta['nhom_con']}" if meta.get("nhom_con") else ""))
    lines.append("")
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("|" + "|".join(["---"] * len(header_cols)) + "|")
    for row in rows_data:
        lines.append("| " + " | ".join(row) + " |")
    content = "\n".join(lines) + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return fname, len(content)

def chunk_document(csv_path, out_dir, doc_prefix, danh_muc_col, nhom_con_col,
                    col_map, source_meta):
    """col_map: list of (csv_field, display_name, is_price) in desired display order."""
    os.makedirs(out_dir, exist_ok=True)
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    groups = []
    cur_key = None
    cur_rows = []
    for r in rows:
        key = (r.get(danh_muc_col, ""), r.get(nhom_con_col, "") if nhom_con_col else "")
        if key != cur_key:
            if cur_rows:
                groups.append((cur_key, cur_rows))
            cur_key = key
            cur_rows = []
        cur_rows.append(r)
    if cur_rows:
        groups.append((cur_key, cur_rows))

    index = []
    chunk_idx = 1
    for (danh_muc, nhom_con), grp_rows in groups:
        # determine which columns have any non-empty value in this whole group
        active_cols = []
        for field, disp, is_price in col_map:
            if any((r.get(field, "") or "").strip() for r in grp_rows):
                active_cols.append((field, disp, is_price))
        if not active_cols:
            active_cols = col_map

        header_cols = [c[1] for c in active_cols]

        buf_rows = []
        buf_chars = 0
        buf_stt_first = None
        buf_stt_last = None
        for r in grp_rows:
            row_cells = []
            for field, disp, is_price in active_cols:
                val = r.get(field, "")
                row_cells.append(fmt_price(val) if is_price else esc(val))
            row_line_len = sum(len(c) for c in row_cells) + 3 * len(row_cells)
            if buf_rows and (buf_chars + row_line_len > CHAR_BUDGET or len(buf_rows) >= MAX_ROWS_PER_CHUNK):
                meta = dict(source_meta)
                meta.update({
                    "doc_id": f"{doc_prefix}_{chunk_idx:03d}",
                    "loai_tai_lieu": "bang_gia_dich_vu",
                    "danh_muc": danh_muc,
                    "nhom_con": nhom_con or "",
                    "stt_tu": buf_stt_first or "",
                    "stt_den": buf_stt_last or "",
                    "so_dong": len(buf_rows),
                })
                fname, clen = write_chunk(out_dir, doc_prefix, chunk_idx, meta, header_cols, buf_rows)
                index.append({"doc_id": meta["doc_id"], "path": f"markdown_chunks/{os.path.basename(out_dir)}/{fname}",
                              "danh_muc": danh_muc, "nhom_con": nhom_con or "", "stt_tu": buf_stt_first,
                              "stt_den": buf_stt_last, "so_dong": len(buf_rows), "chars": clen})
                chunk_idx += 1
                buf_rows = []
                buf_chars = 0
                buf_stt_first = None
            if buf_stt_first is None:
                buf_stt_first = r.get("STT", "")
            buf_stt_last = r.get("STT", "")
            buf_rows.append(row_cells)
            buf_chars += row_line_len

        if buf_rows:
            meta = dict(source_meta)
            meta.update({
                "doc_id": f"{doc_prefix}_{chunk_idx:03d}",
                "loai_tai_lieu": "bang_gia_dich_vu",
                "danh_muc": danh_muc,
                "nhom_con": nhom_con or "",
                "stt_tu": buf_stt_first or "",
                "stt_den": buf_stt_last or "",
                "so_dong": len(buf_rows),
            })
            fname, clen = write_chunk(out_dir, doc_prefix, chunk_idx, meta, header_cols, buf_rows)
            index.append({"doc_id": meta["doc_id"], "path": f"markdown_chunks/{os.path.basename(out_dir)}/{fname}",
                          "danh_muc": danh_muc, "nhom_con": nhom_con or "", "stt_tu": buf_stt_first,
                          "stt_den": buf_stt_last, "so_dong": len(buf_rows), "chars": clen})
            chunk_idx += 1

    with open(os.path.join(out_dir, "_index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    total_rows = sum(x["so_dong"] for x in index)
    print(f"{doc_prefix}: {len(index)} chunks, {total_rows} rows total, "
          f"avg {round(sum(x['chars'] for x in index)/len(index))} chars/chunk, "
          f"max {max(x['chars'] for x in index)} chars")
    return index


# ---- Document 1: BHYT ----
chunk_document(
    csv_path=os.path.join(STRUCTURED_DIR, "bang_gia_BHYT_full.csv"),
    out_dir=os.path.join(CHUNKS_DIR, "bhyt_2023"),
    doc_prefix="bhyt",
    danh_muc_col="Danh_muc",
    nhom_con_col=None,
    col_map=[
        ("STT", "STT", False),
        ("Ma_tuong_duong", "Mã tương đương", False),
        ("Dich_vu_ky_thuat", "Dịch vụ kỹ thuật", False),
        ("Gia_BHYT", "Giá BHYT chi trả tối đa (VNĐ)", True),
        ("Ghi_chu", "Ghi chú", False),
    ],
    source_meta={
        "benh_vien": "Bệnh viện Tim Hà Nội",
        "co_so_phap_ly": "Thông tư 22/2023/TT-BYT",
        "doi_tuong_ap_dung": "Người bệnh có thẻ BHYT",
        "file_goc": "raw/banggiaBHYT.pdf",
        "file_cau_truc": "structured/bang_gia_BHYT_full.csv",
    },
)

# ---- Document 2: DVKT 2025 (2 co so prices) ----
chunk_document(
    csv_path=os.path.join(STRUCTURED_DIR, "gia_dv_ky_thuat_2025_full.csv"),
    out_dir=os.path.join(CHUNKS_DIR, "dvkt_2025"),
    doc_prefix="dvkt2025",
    danh_muc_col="Danh_muc",
    nhom_con_col=None,
    col_map=[
        ("STT", "STT", False),
        ("Ma_tuong_duong", "Mã tương đương", False),
        ("Dich_vu_ky_thuat", "Dịch vụ kỹ thuật", False),
        ("Gia_Co_so_1", "Giá Cơ sở 1 (VNĐ)", True),
        ("Gia_Co_so_2", "Giá Cơ sở 2 (VNĐ)", True),
        ("Ghi_chu", "Ghi chú", False),
    ],
    source_meta={
        "benh_vien": "Bệnh viện Tim Hà Nội",
        "co_so_phap_ly": "Phụ lục số 06 Nghị quyết số 45/2024/NQ-HĐND ngày 10/12/2024 của HĐND TP Hà Nội",
        "doi_tuong_ap_dung": "Người bệnh có và không có thẻ BHYT",
        "file_goc": "raw/gia_dv_ky_thuat_2025.pdf",
        "file_cau_truc": "structured/gia_dv_ky_thuat_2025_full.csv",
    },
)

# ---- Document 3: DVKT thuong (Thong tu 14/2019) ----
chunk_document(
    csv_path=os.path.join(STRUCTURED_DIR, "banggiaDVKT_full.csv"),
    out_dir=os.path.join(CHUNKS_DIR, "dvkt_thuong"),
    doc_prefix="dvkt",
    danh_muc_col="Danh_muc",
    nhom_con_col="Nhom_con",
    col_map=[
        ("STT", "STT", False),
        ("Ma_tuong_duong", "Mã tương đương", False),
        ("Dich_vu_ky_thuat", "Dịch vụ kỹ thuật", False),
        ("Gia_dich_vu", "Giá dịch vụ (VNĐ)", True),
        ("Ghi_chu", "Ghi chú", False),
    ],
    source_meta={
        "benh_vien": "Bệnh viện Tim Hà Nội",
        "co_so_phap_ly": "Thông tư 14/2019/TT-BYT",
        "doi_tuong_ap_dung": "Giá dịch vụ kỹ thuật (không phân biệt BHYT)",
        "file_goc": "raw/banggiaDVKT.pdf",
        "file_cau_truc": "structured/banggiaDVKT_full.csv",
    },
)

# ---- Document 4: DVKT theo yeu cau ----
chunk_document(
    csv_path=os.path.join(STRUCTURED_DIR, "banggiaDVKTYC_full.csv"),
    out_dir=os.path.join(CHUNKS_DIR, "dvkt_yeu_cau"),
    doc_prefix="dvktyc",
    danh_muc_col="Danh_muc",
    nhom_con_col=None,
    col_map=[
        ("STT", "STT", False),
        ("Ma_tuong_duong", "Mã tương đương", False),
        ("Dich_vu_ky_thuat", "Dịch vụ kỹ thuật", False),
        ("Gia_dich_vu", "Giá dịch vụ (VNĐ)", True),
        ("Gia_kham_benh", "Giá khám bệnh (VNĐ)", True),
        ("Gia_dich_vu_theo_yeu_cau", "Giá dịch vụ theo yêu cầu (VNĐ)", True),
        ("Ghi_chu", "Ghi chú", False),
    ],
    source_meta={
        "benh_vien": "Bệnh viện Tim Hà Nội",
        "co_so_phap_ly": "Quyết định 2823/QĐ-BVT (khám theo yêu cầu); Quyết định 3165/QĐ-BVT (MRI/CLVT ngoài giờ theo yêu cầu)",
        "doi_tuong_ap_dung": "Dịch vụ kỹ thuật theo yêu cầu (tự nguyện)",
        "file_goc": "raw/banggiaDVKTYC.pdf",
        "file_cau_truc": "structured/banggiaDVKTYC_full.csv",
    },
)
