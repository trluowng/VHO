# -*- coding: utf-8 -*-
"""Consolidate every merge.json (from the 8 narrative/legal folders) plus the
existing services_merged.json price-table rows into a single unified
markdown_chunks/services_merged.json — one {document_count, sources, documents}
structure covering the whole corpus. Each narrative/legal entry gets a
"source_id" field (= its folder name) added, matching the price-table rows'
existing source_id grouping key; all of that entry's original fields
(doc_id/chunk_id/parent_id/title/context/...) are kept as-is."""
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.dirname(SCRIPT_DIR)  # scripts/ -> data/
CHUNKS_DIR = os.path.join(DATA_DIR, "markdown_chunks")
SERVICES_PATH = os.path.join(CHUNKS_DIR, "services_merged.json")

NARRATIVE_FOLDERS = [
    "luat_kbcb", "quy_trinh", "youmed_gioi_thieu", "lich_su_phat_trien",
    "khoa_phong", "huong_dan", "dich_vu", "bookingcare_gioi_thieu",
]


def main():
    with open(SERVICES_PATH, encoding="utf-8") as f:
        merged = json.load(f)

    for folder in NARRATIVE_FOLDERS:
        path = os.path.join(CHUNKS_DIR, folder, "merge.json")
        with open(path, encoding="utf-8") as f:
            entries = json.load(f)
        for e in entries:
            entry = dict(e)
            entry["source_id"] = folder
            merged["documents"].append(entry)
        merged["sources"][folder] = len(entries)
        print(f"{folder}: +{len(entries)} entries")

    merged["document_count"] = len(merged["documents"])

    with open(SERVICES_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"\nTotal document_count: {merged['document_count']}")
    print("sources:", merged["sources"])


if __name__ == "__main__":
    main()
