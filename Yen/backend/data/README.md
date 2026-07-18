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
| `raw/` | 6 file PDF gốc, không chỉnh sửa — dùng để đối chiếu/kiểm tra khi cần |
| `structured/` | Bảng giá dạng CSV + XLSX đầy đủ (mỗi dòng = 1 dịch vụ) — dùng cho tra cứu chính xác, báo cáo, hoặc nạp trực tiếp vào công cụ RAG hỗ trợ bảng |
| `markdown_chunks/` | Các đoạn văn bản markdown đã chunk sẵn, có front-matter YAML metadata — dùng để embedding |
| `scripts/` | Script Python tái tạo `markdown_chunks/` và `manifest.json` từ `raw/`/`structured/` khi dữ liệu nguồn thay đổi |
| `manifest.json` | Chỉ mục tổng hợp toàn bộ 7 tài liệu + 357 chunk (đường dẫn, danh mục, STT, ngày hiệu lực...) |

## 7 tài liệu nguồn

| source_id | Tài liệu | Loại | Cơ sở pháp lý / nguồn | Số dòng/điều |
|---|---|---|---|---|
| `luat_kbcb_2023` | Luật Khám bệnh, chữa bệnh 15/2023/QH15 | Văn bản pháp lý | — | 121 điều |
| `huong_dan` | Hướng dẫn cho người bệnh (đặt lịch khám; chi phí khám mẫu) | Hướng dẫn hành chính | — | 2 chunk |
| `youmed_gioi_thieu` | Hướng dẫn khám tại BV Tim Hà Nội (YouMed, bên thứ ba) | Bài viết giới thiệu | youmed.vn, đăng 17/04/2026 | 3 chunk |
| `bhyt_2023` | Bảng giá Bảo hiểm y tế | Bảng giá dịch vụ | Thông tư 22/2023/TT-BYT | 701 dòng |
| `dvkt_2025` | Giá dịch vụ kỹ thuật 2025 | Bảng giá dịch vụ | Nghị quyết 45/2024/NQ-HĐND | 2.946 dòng |
| `dvkt_thuong` | Bảng giá Dịch vụ kỹ thuật | Bảng giá dịch vụ | Thông tư 14/2019/TT-BYT | 925 dòng |
| `dvkt_yeu_cau` | Bảng giá Dịch vụ kỹ thuật theo yêu cầu | Bảng giá dịch vụ | QĐ 2823/QĐ-BVT; QĐ 3165/QĐ-BVT | 102 dòng |

## Quy ước chunk markdown

**Văn bản pháp lý** (`markdown_chunks/luat_kbcb/dieu_NNN.md`): mỗi file = 1 Điều
trong luật (đơn vị ngữ nghĩa tự nhiên để trích dẫn/tham chiếu). Front-matter gồm
`chuong`, `muc`, `dieu`, `so_hieu`, `ngay_hieu_luc`. Vài Điều dài (vd. Điều 110, 121,
~6.000 ký tự) — nếu bộ chunker downstream (LlamaIndex/LangChain) cần chia nhỏ hơn
512–1024 token thì nên chia theo ranh giới khoản (`1.`, `2.`...) chứ không cắt giữa câu.

**Bảng giá** (`markdown_chunks/{bhyt_2023,dvkt_2025,dvkt_thuong,dvkt_yeu_cau}/*.md`):
mỗi file là 1 bảng markdown con của một `danh_muc` (và `nhom_con` nếu có, vd. các
loại phẫu thuật A/B/C), giới hạn ~2.800 ký tự/chunk (an toàn dưới 1024 token) và
tối đa 60 dòng, không cắt giữa dòng. Cột giá đã format số có dấu chấm phân cách
nghìn. Front-matter gồm `danh_muc`, `nhom_con`, `stt_tu`/`stt_den`, `co_so_phap_ly`,
`file_goc`, `file_cau_truc` (trỏ về CSV gốc nếu cần tra số liệu chính xác tuyệt đối).

**Hướng dẫn hành chính** (`markdown_chunks/huong_dan/*.md`): mỗi file 1 chủ đề, có
heading theo mục — gồm hướng dẫn liên hệ đặt lịch khám (nguồn: PDF của bệnh viện) và
bảng chi phí khám mẫu (nguồn: YouMed, chuyển từ `youmed_gioi_thieu/` sang đây vì đúng
bản chất là nội dung hướng dẫn/tham khảo hơn là giới thiệu).

## manifest.json

```jsonc
{
  "documents": [ /* 7 tài liệu, mỗi cái có source_id, title, raw_file,
                    structured_files, markdown_chunk_dir, chunk_count... */ ],
  "chunks": [ /* toàn bộ 357 chunk, mỗi cái có doc_source, chunk_id, path, chars,
                 extra (metadata riêng theo loại tài liệu) */ ]
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
python split_law.py        # raw law PDF -> markdown_chunks/luat_kbcb/
python chunk_prices.py     # structured/*.csv -> markdown_chunks/{bhyt_2023,dvkt_2025,dvkt_thuong,dvkt_yeu_cau}/
python build_manifest.py   # gộp tất cả _index.json -> manifest.json
```

`markdown_chunks/huong_dan/` và `markdown_chunks/youmed_gioi_thieu/` được biên soạn thủ
công từ nội dung trang web (không có script tái tạo tự động vì nguồn là HTML, không phải
PDF có thể tải lại y hệt) — nếu nội dung gốc trên web thay đổi, cần cập nhật lại bằng tay.
