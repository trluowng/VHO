# -*- coding: utf-8 -*-
"""Re-split luat_kbcb/dieu_NNN.md files structurally into a khoản-parent /
điểm-child hierarchy:
  - each khoản (1., 2., 3...) that has lettered sub-points (a), b), c)...) becomes
    a PARENT chunk containing only its lead-in text (before the first "a)"), plus
    one CHILD chunk per lettered point (parent_id links back to the parent's chunk_id);
  - a khoản with no lettered points becomes a single standalone chunk;
  - an Điều with no khoản at all (rare) stays a single standalone chunk.
Adds the standardized cross-corpus metadata fields, kept as 3 distinct ID concepts:
  - doc_id: constant for the whole source document (luat_kbcb_2023 for every chunk)
  - chunk_id: unique per chunk (content-addressed, not sequence-based)
  - parent_id: chunk_id of this chunk's parent in the hierarchy, or "" if none
plus source_doc, section, category, effective_date, approved_by (alongside the
existing luật-specific fields chuong/muc/dieu/tieu_de_dieu/so_hieu/...)."""
import re
import os
import glob
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.dirname(SCRIPT_DIR)  # scripts/ -> data/
FOLDER = os.path.join(DATA_DIR, "markdown_chunks", "luat_kbcb")

DOC_ID = "luat_kbcb_2023"  # constant across every chunk of this source document
SOURCE_DOC = "Luật Khám bệnh, chữa bệnh số 15/2023/QH15"
CATEGORY = "van_ban_phap_ly"

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
    fm = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = unquote(v)
    return fm, body

def split_body_into_clauses(body_lines):
    """Split body lines into: preamble (before any numbered clause), then list of
    clauses where each clause is (number, [lines])."""
    preamble = []
    clauses = []
    cur_num = None
    cur_lines = []
    for line in body_lines:
        m = clause_re.match(line)
        if m:
            if cur_num is not None:
                clauses.append((cur_num, cur_lines))
            cur_num = m.group(1)
            cur_lines = [line]
        elif cur_num is not None:
            cur_lines.append(line)
        else:
            preamble.append(line)
    if cur_num is not None:
        clauses.append((cur_num, cur_lines))
    return preamble, clauses

def split_clause_into_intro_and_points(clines):
    """Returns (intro_lines, [(letter, lines), ...]) — points is empty if the
    khoản has no lettered sub-points."""
    intro = []
    points = []
    cur_letter = None
    cur_lines = []
    for line in clines:
        m = point_re.match(line)
        if m:
            if cur_letter is not None:
                points.append((cur_letter, cur_lines))
            elif cur_lines:
                intro = cur_lines
            cur_letter = m.group(1)
            cur_lines = [line]
        elif cur_letter is not None:
            cur_lines.append(line)
        else:
            intro.append(line)
    if cur_letter is not None:
        points.append((cur_letter, cur_lines))
    return intro, points

def write_chunk(path, fm, body_lines):
    yaml_lines = ["---"]
    for k, v in fm.items():
        yaml_lines.append(f"{k}: {quote_if_needed(v)}")
    yaml_lines.append("---")
    content = "\n".join(yaml_lines) + "\n\n" + "\n".join(body_lines).rstrip() + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

