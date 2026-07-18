# -*- coding: utf-8 -*-
"""Recursively split each markdown file in the 7 narrative folders (khoa_phong,
lich_su_phat_trien, huong_dan, dich_vu, bookingcare_gioi_thieu, quy_trinh,
youmed_gioi_thieu) by structural priority: "##" section > "###" subsection >
numbered clause (1., 2., 3...) > lettered point (a), b), c)...). Headings are the
outer document skeleton and must be peeled off before recursing inward, otherwise
a "###" appearing deep inside a later "##" section would wrongly compete with (and
pre-empt) the top-level "##" split. Once recursion has descended past all headings
into actual prose, clause and then point apply as the finest-grained leaf-level
split. At every level, if a pattern yields 2+ matches, the node becomes a PARENT
chunk (its own lead-in content only, no duplication) plus one CHILD chunk per
match (parent_id pointing back) — and each child is recursively re-checked the
same way. A node with no matching pattern anywhere is a single leaf chunk.

Every chunk gets doc_id (constant per folder), chunk_id (unique, structure-derived),
parent_id (chunk_id of its parent, or "" at the root), source_doc, section, category,
effective_date, approved_by.

Safe to run only on a "flat" baseline (one file per topic, no prior *_s1/*_x1/*_c1/
*_a suffixed split files) — running it twice without first reconstructing back to
the flat baseline will re-split the already-split parent files."""
import re
import os
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.dirname(SCRIPT_DIR)  # scripts/ -> data/
CHUNKS_DIR = os.path.join(DATA_DIR, "markdown_chunks")

FOLDERS = ["khoa_phong", "lich_su_phat_trien", "huong_dan", "dich_vu",
           "bookingcare_gioi_thieu", "quy_trinh", "youmed_gioi_thieu"]

FOLDER_META = {
    "khoa_phong": {"doc_id": "khoa_phong", "source_doc": "benhvientimhanoi.vn",
                   "category": "to_chuc_khoa_phong", "approved_by": ""},
    "lich_su_phat_trien": {"doc_id": "lich_su_phat_trien", "source_doc": "benhvientimhanoi.vn",
                            "category": "gioi_thieu_benh_vien", "approved_by": ""},
    "huong_dan": {"doc_id": "huong_dan", "source_doc": None,
                  "category": "huong_dan_benh_nhan", "approved_by": ""},
    "dich_vu": {"doc_id": "dich_vu", "source_doc": "benhvientimhanoi.vn",
                "category": "dich_vu_y_te", "approved_by": ""},
    "bookingcare_gioi_thieu": {"doc_id": "bookingcare_gioi_thieu", "source_doc": "bookingcare.vn",
                               "category": "gioi_thieu_benh_vien", "approved_by": ""},
    "quy_trinh": {"doc_id": "quy_trinh", "source_doc": "Quy trình QT.25.01 - Bệnh viện Tim Hà Nội",
                  "category": "quy_trinh_noi_bo", "approved_by": None},
    "youmed_gioi_thieu": {"doc_id": "youmed_gioi_thieu", "source_doc": "youmed.vn",
                          "category": "gioi_thieu_benh_vien", "approved_by": ""},
}

h2_re = re.compile(r"^## (?!#)(.+)$")
h3_re = re.compile(r"^### (?!#)(.+)$")
clause_re = re.compile(r"^(\d+)\.\s")
point_re = re.compile(r"^([a-zđ])\)\s", re.IGNORECASE)

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
    fm, order = {}, []
    for line in fm_text.split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip()
            fm[k] = unquote(v)
            order.append(k)
    return fm, order, body

def derive_effective_date(fm):
    for k in ("ngay_hieu_luc", "ngay_ban_hanh", "ngay_cap_nhat", "ngay_dang"):
        if fm.get(k):
            return fm[k]
    return ""

def try_split(lines, regex):
    """Generic splitter for a start-of-line regex. Returns (intro, [(label, lines)]) or
    None if fewer than 2 matches."""
    intro = []
    items = []
    cur_label = None
    cur_lines = []
    for line in lines:
        m = regex.match(line)
        if m:
            if cur_label is not None:
                items.append((cur_label, cur_lines))
            elif cur_lines and any(l.strip() for l in cur_lines):
                intro = cur_lines
            cur_label = m.group(1)
            cur_lines = [line]
        elif cur_label is not None:
            cur_lines.append(line)
        else:
            intro.append(line)
    if cur_label is not None:
        items.append((cur_label, cur_lines))
    if len(items) < 2:
        return None
    return intro, items

def try_split_heading(lines, marker_re):
    intro = []
    items = []
    cur_label = None
    cur_lines = []
    for line in lines:
        m = marker_re.match(line)
        if m:
            if cur_label is not None:
                items.append((cur_label, cur_lines))
            elif cur_lines and any(l.strip() for l in cur_lines):
                intro = cur_lines
            cur_label = m.group(1).strip()
            cur_lines = []
        elif cur_label is not None:
            cur_lines.append(line)
        else:
            intro.append(line)
    if cur_label is not None:
        items.append((cur_label, cur_lines))
    if len(items) < 2:
        return None
    return intro, items

