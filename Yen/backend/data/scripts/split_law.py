# -*- coding: utf-8 -*-
import re
import os
import json
from pypdf import PdfReader

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.dirname(SCRIPT_DIR)  # scripts/ -> data/
SRC_PDF = os.path.join(DATA_DIR, "raw", "15_2023_QH15_372143.pdf")
OUT_DIR = os.path.join(DATA_DIR, "markdown_chunks", "luat_kbcb")
os.makedirs(OUT_DIR, exist_ok=True)

# NOTE: use pypdf, not pdfplumber — this particular PDF's character stream has no
# real space glyphs between words, and pdfplumber (even with layout=True) drops
# them; pypdf's extract_text() reconstructs word spacing correctly.
reader = PdfReader(SRC_PDF)
text = "\n".join(page.extract_text() for page in reader.pages)
lines = [l + "\n" for l in text.split("\n")]

chuong_re = re.compile(r"^Chương\s+([IVXLCDM]+)\s*$")
muc_re = re.compile(r"^Mục\s+(\d+)\.\s*(.+)$")
dieu_re = re.compile(r"^Điều\s+(\d+)\.\s*(.*)$")

records = []
cur_chuong_num = ""
cur_chuong_title = ""
cur_muc = ""
expected_dieu = 1
cur_dieu_num = None
cur_dieu_title = ""
cur_body = []

def flush():
    global cur_dieu_num, cur_dieu_title, cur_body
    if cur_dieu_num is not None:
        body_text = "\n".join(cur_body).strip()
        records.append({
            "dieu": cur_dieu_num,
            "title": cur_dieu_title.strip(),
            "chuong_num": cur_chuong_num,
            "chuong_title": cur_chuong_title,
            "muc": cur_muc,
            "body": body_text,
        })
    cur_dieu_num = None
    cur_dieu_title = ""
    cur_body = []

i = 0
n = len(lines)
while i < n:
    line = lines[i].rstrip("\n")
    stripped = line.strip()

    m_chuong = chuong_re.match(stripped)
    if m_chuong:
        # next non-empty line is the chapter title
        title_line = ""
        j = i + 1
        while j < n and not lines[j].strip():
            j += 1
        if j < n:
            title_line = lines[j].strip()
        cur_chuong_num = m_chuong.group(1)
        cur_chuong_title = title_line
        cur_muc = ""
        i = j + 1
        continue

    m_muc = muc_re.match(stripped)
    if m_muc:
        cur_muc = f"Mục {m_muc.group(1)}. {m_muc.group(2)}"
        i += 1
        continue

    m_dieu = dieu_re.match(stripped)
    if m_dieu and int(m_dieu.group(1)) == expected_dieu:
        flush()
        cur_dieu_num = int(m_dieu.group(1))
        cur_dieu_title = m_dieu.group(2)
        expected_dieu += 1
        i += 1
        # Title sometimes wraps onto the next line in the source PDF.
        # A continuation line is short, starts lowercase, and is not a
        # numbered/lettered clause marker ("1.", "a)", etc.).
        while i < n:
            nxt = lines[i].strip()
            if not nxt:
                break
            if re.match(r"^\d+[.,]", nxt) or re.match(r"^[a-zđ]\)", nxt, re.IGNORECASE):
                break
            if nxt[:1].islower() and len(nxt) < 100:
                cur_dieu_title += " " + nxt
                i += 1
            else:
                break
        continue

    if cur_dieu_num is not None:
        cur_body.append(line)
    i += 1

flush()

print("total dieu extracted:", len(records))
print("first:", records[0]["dieu"], records[0]["title"])
print("last:", records[-1]["dieu"], records[-1]["title"])

# sanity: check sequence
nums = [r["dieu"] for r in records]
expected = list(range(1, len(records) + 1))
if nums != expected:
    print("WARNING: sequence mismatch!")
    print(nums)
else:
    print("sequence OK: 1..", len(records))

# write markdown chunks, one per Dieu (merge tiny ones is not needed; 121 dieu is fine as
# individual chunks since legal articles are natural retrieval units)
SOURCE_META = {
    "nguon": "https://thuvienphapluat.vn/van-ban/The-thao-Y-te/Luat-15-2023-QH15-kham-benh-chua-benh-372143.aspx",
    "file_goc": "raw/15_2023_QH15_372143.pdf",
    "so_hieu": "15/2023/QH15",
    "loai_van_ban": "Luật",
    "ngay_ban_hanh": "2023-01-09",
    "ngay_hieu_luc": "2024-01-01",
    "co_quan_ban_hanh": "Quốc hội",
}

index = []
for r in records:
    fname = f"dieu_{r['dieu']:03d}.md"
    path = os.path.join(OUT_DIR, fname)
    front_matter = {
        "doc_id": f"luat_kbcb_dieu_{r['dieu']:03d}",
        "loai_tai_lieu": "van_ban_phap_ly",
        "chuong": f"Chương {r['chuong_num']}. {r['chuong_title']}" if r["chuong_num"] else "",
        "muc": r["muc"],
        "dieu": r["dieu"],
        "tieu_de_dieu": r["title"],
        **SOURCE_META,
    }
    yaml_lines = ["---"]
    for k, v in front_matter.items():
        if isinstance(v, str) and (":" in v or '"' in v):
            v_esc = v.replace('"', '\\"')
            yaml_lines.append(f'{k}: "{v_esc}"')
        else:
            yaml_lines.append(f"{k}: {v}")
    yaml_lines.append("---")
    content = "\n".join(yaml_lines) + "\n\n"
    content += f"# Điều {r['dieu']}. {r['title']}\n\n"
    if r["chuong_num"]:
        content += f"*{front_matter['chuong']}*"
        if r["muc"]:
            content += f" — *{r['muc']}*"
        content += "\n\n"
    content += r["body"] + "\n"

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    index.append({
        "doc_id": front_matter["doc_id"],
        "path": f"markdown_chunks/luat_kbcb/{fname}",
        "dieu": r["dieu"],
        "tieu_de": r["title"],
        "chuong": front_matter["chuong"],
        "muc": r["muc"],
        "chars": len(content),
    })

with open(os.path.join(OUT_DIR, "_index.json"), "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

print("wrote", len(index), "markdown files to", OUT_DIR)
avg_chars = sum(x["chars"] for x in index) / len(index)
print("avg chars per chunk:", round(avg_chars))
print("max chars:", max(x["chars"] for x in index))