results = []  # list of output paths, in write order
files = sorted(glob.glob(os.path.join(FOLDER, "dieu_*.md")))
for path in files:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    fm, body = parse_front_matter(text)
    lines = body.split("\n")

    header_line = lines[0]
    idx = 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    chuong_line = None
    if idx < len(lines) and lines[idx].startswith("*"):
        chuong_line = lines[idx]
        idx += 1
        while idx < len(lines) and not lines[idx].strip():
            idx += 1
    content_lines = lines[idx:]

    dieu_num = fm["dieu"]
    tieu_de = unquote(fm["tieu_de_dieu"])
    base = os.path.splitext(os.path.basename(path))[0]  # dieu_NNN
    base_id = f"luat_kbcb_{base}"

    common_fm_extra = {
        "source_doc": SOURCE_DOC,
        "category": CATEGORY,
        "effective_date": fm.get("ngay_hieu_luc", ""),
        "approved_by": fm.get("co_quan_ban_hanh", ""),
    }

    def make_fm(chunk_id, section, parent_id=""):
        # doc_id = whole source document (constant); chunk_id = this specific chunk
        # (unique, content-addressed); parent_id = chunk_id of the parent chunk in the
        # khoản/điểm hierarchy, if any. Kept as 3 distinct fields, not merged.
        out = {"doc_id": DOC_ID, "chunk_id": chunk_id, "parent_id": parent_id}
        out.update(common_fm_extra)
        out["section"] = section
        for k, v in fm.items():
            if k == "doc_id":
                continue
            out[k] = v
        return out

    def heading(section_suffix):
        return f"# Điều {dieu_num}. {tieu_de}" + (f" — {section_suffix}" if section_suffix else "")

    preamble, clauses = split_body_into_clauses(content_lines)
    os.remove(path)

    if not clauses:
        # no numbered clauses at all -- single standalone chunk
        section = f"Điều {dieu_num}"
        new_fm = make_fm(base_id, section)
        body_out = [heading(""), ""]
        if chuong_line:
            body_out += [chuong_line, ""]
        body_out += content_lines
        out_path = os.path.join(FOLDER, base + ".md")
        write_chunk(out_path, new_fm, body_out)
        results.append(out_path)
        continue

    first_chunk = True
    for num, clines in clauses:
        intro, points = split_clause_into_intro_and_points(clines)

        if not points:
            # whole khoản is one standalone chunk (no children)
            section = f"Điều {dieu_num} - Khoản {num}"
            chunk_id = f"{base_id}_k{num}"
            new_fm = make_fm(chunk_id, section)
            body_out = [heading(f"Khoản {num}"), ""]
            if chuong_line and first_chunk:
                body_out += [chuong_line, ""]
            if first_chunk and preamble and any(l.strip() for l in preamble):
                body_out += preamble
            body_out += clines
            out_path = os.path.join(FOLDER, f"{base}_k{num}.md")
            write_chunk(out_path, new_fm, body_out)
            results.append(out_path)
        else:
            # parent chunk: lead-in text only
            parent_section = f"Điều {dieu_num} - Khoản {num}"
            parent_id = f"{base_id}_k{num}"
            parent_fm = make_fm(parent_id, parent_section)
            parent_body = [heading(f"Khoản {num}"), ""]
            if chuong_line and first_chunk:
                parent_body += [chuong_line, ""]
            if first_chunk and preamble and any(l.strip() for l in preamble):
                parent_body += preamble
            parent_body += intro if intro else [f"{num}. (xem các điểm con)"]
            parent_path = os.path.join(FOLDER, f"{base}_k{num}.md")
            write_chunk(parent_path, parent_fm, parent_body)
            results.append(parent_path)

            for letter, plines in points:
                child_section = f"Điều {dieu_num} - Khoản {num} - Điểm {letter})"
                child_id = f"{base_id}_k{num}{letter}"
                child_fm = make_fm(child_id, child_section, parent_id=parent_id)
                child_body = [heading(f"Khoản {num}, điểm {letter})"), ""]
                child_body += plines
                child_path = os.path.join(FOLDER, f"{base}_k{num}{letter}.md")
                write_chunk(child_path, child_fm, child_body)
                results.append(child_path)

        first_chunk = False

print("files processed:", len(files))
print("total output chunks:", len(results))

# rebuild _index.json
index = []
for path in sorted(results):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    fm, _ = parse_front_matter(text)
    index.append({
        "doc_id": fm["doc_id"],
        "chunk_id": fm["chunk_id"],
        "parent_id": fm.get("parent_id", ""),
        "path": f"markdown_chunks/luat_kbcb/{os.path.basename(path)}",
        "dieu": int(fm["dieu"]),
        "section": fm["section"],
        "source_doc": fm.get("source_doc", ""),
        "category": fm.get("category", ""),
        "effective_date": fm.get("effective_date", ""),
        "approved_by": fm.get("approved_by", ""),
        "tieu_de": unquote(fm["tieu_de_dieu"]),
        "chuong": unquote(fm.get("chuong", "")),
        "muc": unquote(fm.get("muc", "")),
        "chars": len(text),
    })

with open(os.path.join(FOLDER, "_index.json"), "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

print("final chunk count:", len(index))
sizes = [x["chars"] for x in index]
print("max chars:", max(sizes), "| min chars:", min(sizes), "| avg:", round(sum(sizes)/len(sizes)))
child_count = sum(1 for x in index if x["parent_id"])
print("child chunks (with parent_id):", child_count)