def pick_split(lines):
    r = try_split_heading(lines, h2_re)
    if r:
        return ("h2", r[0], r[1])
    r = try_split_heading(lines, h3_re)
    if r:
        return ("h3", r[0], r[1])
    r = try_split(lines, clause_re)
    if r:
        return ("clause", r[0], r[1])
    r = try_split(lines, point_re)
    if r:
        return ("point", r[0], r[1])
    return None

def child_suffix(kind, label, index):
    if kind == "point":
        return label.lower()
    if kind == "clause":
        return f"c{label}"
    if kind == "h3":
        return f"x{index}"
    if kind == "h2":
        return f"s{index}"

def child_section_text(kind, label):
    if kind == "point":
        return f"Điểm {label})"
    if kind == "clause":
        return f"Mục {label}."
    return label  # h2/h3: heading text itself

def emit(path, fm, body_lines):
    yaml_lines = ["---"]
    for k, v in fm.items():
        yaml_lines.append(f"{k}: {quote_if_needed(v)}")
    yaml_lines.append("---")
    content = "\n".join(yaml_lines) + "\n\n" + "\n".join(body_lines).rstrip() + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def process_node(lines, chunk_id, section_path, parent_id, folder, base_fm, title, out_prefix):
    split = pick_split(lines)
    if split is None:
        fm = dict(base_fm)
        fm["chunk_id"] = chunk_id
        fm["parent_id"] = parent_id
        fm["section"] = " — ".join(section_path)
        body = [f"# {title}", ""] + lines
        emit(os.path.join(folder, f"{out_prefix}.md"), fm, body)
        return

    kind, intro, items = split
    fm = dict(base_fm)
    fm["chunk_id"] = chunk_id
    fm["parent_id"] = parent_id
    fm["section"] = " — ".join(section_path)
    parent_body = [f"# {title}", ""]
    parent_body += intro if (intro and any(l.strip() for l in intro)) else []
    emit(os.path.join(folder, f"{out_prefix}.md"), fm, parent_body)

    for i, (label, item_lines) in enumerate(items, start=1):
        suffix = child_suffix(kind, label, i)
        child_id = f"{chunk_id}_{suffix}"
        child_section_path = section_path + [child_section_text(kind, label)]
        child_title = title if kind in ("point", "clause") else f"{title} — {label}"
        process_node(item_lines, child_id, child_section_path, chunk_id, folder,
                     base_fm, child_title, f"{out_prefix}_{suffix}")

def main():
    for folder_name in FOLDERS:
        folder = os.path.join(CHUNKS_DIR, folder_name)
        meta = FOLDER_META[folder_name]
        files = sorted(f for f in os.listdir(folder) if f.endswith(".md"))
        for fname in files:
            path = os.path.join(folder, fname)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            fm, order, body = parse_front_matter(text)
            lines = body.split("\n")

            title = fm.get("tieu_de", fm.get("section", ""))
            idx = 1
            while idx < len(lines) and not lines[idx].strip():
                idx += 1
            content_lines = lines[idx:]

            root_chunk_id = fm.get("chunk_id", os.path.splitext(fname)[0])

            base_fm = {
                "doc_id": meta["doc_id"],
                "chunk_id": "",
                "parent_id": "",
                "source_doc": meta["source_doc"] if meta["source_doc"] is not None else fm.get("nguon", ""),
                "category": meta["category"],
                "effective_date": derive_effective_date(fm),
                "approved_by": meta["approved_by"] if meta["approved_by"] is not None else fm.get("nguoi_phe_duyet", ""),
                "section": "",
            }
            for k in order:
                if k in ("doc_id", "chunk_id", "parent_id", "source_doc", "category",
                         "effective_date", "approved_by", "section"):
                    continue
                base_fm[k] = fm[k]

            os.remove(path)
            out_prefix = os.path.splitext(fname)[0]
            process_node(content_lines, root_chunk_id, [title], "", folder, base_fm,
                         title, out_prefix)

        # rebuild _index.json
        index = []
        for fname in sorted(f for f in os.listdir(folder) if f.endswith(".md")):
            path = os.path.join(folder, fname)
            with open(path, encoding="utf-8") as f:
                t = f.read()
            fm2, _, _ = parse_front_matter(t)
            index.append({
                "doc_id": fm2.get("doc_id", ""),
                "chunk_id": fm2.get("chunk_id", ""),
                "parent_id": fm2.get("parent_id", ""),
                "path": f"markdown_chunks/{folder_name}/{fname}",
                "section": fm2.get("section", ""),
                "source_doc": fm2.get("source_doc", ""),
                "category": fm2.get("category", ""),
                "effective_date": fm2.get("effective_date", ""),
                "approved_by": fm2.get("approved_by", ""),
                "chars": len(t),
            })
        with open(os.path.join(folder, "_index.json"), "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        child_count = sum(1 for x in index if x["parent_id"])
        print(f"{folder_name}: {len(index)} chunks ({child_count} with parent_id)")

if __name__ == "__main__":
    main()
