# -*- coding: utf-8 -*-
import csv
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.dirname(SCRIPT_DIR)
STRUCTURED_DIR = os.path.join(DATA_DIR, "structured")
OUTPUT_CHUNKS_DIR = os.path.join(DATA_DIR, "markdown_chunks_flat")

PRICE_FIELDS = [
    ("Danh_muc", "Danh mục", False),
    ("Nhom_con", "Nhóm con", False),
    ("STT", "STT", False),
    ("Ma_tuong_duong", "Mã tương đương", False),
    ("Dich_vu_ky_thuat", "Dịch vụ kỹ thuật", False),
    ("Gia_BHYT", "Giá BHYT chi trả tối đa (VNĐ)", True),
    ("Gia_Co_so_1", "Giá Cơ sở 1 (VNĐ)", True),
    ("Gia_Co_so_2", "Giá Cơ sở 2 (VNĐ)", True),
    ("Gia_dich_vu", "Giá dịch vụ (VNĐ)", True),
    ("Gia_kham_benh", "Giá khám bệnh (VNĐ)", True),
    ("Gia_dich_vu_theo_yeu_cau", "Giá dịch vụ theo yêu cầu (VNĐ)", True),
    ("Ghi_chu", "Ghi chú", False),
]

DATASETS = [
    {
        "source_id": "bhyt_2023",
        "csv_file": "bang_gia_BHYT_full.csv",
        "prefix": "bhyt",
    },
    {
        "source_id": "dvkt_2025",
        "csv_file": "gia_dv_ky_thuat_2025_full.csv",
        "prefix": "dvkt2025",
    },
    {
        "source_id": "dvkt_thuong",
        "csv_file": "banggiaDVKT_full.csv",
        "prefix": "dvkt",
    },
    {
        "source_id": "dvkt_yeu_cau",
        "csv_file": "banggiaDVKTYC_full.csv",
        "prefix": "dvktyc",
    },
]


def fmt_price(v):
    v = (v or "").strip()
    if not v:
        return ""
    try:
        return f"{int(v):,}".replace(",", ".")
    except ValueError:
        return v


def esc(v):
    return (v or "").strip().replace("\n", " ").replace("\r", " ")


def write_row_chunk(out_dir, doc_id, row, field_defs):
    os.makedirs(out_dir, exist_ok=True)
    fname = f"{doc_id}.md"
    path = os.path.join(out_dir, fname)
    lines = [f"Document ID: {doc_id}", ""]
    for field_name, label, is_price in field_defs:
        if field_name not in row:
            continue
        value = row.get(field_name, "")
        if not str(value).strip():
            continue
        rendered = fmt_price(value) if is_price else esc(value)
        lines.append(f"{label}: {rendered}")
    content = "\n".join(lines).rstrip() + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return fname, len(content)


def chunk_dataset(dataset, field_defs):
    csv_path = os.path.join(STRUCTURED_DIR, dataset["csv_file"])
    out_dir = os.path.join(OUTPUT_CHUNKS_DIR, dataset["source_id"])
    index = []

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row_idx, row in enumerate(reader, start=1):
            doc_id = f"{dataset['prefix']}_{row_idx:06d}"
            fname, clen = write_row_chunk(out_dir, doc_id, row, field_defs)
            index.append({
                "doc_id": doc_id,
                "path": os.path.join("markdown_chunks_flat", dataset["source_id"], fname).replace("\\", "/"),
                "source_id": dataset["source_id"],
                "row_index": row_idx,
                "chars": clen,
            })

    index_path = os.path.join(out_dir, "_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"{dataset['source_id']}: wrote {len(index)} chunk files to {out_dir}")
    return index


if __name__ == "__main__":
    all_index = {}
    for dataset in DATASETS:
        all_index[dataset["source_id"]] = chunk_dataset(dataset, PRICE_FIELDS)

    manifest_path = os.path.join(OUTPUT_CHUNKS_DIR, "_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"datasets": {k: len(v) for k, v in all_index.items()}}, f, ensure_ascii=False, indent=2)
    print(f"Manifest saved to {manifest_path}")
