# -*- coding: utf-8 -*-
"""Split luat_kbcb/dieu_NNN.md into one chunk per khoan (top-level numbered clause,
e.g. "1.", "2."...) so each chunk covers exactly one 'dau muc'. Articles with no
numbered clauses stay as a single whole-article chunk. Also emits a consolidated
structured/luat_kbcb_full.json with full content for easy programmatic retrieval."""
import re
import os
import glob
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.dirname(SCRIPT_DIR)  # scripts/ -> data/
FOLDER = os.path.join(DATA_DIR, "markdown_chunks", "luat_kbcb")
JSON_OUT = os.path.join(DATA_DIR, "structured", "luat_kbcb_full.json")

clause_re = re.compile(r"^(\d+)\.\s")

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

def split_body_into_clauses(body_lines):
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

json_records = []

files = sorted(glob.glob(os.path.join(FOLDER, "dieu_*.md")))
for path in files:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    fm, order, body = parse_front_matter(text)
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
    tieu_de = fm["tieu_de_dieu"]
    base_doc_id = fm["doc_id"]

    preamble, clauses = split_body_into_clauses(content_lines)

    if not clauses:
        # whole article is a single chunk already -- keep the file, just record for JSON
        json_records.append({
            **{k: fm[k] for k in order},
            "khoan": None,
            "noi_dung": "\n".join(content_lines).strip(),
        })
        continue

    # one khoan = one chunk; drop the original merged file, write per-khoan files
    os.remove(path)
    fname_base = os.path.splitext(os.path.basename(path))[0]  # dieu_NNN
    n_khoan = len(clauses)

    for i, (num, clines) in enumerate(clauses):
        khoan_fname = f"{fname_base}_k{num.zfill(2)}.md"
        khoan_path = os.path.join(FOLDER, khoan_fname)

        new_fm = dict(fm)
        new_fm["doc_id"] = f"{base_doc_id}_k{num.zfill(2)}"
        new_fm["khoan"] = num

        yaml_lines = ["---"]
        for k in order:
            if k == "doc_id":
                yaml_lines.append(f"doc_id: {new_fm['doc_id']}")
            else:
                yaml_lines.append(f"{k}: {quote_if_needed(new_fm[k])}")
        yaml_lines.append(f"khoan: {num}")
        yaml_lines.append("---")

        clause_text = "\n".join(clines).strip()
        body_out = [f"# Điều {dieu_num}. {tieu_de} — Khoản {num}", ""]
        if chuong_line:
            body_out.append(chuong_line)
            body_out.append("")
        if i == 0 and preamble and any(l.strip() for l in preamble):
            body_out.extend(preamble)
            body_out.append("")
        body_out.append(clause_text)

        content = "\n".join(yaml_lines) + "\n\n" + "\n".join(body_out).rstrip() + "\n"
        with open(khoan_path, "w", encoding="utf-8") as f:
            f.write(content)

        json_records.append({
            **{k: new_fm[k] for k in order if k != "doc_id"},
            "doc_id": new_fm["doc_id"],
            "khoan": num,
            "noi_dung": clause_text if i > 0 or not (preamble and any(l.strip() for l in preamble))
                        else ("\n".join(preamble).strip() + "\n\n" + clause_text),
        })

print("articles processed:", len(files))
print("total chunk records:", len(json_records))

# rebuild _index.json
files_now = sorted(f for f in os.listdir(FOLDER) if f.endswith(".md"))
index = []
for fname in files_now:
    path = os.path.join(FOLDER, fname)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    fm, _, _ = parse_front_matter(text)
    index.append({
        "doc_id": fm["doc_id"],
        "path": f"markdown_chunks/luat_kbcb/{fname}",
        "dieu": int(fm["dieu"]),
        "khoan": fm.get("khoan"),
        "tieu_de": fm["tieu_de_dieu"],
        "chuong": fm.get("chuong", ""),
        "muc": fm.get("muc", ""),
        "chars": len(text),
    })
with open(os.path.join(FOLDER, "_index.json"), "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

print("final chunk count:", len(index))
print("max chars:", max(x["chars"] for x in index))
print("avg chars:", round(sum(x["chars"] for x in index)/len(index)))

# consolidated JSON for easy programmatic retrieval
json_records.sort(key=lambda r: (int(r["dieu"]), int(r["khoan"]) if r.get("khoan") else 0))
os.makedirs(os.path.dirname(JSON_OUT), exist_ok=True)
with open(JSON_OUT, "w", encoding="utf-8") as f:
    json.dump(json_records, f, ensure_ascii=False, indent=2)
print("wrote consolidated JSON:", JSON_OUT, "-", len(json_records), "records")
