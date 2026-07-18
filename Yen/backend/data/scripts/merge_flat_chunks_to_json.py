# -*- coding: utf-8 -*-
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.dirname(SCRIPT_DIR)
FLAT_DIR = os.path.join(DATA_DIR, "markdown_chunks_flat")


def parse_chunk_file(path):
    item = {}
    with open(path, encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f]
    if not lines:
        return None
    first = lines[0].strip()
    if first.startswith("Document ID:"):
        item["doc_id"] = first.split(":", 1)[1].strip()
    else:
        item["doc_id"] = os.path.splitext(os.path.basename(path))[0]
    fields = {}
    for line in lines[1:]:
        if not line.strip():
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        fields[key] = value
    item["fields"] = fields
    return item


def merge_folder(folder_path):
    entries = []
    for fname in sorted(os.listdir(folder_path)):
        if not fname.lower().endswith(".md"):
            continue
        if fname.startswith("_"):
            continue
        file_path = os.path.join(folder_path, fname)
        entry = parse_chunk_file(file_path)
        if entry is not None:
            entries.append(entry)
    return entries


def main():
    if not os.path.isdir(FLAT_DIR):
        raise FileNotFoundError(f"Flat output directory not found: {FLAT_DIR}")

    for name in sorted(os.listdir(FLAT_DIR)):
        folder_path = os.path.join(FLAT_DIR, name)
        if not os.path.isdir(folder_path):
            continue
        merged = merge_folder(folder_path)
        out_path = os.path.join(folder_path, "merged.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"source_id": name, "documents": merged}, f, ensure_ascii=False, indent=2)
        print(f"Wrote {len(merged)} documents to {out_path}")

    print("Done.")


if __name__ == "__main__":
    main()
