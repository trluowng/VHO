# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(SCRIPT_DIR)  # scripts/ -> data/
CHUNKS_DIR = os.path.join(BASE, "markdown_chunks")

def load_index(rel_dir):
    path = os.path.join(CHUNKS_DIR, rel_dir, "_index.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def base_chunk(item, doc_source_fallback):
    """Build the common chunk-level fields every entry gets: the 3 distinct ID
    concepts (doc_id constant per document, chunk_id unique per chunk, parent_id
    for hierarchy) plus the 5 descriptive standardized fields."""
    return {
        "doc_id": item.get("doc_id", doc_source_fallback),
        "chunk_id": item.get("chunk_id", item.get("id", "")),
        "parent_id": item.get("parent_id", item.get("parent_chunk_id", "")),
        "path": item["path"],
        "chars": item["chars"],
        "source_doc": item.get("source_doc", ""),
        "section": item.get("section", ""),
        "category": item.get("category", ""),
        "effective_date": item.get("effective_date", ""),
        "approved_by": item.get("approved_by", ""),
    }

documents = []
all_chunks = []

# 1) Luat KBCB
luat_idx = load_index("luat_kbcb")
for item in luat_idx:
    chunk = base_chunk(item, "luat_kbcb_2023")
    chunk["extra"] = {"dieu": item["dieu"], "tieu_de": item["tieu_de"], "chuong": item["chuong"], "muc": item["muc"]}
    all_chunks.append(chunk)
documents.append({
    "source_id": "luat_kbcb_2023",
    "title": "Luật Khám bệnh, chữa bệnh số 15/2023/QH15",
    "loai_tai_lieu": "van_ban_phap_ly",
    "category": "van_ban_phap_ly",
    "source_doc": "Luật Khám bệnh, chữa bệnh số 15/2023/QH15",
    "raw_file": "raw/15_2023_QH15_372143.pdf",
    "structured_files": [],
    "markdown_chunk_dir": "markdown_chunks/luat_kbcb",
    "chunk_count": len(luat_idx),
    "so_hieu": "15/2023/QH15",
    "ngay_ban_hanh": "2023-01-09",
    "ngay_hieu_luc": "2024-01-01",
    "approved_by": "Quốc hội",
    "nguon": "https://thuvienphapluat.vn/van-ban/The-thao-Y-te/Luat-15-2023-QH15-kham-benh-chua-benh-372143.aspx",
})

# 2) Huong dan (mixed: PDF-sourced booking guide + YouMed-sourced cost guide)
huongdan_idx = load_index("huong_dan")
for item in huongdan_idx:
    chunk = base_chunk(item, "huong_dan")
    chunk["extra"] = {}
    all_chunks.append(chunk)
documents.append({
    "source_id": "huong_dan",
    "title": "Hướng dẫn cho người bệnh (đặt lịch khám, chi phí khám chữa bệnh)",
    "loai_tai_lieu": "huong_dan_hanh_chinh",
    "category": "huong_dan_benh_nhan",
    "raw_file": "raw/Hướng dẫn liên hệ đặt lịch khám.pdf",
    "structured_files": [],
    "markdown_chunk_dir": "markdown_chunks/huong_dan",
    "chunk_count": len(huongdan_idx),
})

# 2b) YouMed overview article (third-party source, no raw PDF — URL is the source)
youmed_idx = load_index("youmed_gioi_thieu")
for item in youmed_idx:
    chunk = base_chunk(item, "youmed_gioi_thieu")
    chunk["extra"] = {}
    all_chunks.append(chunk)
documents.append({
    "source_id": "youmed_gioi_thieu",
    "title": "Hướng dẫn chi tiết khám bệnh tại Bệnh viện Tim Hà Nội (YouMed)",
    "loai_tai_lieu": "bai_viet_gioi_thieu",
    "category": "gioi_thieu_benh_vien",
    "source_doc": "youmed.vn",
    "nguon_ben_thu_ba": True,
    "raw_file": None,
    "nguon": "https://youmed.vn/tin-tuc/benh-vien-tim-ha-noi/",
    "tac_gia": "YouMed",
    "ngay_dang": "2026-04-17",
    "ngay_cap_nhat": "2026-06-10",
    "structured_files": [],
    "markdown_chunk_dir": "markdown_chunks/youmed_gioi_thieu",
    "chunk_count": len(youmed_idx),
})

# 2c) Simple narrative doc groups (department pages, hospital history, third-party
# overview, corporate health-check service) — each folder is a flat list of markdown
# files indexed via _index.json, no per-row structured data.
simple_doc_groups = [
    {
        "source_id": "quy_trinh",
        "title": "Quy trình đón tiếp bệnh nhân và khám chữa bệnh ngoại trú tại khu Tự nguyện 1 - Cơ sở 1",
        "loai_tai_lieu": "quy_trinh_sop",
        "category": "quy_trinh_noi_bo",
        "raw_files": [
            "raw/QUY TRÌNH ĐÓN TIẾP BỆNH NHÂN VÀ KHÁM CHỮA BỆNH NGOẠI TRÚ TẠI KHU TỰ NGUYỆN 1 CS1.pdf",
        ],
        "nguon": "không rõ URL gốc (tài liệu nội bộ do người dùng cung cấp)",
        "dir": "quy_trinh",
        "ma_so": "QT.25.01",
        "ngay_ban_hanh": "2024-12-05",
        "lan_ban_hanh": 7,
    },
    {
        "source_id": "khoa_phong",
        "title": "Giới thiệu các khoa/phòng và sơ đồ tổ chức",
        "loai_tai_lieu": "gioi_thieu_khoa_phong",
        "category": "to_chuc_khoa_phong",
        "raw_files": [
            "raw/Khoa dược và hiệu thuốc.pdf",
            "raw/Khoa_Kham_benh_tu_nguyen.pdf",
            "raw/nv_sodo_Ck.pdf",
            "raw/sodo.jpg",
        ],
        "nguon": "benhvientimhanoi.vn (URL cụ thể chưa xác định)",
        "dir": "khoa_phong",
    },
    {
        "source_id": "lich_su_phat_trien",
        "title": "Quá trình phát triển Bệnh viện Tim Hà Nội",
        "loai_tai_lieu": "gioi_thieu_lich_su",
        "category": "gioi_thieu_benh_vien",
        "raw_files": ["raw/Qua_trinh_phat_trien_bv.pdf"],
        "nguon": "benhvientimhanoi.vn (URL cụ thể chưa xác định)",
        "dir": "lich_su_phat_trien",
    },
    {
        "source_id": "bookingcare_gioi_thieu",
        "title": "Bệnh viện Tim Hà Nội — tổng quan và 5 mũi nhọn (BookingCare)",
        "loai_tai_lieu": "bai_viet_gioi_thieu",
        "category": "gioi_thieu_benh_vien",
        "nguon_ben_thu_ba": True,
        "raw_files": ["raw/Bệnh viện Tim Hà Nội.pdf", "raw/5 mũi nhọn của Bệnh viện Tim Hà Nội.pdf"],
        "nguon": "bookingcare.vn (URL cụ thể chưa xác định)",
        "dir": "bookingcare_gioi_thieu",
    },
    {
        "source_id": "dich_vu",
        "title": "Giới thiệu dịch vụ (khám sức khỏe cơ quan - doanh nghiệp)",
        "loai_tai_lieu": "gioi_thieu_dich_vu",
        "category": "dich_vu_y_te",
        "raw_files": ["raw/Khám sức khỏe cá nhân và tổ chức.pdf"],
        "nguon": "benhvientimhanoi.vn (URL cụ thể chưa xác định)",
        "dir": "dich_vu",
    },
]

for sd in simple_doc_groups:
    idx = load_index(sd["dir"])
    for item in idx:
        chunk = base_chunk(item, sd["source_id"])
        chunk["extra"] = {}
        all_chunks.append(chunk)
    doc_entry = {
        "source_id": sd["source_id"],
        "title": sd["title"],
        "loai_tai_lieu": sd["loai_tai_lieu"],
        "category": sd["category"],
        "raw_file": sd["raw_files"][0] if len(sd["raw_files"]) == 1 else None,
        "raw_files": sd["raw_files"] if len(sd["raw_files"]) > 1 else None,
        "nguon": sd["nguon"],
        "structured_files": [],
        "markdown_chunk_dir": f"markdown_chunks/{sd['dir']}",
        "chunk_count": len(idx),
    }
    if sd.get("nguon_ben_thu_ba"):
        doc_entry["nguon_ben_thu_ba"] = True
    for k in ("ma_so", "ngay_ban_hanh", "lan_ban_hanh"):
        if k in sd:
            doc_entry[k] = sd[k]
    documents.append(doc_entry)

# 3) Price-list documents
price_docs = [
    {
        "source_id": "bhyt_2023",
        "title": "Bảng giá Bảo hiểm y tế - Bệnh viện Tim Hà Nội",
        "raw_file": "raw/banggiaBHYT.pdf",
        "structured_files": ["structured/bang_gia_BHYT_full.csv", "structured/bang_gia_BHYT_full.xlsx"],
        "dir": "bhyt_2023",
        "co_so_phap_ly": "Thông tư 22/2023/TT-BYT",
    },
    {
        "source_id": "dvkt_2025",
        "title": "Giá dịch vụ kỹ thuật áp dụng tại Bệnh viện Tim Hà Nội 2025",
        "raw_file": "raw/gia_dv_ky_thuat_2025.pdf",
        "structured_files": ["structured/gia_dv_ky_thuat_2025_full.csv", "structured/gia_dv_ky_thuat_2025_full.xlsx"],
        "dir": "dvkt_2025",
        "co_so_phap_ly": "Phụ lục số 06 Nghị quyết số 45/2024/NQ-HĐND ngày 10/12/2024 của HĐND TP Hà Nội",
    },
    {
        "source_id": "dvkt_thuong",
        "title": "Bảng giá Dịch vụ kỹ thuật - Bệnh viện Tim Hà Nội",
        "raw_file": "raw/banggiaDVKT.pdf",
        "structured_files": ["structured/banggiaDVKT_full.csv", "structured/banggiaDVKT_full.xlsx"],
        "dir": "dvkt_thuong",
        "co_so_phap_ly": "Thông tư 14/2019/TT-BYT",
    },
    {
        "source_id": "dvkt_yeu_cau",
        "title": "Bảng giá Dịch vụ kỹ thuật theo yêu cầu - Bệnh viện Tim Hà Nội",
        "raw_file": "raw/banggiaDVKTYC.pdf",
        "structured_files": ["structured/banggiaDVKTYC_full.csv", "structured/banggiaDVKTYC_full.xlsx"],
        "dir": "dvkt_yeu_cau",
        "co_so_phap_ly": "Quyết định 2823/QĐ-BVT; Quyết định 3165/QĐ-BVT",
    },
]

for pd_ in price_docs:
    idx = load_index(pd_["dir"])
    for item in idx:
        chunk = base_chunk(item, pd_["source_id"])
        chunk["extra"] = {"danh_muc": item["danh_muc"], "nhom_con": item.get("nhom_con", ""),
                           "stt_tu": item["stt_tu"], "stt_den": item["stt_den"], "so_dong": int(item["so_dong"])}
        all_chunks.append(chunk)
    documents.append({
        "source_id": pd_["source_id"],
        "title": pd_["title"],
        "loai_tai_lieu": "bang_gia_dich_vu",
        "category": "bao_hiem_y_te" if pd_["source_id"] == "bhyt_2023" else "gia_dich_vu",
        "raw_file": pd_["raw_file"],
        "structured_files": pd_["structured_files"],
        "markdown_chunk_dir": f"markdown_chunks/{pd_['dir']}",
        "chunk_count": len(idx),
        "row_count": sum(int(x["so_dong"]) for x in idx),
        "co_so_phap_ly": pd_["co_so_phap_ly"],
    })

manifest = {
    "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "benh_vien": "Bệnh viện Tim Hà Nội",
    "so_luong_tai_lieu": len(documents),
    "so_luong_chunk": len(all_chunks),
    "documents": documents,
    "chunks": all_chunks,
}

out_path = os.path.join(BASE, "manifest.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

print("documents:", len(documents))
print("total chunks:", len(all_chunks))
child_count = sum(1 for c in all_chunks if c.get("parent_id"))
print("chunks with parent_id:", child_count)
for d in documents:
    print(" -", d["source_id"], "|", d.get("chunk_count"), "chunks", "|", d.get("row_count", ""))
