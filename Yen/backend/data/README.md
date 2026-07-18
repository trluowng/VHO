# Dữ liệu Bệnh viện Tim Hà Nội — chuẩn bị cho RAG

Thư mục này chứa dữ liệu đã crawl/trích xuất từ website Bệnh viện Tim Hà Nội và
thuvienphapluat.vn, được tổ chức để đưa vào pipeline RAG:

```
Tài liệu gốc (PDF) → OCR/extract text → Markdown chunk (giữ bảng nguyên vẹn)
→ Gắn metadata (nguồn, mục, ngày hiệu lực) → [bước tiếp theo: embedding, vector DB...]
```

## Cấu trúc thư mục

| Thư mục | Nội dung |
|---|---|
| `raw/` | 17 file gốc (PDF + 1 ảnh sơ đồ), không chỉnh sửa — dùng để đối chiếu/kiểm tra khi cần |
| `structured/` | Bảng giá dạng CSV + XLSX đầy đủ (mỗi dòng = 1 dịch vụ) — dùng cho tra cứu chính xác, báo cáo, hoặc nạp trực tiếp vào công cụ RAG hỗ trợ bảng |
| `markdown_chunks/` | Các đoạn văn bản markdown đã chunk sẵn, có front-matter YAML metadata — dùng để embedding |
| `scripts/` | Script Python tái tạo `markdown_chunks/` và `manifest.json` từ `raw/`/`structured/` khi dữ liệu nguồn thay đổi |
| `manifest.json` | Chỉ mục tổng hợp toàn bộ 12 tài liệu + 1.348 chunk (đường dẫn, doc_id/chunk_id/parent_id, section, ngày hiệu lực...) |

## 12 tài liệu nguồn

