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

documents = []
all_chunks = []

# 1) Luat KBCB
luat_idx = load_index("luat_kbcb")
for item in luat_idx:
    all_chunks.append({
        "doc_source": "luat_kbcb_2023",
        "chunk_id": item["doc_id"],
        "path": item["path"],
        "chars": item["chars"],
        "extra": {"dieu": item["dieu"], "tieu_de": item["tieu_de"], "chuong": item["chuong"], "muc": item["muc"]},
    })
documents.append({
    "source_id": "luat_kbcb_2023",
    "title": "Luật Khám bệnh, chữa bệnh số 15/2023/QH15",
    "loai_tai_lieu": "van_ban_phap_ly",
    "raw_file": "raw/15_2023_QH15_372143.pdf",
    "structured_files": [],
    "markdown_chunk_dir": "markdown_chunks/luat_kbcb",
    "chunk_count": len(luat_idx),
    "so_hieu": "15/2023/QH15",
    "ngay_ban_hanh": "2023-01-09",
    "ngay_hieu_luc": "2024-01-01",
    "nguon": "https://thuvienphapluat.vn/van-ban/The-thao-Y-te/Luat-15-2023-QH15-kham-benh-chua-benh-372143.aspx",
})

# 2) Huong dan (mixed: PDF-sourced booking guide + YouMed-sourced cost guide)
huongdan_idx = load_index("huong_dan")
for item in huongdan_idx:
    all_chunks.append({
        "doc_source": "huong_dan",
        "chunk_id": item["doc_id"],
        "path": item["path"],
        "chars": item["chars"],
        "extra": {"muc": item["muc"]},
    })
documents.append({
    "source_id": "huong_dan",
    "title": "Hướng dẫn cho người bệnh (đặt lịch khám, chi phí khám chữa bệnh)",
    "loai_tai_lieu": "huong_dan_hanh_chinh",
    "raw_file": "raw/Hướng dẫn liên hệ đặt lịch khám.pdf",
    "structured_files": [],
    "markdown_chunk_dir": "markdown_chunks/huong_dan",
    "chunk_count": len(huongdan_idx),
})

# 2b) YouMed overview article (third-party source, no raw PDF — URL is the source)
youmed_idx = load_index("youmed_gioi_thieu")
for item in youmed_idx:
    all_chunks.append({
        "doc_source": "youmed_gioi_thieu",
        "chunk_id": item["doc_id"],
        "path": item["path"],
        "chars": item["chars"],
        "extra": {"muc": item["muc"]},
    })
documents.append({
    "source_id": "youmed_gioi_thieu",
    "title": "Hướng dẫn chi tiết khám bệnh tại Bệnh viện Tim Hà Nội (YouMed)",
    "loai_tai_lieu": "bai_viet_gioi_thieu",
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
        all_chunks.append({
            "doc_source": pd_["source_id"],
            "chunk_id": item["doc_id"],
            "path": item["path"],
            "chars": item["chars"],
            "extra": {"danh_muc": item["danh_muc"], "nhom_con": item.get("nhom_con", ""),
                      "stt_tu": item["stt_tu"], "stt_den": item["stt_den"], "so_dong": item["so_dong"]},
        })
    documents.append({
        "source_id": pd_["source_id"],
        "title": pd_["title"],
        "loai_tai_lieu": "bang_gia_dich_vu",
        "raw_file": pd_["raw_file"],
        "structured_files": pd_["structured_files"],
        "markdown_chunk_dir": f"markdown_chunks/{pd_['dir']}",
        "chunk_count": len(idx),
        "row_count": sum(x["so_dong"] for x in idx),
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
for d in documents:
    print(" -", d["source_id"], "|", d.get("chunk_count"), "chunks", "|", d.get("row_count", ""))
