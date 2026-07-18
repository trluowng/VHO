# -*- coding: utf-8 -*-
"""Consolidate the full front-matter schema of every chunk in a markdown_chunks
folder into a single merge.json array, one object per chunk: every front-matter
field except a fixed exclusion list (link/path fields luu_y/nguon/path/
file_goc, third-party/press-source fields tac_gia/ngay_dang/ngay_cap_nhat/
nguon_ben_thu_ba, and source_doc), plus chars, title (the big/root section's
own title: tieu_de, or tieu_de_dieu for luat_kbcb), and context (the chunk's
own markdown body content, i.e. everything after the front matter)."""
import re
import os
import sys
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.dirname(SCRIPT_DIR)  # scripts/ -> data/
CHUNKS_DIR = os.path.join(DATA_DIR, "markdown_chunks")

EXCLUDED_FIELDS = (
    "luu_y", "nguon", "path", "file_goc",
    "tac_gia", "ngay_dang", "ngay_cap_nhat", "nguon_ben_thu_ba",
    "source_doc",
)

def unquote(v):
    v = v.strip()
    if v.startswith('"') and v.endswith('"'):
        return v[1:-1].replace('\\"', '"')
    return v

def parse_front_matter(text):
    m = re.match(r"^---\n(.*?)\n---\n\n(.*)$", text, re.DOTALL)
    fm_text, body = m.group(1), m.group(2)
    fm = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = unquote(v)
    return fm, body

def build(folder_name):
    folder = os.path.join(CHUNKS_DIR, folder_name)
    merged = []
    for fname in sorted(f for f in os.listdir(folder) if f.endswith(".md")):
        path = os.path.join(folder, fname)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        fm, body = parse_front_matter(text)
        title = fm.get("tieu_de", fm.get("tieu_de_dieu", ""))
        entry = {k: v for k, v in fm.items() if k not in EXCLUDED_FIELDS}
        entry["chars"] = len(text)
        entry["title"] = title
        entry["context"] = body.strip()
        merged.append(entry)
    out_path = os.path.join(folder, "merge.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"{folder_name}: {len(merged)} chunks -> {out_path}")

if __name__ == "__main__":
    folder_name = sys.argv[1] if len(sys.argv) > 1 else "luat_kbcb"
    build(folder_name)