| source_id | Tài liệu | Loại | Cơ sở pháp lý / nguồn | Số dòng/điều |
|---|---|---|---|---|
| `luat_kbcb_2023` | Luật Khám bệnh, chữa bệnh 15/2023/QH15 | Văn bản pháp lý | — | 121 điều → 1.013 chunk (cấu trúc khoản-cha/điểm-con) |
| `huong_dan` | Hướng dẫn cho người bệnh (đặt lịch khám; chi phí khám mẫu; lưu ý trước khi khám; giờ/lưu ý thăm bệnh) | Hướng dẫn hành chính | — | 21 chunk (cấu trúc phân cấp ##/###/khoản/điểm) |
| `youmed_gioi_thieu` | Hướng dẫn khám tại BV Tim Hà Nội (YouMed, bên thứ ba) | Bài viết giới thiệu | youmed.vn, đăng 17/04/2026 | 17 chunk (cấu trúc phân cấp ##/###/khoản/điểm) |
| `quy_trinh` | Quy trình đón tiếp bệnh nhân và KCB ngoại trú tại khu Tự nguyện 1 - CS1 | Quy trình SOP nội bộ | QT.25.01, ban hành 05/12/2024, lần 07 (Giám đốc BVT phê duyệt) | 22 chunk (cấu trúc phân cấp theo bước/trách nhiệm) |
| `khoa_phong` | Giới thiệu khoa/phòng (Khoa Dược, Khoa KBTN) + sơ đồ tổ chức 3 khối | Giới thiệu khoa phòng | benhvientimhanoi.vn (URL chưa xác định) | 23 chunk (cấu trúc phân cấp ##/###/khoản/điểm) |
| `lich_su_phat_trien` | Quá trình phát triển bệnh viện (2001–2013+) | Giới thiệu lịch sử | benhvientimhanoi.vn (URL chưa xác định) | 3 chunk |
| `bookingcare_gioi_thieu` | Tổng quan 2 cơ sở + 5 mũi nhọn chuyên môn | Bài viết giới thiệu (bên thứ ba) | bookingcare.vn (URL chưa xác định) | 9 chunk (cấu trúc phân cấp ##/###/khoản/điểm) |
| `dich_vu` | Khám sức khỏe cho cơ quan - doanh nghiệp | Giới thiệu dịch vụ | benhvientimhanoi.vn (URL chưa xác định) | 9 chunk (cấu trúc phân cấp ##/###/khoản/điểm) |
| `bhyt_2023` | Bảng giá Bảo hiểm y tế | Bảng giá dịch vụ | Thông tư 22/2023/TT-BYT | 701 dòng |
| `dvkt_2025` | Giá dịch vụ kỹ thuật 2025 | Bảng giá dịch vụ | Nghị quyết 45/2024/NQ-HĐND | 2.946 dòng |
| `dvkt_thuong` | Bảng giá Dịch vụ kỹ thuật | Bảng giá dịch vụ | Thông tư 14/2019/TT-BYT | 925 dòng |
| `dvkt_yeu_cau` | Bảng giá Dịch vụ kỹ thuật theo yêu cầu | Bảng giá dịch vụ | QĐ 2823/QĐ-BVT; QĐ 3165/QĐ-BVT | 102 dòng |

## Schema metadata chuẩn (áp dụng cho cả 12 tài liệu)

Ngoài các field riêng theo loại tài liệu (`chuong`/`muc`/`dieu` cho luật, `danh_muc`/
`nhom_con`/`stt_tu`/`stt_den` cho bảng giá, `ma_so`/`nguoi_phe_duyet` cho quy trình...),
**mọi chunk** đều có 8 field chuẩn hóa sau trong front-matter. Ba field đầu là **3 khái
niệm ID tách biệt, không gộp làm một** — mỗi cái có vai trò và độ ổn định riêng:

| Field | Ý nghĩa | Độ ổn định | Ví dụ |
|---|---|---|---|
| `doc_id` | Định danh **toàn bộ tài liệu gốc** — hằng số, giống nhau cho mọi chunk thuộc cùng 1 tài liệu | Rất ổn định, gắn với văn bản/quyết định, ít đổi | `luat_kbcb_2023` (giống nhau ở cả 1.013 chunk luật); `bhyt_2023` |
| `chunk_id` | Định danh **1 chunk cụ thể** sau khi tách — duy nhất, đặt theo cấu trúc nội dung (không theo số thứ tự phát sinh) | Ổn định theo nội dung/cấu trúc | `luat_kbcb_dieu_115_k1a`; `bhyt_001` |
| `parent_id` | `chunk_id` của **chunk cha** mà chunk này trực thuộc trong cấu trúc phân cấp; rỗng nếu là chunk gốc/độc lập (không phải mọi tài liệu đều có phân cấp) | Ổn định theo cấu trúc phân cấp của tài liệu | `luat_kbcb_dieu_115_k1` |
| `source_doc` | Tên văn bản/nguồn gốc (mô tả người đọc được) | | `Luật Khám bệnh, chữa bệnh số 15/2023/QH15` |
| `section` | Vị trí trong văn bản gốc (mô tả người đọc được) | | `Điều 115 - Khoản 1 - Điểm a)` |
| `category` | Nhóm chủ đề chuẩn hóa | | `van_ban_phap_ly`, `bao_hiem_y_te`, `gia_dich_vu`... |
| `effective_date` | Ngày hiệu lực/ban hành (rỗng nếu không rõ) | | `2024-01-01` |
| `approved_by` | Cơ quan/người phê duyệt (rỗng nếu không rõ) | | `Quốc hội` |

`doc_id` cho phép gom/lọc mọi chunk thuộc cùng 1 tài liệu; `chunk_id` là khoá duy nhất
của từng chunk; `parent_id` cho phép dựng lại cây phân cấp (vd. truy vấn "khoản 1" trả
về chunk cha tổng quát, truy vấn "điểm a của khoản 1" trả về đúng chunk con cụ thể) —
đọc 3 field song song để biết chunk này thuộc tài liệu nào, là gì, và nằm dưới chunk nào.

## Quy ước chunk markdown

**Văn bản pháp lý** (`markdown_chunks/luat_kbcb/dieu_NNN.md`, `dieu_NNN_kK.md`,
`dieu_NNN_kKx.md`): tách theo cấu trúc pháp lý 2 cấp **khoản-cha / điểm-con**, không
theo ngân sách token:
- 1 khoản (`1.`, `2.`, `3.`...) **có** điểm lẻ (`a)`, `b)`, `c)`...) → tách thành 1
  chunk **cha** `dieu_NNN_kK.md` (chỉ chứa câu dẫn trước điểm `a)` đầu tiên, `section:
  "Điều N - Khoản K"`, `parent_id: ""`) + N chunk **con** `dieu_NNN_kKa.md`,
  `_kKb.md`... (mỗi điểm 1 chunk, `section: "Điều N - Khoản K - Điểm a)"`,
  `parent_id` trỏ về chunk_id của chunk cha). Nội dung không lặp giữa cha/con.
- 1 khoản **không có** điểm lẻ → cả khoản là 1 chunk độc lập `dieu_NNN_kK.md`
  (`parent_id: ""`).
- 1 Điều không có khoản nào (hiếm) → cả Điều là 1 chunk `dieu_NNN.md`.

Nhờ vậy khi RAG truy vấn tới "khoản 1" sẽ ra chunk cha (tổng quát), còn truy vấn tới
"điểm a của khoản 1" sẽ ra đúng chunk con cụ thể. 121 điều → 1.013 chunk, kích thước
dao động ~500-1.600 ký tự tùy độ dài điểm/khoản gốc — không ép về một khoảng token
cố định vì ưu tiên bám sát ranh giới cấu trúc thật của văn bản.

**Bảng giá** (`markdown_chunks/{bhyt_2023,dvkt_2025,dvkt_thuong,dvkt_yeu_cau}/*.md`):
mỗi file là 1 bảng markdown con của một `danh_muc` (và `nhom_con` nếu có, vd. các
loại phẫu thuật A/B/C), giới hạn ~2.800 ký tự/chunk (an toàn dưới 1024 token) và
tối đa 60 dòng, không cắt giữa dòng. Cột giá đã format số có dấu chấm phân cách
nghìn. Front-matter gồm `danh_muc`, `nhom_con`, `stt_tu`/`stt_den`, `co_so_phap_ly`,
`file_goc`, `file_cau_truc` (trỏ về CSV gốc nếu cần tra số liệu chính xác tuyệt đối).

**7 tài liệu tường thuật** (`huong_dan/`, `khoa_phong/`, `lich_su_phat_trien/`,
`dich_vu/`, `bookingcare_gioi_thieu/`, `quy_trinh/`, `youmed_gioi_thieu/`): áp dụng
cùng nguyên tắc tách theo cấu trúc thật (không theo ngân sách token) như `luat_kbcb`,
nhưng đệ quy qua 4 cấp đánh dấu theo thứ tự **từ ngoài vào trong**: heading `## ` →
heading `### ` → khoản số `1.`/`2.`/`3.`... → điểm chữ `a)`/`b)`/`c)`... Tại mỗi cấp,
nếu tìm được ≥ 2 khớp thì file gốc/nút hiện tại trở thành 1 chunk **cha** (`*_s1`,
`*_x1`, `*_c1`... chỉ chứa câu dẫn trước mục con đầu tiên, không lặp nội dung) + N
chunk **con** (mỗi mục 1 chunk, `parent_id` trỏ về cha) — mỗi con lại được đệ quy
kiểm tra tiếp theo đúng thứ tự trên. Không tìm thấy mục nào ở bất kỳ cấp nào → cả
nút là 1 chunk lá duy nhất. Đảo ngược thứ tự ưu tiên (vd. kiểm tra khoản/điểm trước
heading) sẽ làm một `###` nằm sâu trong 1 mục `##` tranh mất quyền tách với `##` ở
gốc, phá vỡ đúng lồng cấu trúc — vì vậy heading lớn nhất luôn được bóc trước.
`quy_trinh/` giữ nguyên cấu trúc "Bước / Trách nhiệm / Mô tả" của văn bản gốc;
front-matter có `ma_so` (vd. QT.25.01), `ngay_ban_hanh`, `lan_ban_hanh`,
`nguoi_phe_duyet` — quan trọng để AI trích dẫn đúng phiên bản quy trình khi trả lời
câu hỏi về nghiệp vụ/workflow. Nguồn `quy_trinh` là PDF scan ảnh (đọc bằng thị giác).
Vì văn bản SOP đánh dấu ranh giới bước bằng `*Trách nhiệm: ...*` (in nghiêng) thay vì
heading chuẩn, các mốc này được tách thủ công theo cùng nguyên tắc cha/con (mỗi
`*Trách nhiệm:*` = 1 chunk con, `parent_id` trỏ về mục lớn chứa nó) — ví dụ mục
"Thu phí, đo dấu hiệu sinh tồn" tách thành Bước 4 (thu phí) và Bước 5 (đo DHST).

## manifest.json

```jsonc
{
  "documents": [ /* 12 tài liệu, mỗi cái có source_id, title, raw_file,
                    structured_files, markdown_chunk_dir, chunk_count... */ ],
  "chunks": [ /* toàn bộ 1.348 chunk, mỗi cái có 8 field chuẩn (doc_id, chunk_id,
                 parent_id, source_doc, section, category, effective_date,
                 approved_by) + path, chars, và extra (field riêng theo loại
                 tài liệu, vd. dieu/chuong/muc cho luật, danh_muc/stt cho bảng giá) */ ]
}
```

Dùng `chunks[].path` (tương đối so với `E:\VHO\data\`) để đọc từng file markdown khi
nạp vào bước embedding.

## Lưu ý về độ chính xác

- Bảng giá BHYT, DVKT, DVKTYC được trích từ PDF **scan ảnh** (không có lớp text) — đọc
  bằng thị giác qua nhiều agent song song, đã kiểm tra chéo (không trùng/thiếu STT
  trong từng danh mục) nhưng có thể còn sai sót nhỏ ở vài dòng bị mờ/cắt chữ trong
  bản gốc (đã ghi chú "UNCERTAIN" tại thời điểm trích nếu có).
- File `gia_dv_ky_thuat_2025.pdf` và `15_2023_QH15_372143.pdf` có lớp text thật nên
  trích xuất trực tiếp, độ chính xác cao hơn.
- Nếu cần độ chính xác tuyệt đối cho một con số cụ thể (thanh toán, pháp lý), nên đối
  chiếu lại `file_goc` trong `raw/`.
- `youmed_gioi_thieu` là bài viết của bên thứ ba (YouMed), không phải nguồn chính thức
  từ bệnh viện — hữu ích cho câu hỏi tổng quan (địa chỉ, giờ làm, đội ngũ, quy trình
  khám) nhưng KHÔNG dùng làm nguồn giá dịch vụ (bảng giá trong bài chỉ là 11 dòng minh
  họa); ưu tiên `bhyt_2023`/`dvkt_2025`/`dvkt_thuong`/`dvkt_yeu_cau` cho câu hỏi về giá.

## Tái tạo dữ liệu

```bash
cd scripts
python split_law.py          # raw law PDF -> markdown_chunks/luat_kbcb/ (1 file/điều)
python resplit_law.py        # tách khoản-cha/điểm-con + gắn 7 field metadata chuẩn
python chunk_prices.py       # structured/*.csv -> markdown_chunks/{bhyt_2023,dvkt_2025,dvkt_thuong,dvkt_yeu_cau}/
python resplit_narrative.py  # tách đệ quy 7 folder tường thuật theo ##>###>khoản>điểm + gắn 8 field metadata chuẩn
python add_standard_fields.py # gắn 7 field metadata chuẩn cho các tài liệu bảng giá còn lại
python build_manifest.py     # gộp tất cả _index.json -> manifest.json
```

`markdown_chunks/{huong_dan,khoa_phong,youmed_gioi_thieu,lich_su_phat_trien,
bookingcare_gioi_thieu,dich_vu,quy_trinh}/` được biên soạn thủ công từ nội dung
trang web/PDF nguồn (không có script trích xuất ban đầu tự động vì nguồn không đồng
nhất — HTML, PDF có lớp text, PDF scan ảnh). `resplit_narrative.py` chỉ chạy đúng
trên baseline "phẳng" (1 file gốc/chủ đề, chưa có file con `*_s1`/`*_x1`/`*_c1`/`*_a`)
— nếu nội dung gốc thay đổi, cần khôi phục về baseline phẳng (gộp các file con thành
1 file gốc theo `parent_id`) trước khi sửa và chạy lại, rồi chạy tiếp
`build_manifest.py`.

`resplit_law.py` xử lý trực tiếp trên `dieu_NNN.md` do `split_law.py` tạo ra (xoá hết
`dieu_*.md` trong `luat_kbcb/` và chạy lại `split_law.py` trước khi chạy `resplit_law.py`
lần nữa, vì nó xoá file gốc khi tách). `add_standard_fields.py` **an toàn để chạy lại
nhiều lần** trên cùng 1 tập file (tự nhận diện field đã có, không tạo trùng key).
