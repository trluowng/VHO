# Kho dữ liệu sơ cứu (First-aid) — nguồn tham chiếu & rule-base

Thư mục này chứa **dữ liệu sơ cứu** cho "An" (trợ lý AI tư vấn triệu chứng): danh sách nguồn
tham khảo có kiểm chứng, một bộ rule sơ cứu ở dạng nháp, và một bảng Excel tổng hợp để soạn/rà
soát nội dung trước khi đưa vào hệ thống.

**Đây KHÔNG phải một mô hình chẩn đoán** và không được dùng để tự động kích hoạt hành động
không thể đảo ngược (gọi xe cấp cứu thật, gửi cảnh báo cho người thân...). Mọi rule đều ở
trạng thái `needs_clinician_review` — nghĩa là **chưa có bác sĩ nào duyệt**, chỉ dùng để
nghiên cứu/nháp cho tới khi có người có chuyên môn y tế xác nhận.

---

## 1. Các file trong thư mục này

### `source_registry.json`
Danh mục các **nguồn tham khảo** (WHO, WHO-ICRC, NHS, CDC, Mayo Clinic, MedlinePlus, American
Red Cross, Bộ Y tế Việt Nam...). Mỗi nguồn có:

| Trường | Ý nghĩa |
|---|---|
| `id` | mã định danh, dùng để trích dẫn trong `rules.seed.json` (`evidence.source_id`) |
| `landing_url` / `allowed_domains` | trang gốc, giới hạn domain được phép tải (an toàn cho crawler) |
| `fetch_mode` | `metadata_only` (chỉ lưu thông tin nguồn) hoặc `download_and_extract` (được phép tải & trích văn bản) |
| `license` | điều khoản bản quyền — quyết định có được trích dẫn nguyên văn hay không |
| `topics` | các chủ đề nguồn này bao phủ, dùng để đối chiếu khi gắn `evidence` cho một rule |
| `requires_clinician_review` | luôn `true` trong thư mục này |

File này là **danh sách được duyệt trước** — chỉ thêm nguồn mới sau khi đã kiểm tra chủ sở
hữu, giấy phép, đối tượng độc giả và tần suất cần cập nhật lại.

### `rules.seed.json`
**Rule-base sơ cứu** — nơi hệ thống (khi được nối vào agent) sẽ tra cứu để đưa ra hướng dẫn.
Hiện có **150 rule**, mỗi rule có cấu trúc:

```jsonc
{
  "id": "GT-042-...",                 // mã định danh (FA-xxx = 15 rule gốc, GT-xxx = mở rộng)
  "status": "needs_clinician_review", // luôn giữ nguyên cho tới khi được duyệt chính thức
  "scope": "adult_or_child",          // đối tượng áp dụng
  "signals_any": ["...", "..."],      // tín hiệu CHUẨN HÓA (slug), không phải từ khóa thô người dùng gõ
  "signals_any_vi": ["...", "..."],   // câu tiếng Việt gốc, tương ứng 1-1 với signals_any
  "decision": "emergency",            // "emergency" (gọi 115 ngay) hoặc "non_emergency" (tự chăm sóc/khám thường)
  "education_actions": ["...", ...],  // các bước nên làm — dạng slug
  "education_actions_vi": ["...", ...], // các bước nên làm — câu tiếng Việt
  "never_do": ["...", ...],
  "never_do_vi": ["...", ...],
  "escalation_vi": "...",             // câu mô tả khi nào cần leo thang (gọi 115 / đi khám ngay)
  "evidence": [{"source_id": "...", "topic": "..."}],
  "review": {"clinical_approver": null, "reviewed_at": null, "expires_at": null},
  "name_vi": "...",                   // tên bệnh/tình huống (chỉ có ở rule sinh từ Excel, GT-xxx)
  "category_vi": "..."                // nhóm bệnh (chỉ có ở rule sinh từ Excel, GT-xxx)
}
```

Ở đầu file còn có `global_guards` (nguyên tắc an toàn áp dụng cho MỌI rule, vd "luôn xác nhận
hiện trường an toàn trước", "không trì hoãn cấp cứu để tiếp tục hỏi han") và bản dịch tiếng
Việt `global_guards_vi`.

Hai nhóm rule trong file (phân biệt qua tiền tố `id`):
- **`FA-001` → `FA-015`** — 15 rule khẩn cấp gốc, viết tay, tất cả `decision = "emergency"`
  (chảy máu nặng, ngưng thở, hôn mê, hóc dị vật, bỏng hóa chất, đột quỵ, nhồi máu cơ tim, sốc
  phản vệ, co giật, đuối nước, say nắng, hạ thân nhiệt, điện giật, ngộ độc, rắn/côn trùng cắn).
- **`GT-001` → `GT-135`** — 135 rule sinh **tự động** từ `first_aid_ground_truth.xlsx` bằng
  script `sync_ground_truth_to_rules.py` (xem mục 3). Gồm cả `emergency` lẫn `non_emergency`.

>  **Không sửa tay các rule `GT-xxx` trong file JSON này.** Vì chúng được sinh tự động từ
> Excel, sửa trực tiếp trong JSON sẽ bị ghi đè/mất đồng bộ ở lần chạy script sau. Hãy sửa trong
> `first_aid_ground_truth.xlsx` rồi chạy lại script đồng bộ.

### `first_aid_ground_truth.xlsx`
Bảng Excel **dùng để soạn thảo và rà soát** — dễ đọc, dễ sửa hàng loạt hơn JSON. Sheet
`First-aid Ground Truth` có 150 dòng, 12 cột:

| Cột | Ý nghĩa |
|---|---|
| STT, Mã (ID) | số thứ tự và mã (`FA-xxx` / `GT-xxx`) |
| Tên bệnh / tình huống, Nhóm | tên và danh mục (Tim mạch, Thần kinh, Nhi khoa, Ngộ độc...) |
| Mức độ khẩn cấp | mô tả tự nhiên cho người đọc (vd "Khẩn cấp - Gọi 115", "Tự chăm sóc tại nhà") |
| Dấu hiệu nhận biết | triệu chứng, phân tách bằng dấu phẩy `,` |
| Hướng dẫn sơ cứu / xử trí ban đầu | các bước nên làm, phân tách bằng dấu chấm phẩy `;` |
| Không nên làm | các việc cần tránh, phân tách bằng dấu chấm phẩy `;` |
| Khi nào cần gọi 115 / đi khám ngay | ngưỡng leo thang |
| Trạng thái | luôn là "Cần chuyên gia y tế duyệt trước khi áp dụng" |
| Source | tên tổ chức nguồn (không phải URL cụ thể — xem mục Giấy phép) |
| **Phân loại (JSON)** | **`emergency`** hoặc **`non_emergency`** — cột duy nhất mà script đồng bộ đọc để quyết định `decision` của rule sinh ra |

Sheet `README` (trong chính file Excel) tóm tắt lại ranh giới an toàn và cách đối chiếu cột với
schema JSON.

**Lưu ý khi sửa**: chỉ sửa nội dung theo đúng dấu phân tách đã quy ước (`,` cho Dấu hiệu nhận
biết, `;` cho hai cột hướng dẫn), nếu không script đồng bộ sẽ tách câu sai chỗ.

---

## 2. Các script liên quan (nằm ở `../../scripts/`, không nằm trong thư mục này)

| Script | Vai trò |
|---|---|
| `scripts/crawl_first_aid_sources.py` | Tải nguồn đã duyệt trong `source_registry.json` về (allow-list, không tự dò link). `--dry-run` để kiểm tra trước, `--extract` để tải + trích văn bản thật. |
| `scripts/validate_first_aid_rules.py` | Kiểm tra `rules.seed.json` + `source_registry.json` đúng cấu trúc và đúng ranh giới an toàn (id không trùng, `status` phải là `needs_clinician_review`, `decision` phải là `emergency`/`non_emergency`, có đủ `education_actions`/`never_do`, `evidence.source_id` phải tồn tại trong registry...). |
| `scripts/sync_ground_truth_to_rules.py` | Đọc `first_aid_ground_truth.xlsx`, chuyển các dòng **chưa có** trong `rules.seed.json` thành rule mới rồi nối vào — xem mục 3. |

## 3. Quy trình cập nhật dữ liệu

```text
Sửa/thêm dòng trong first_aid_ground_truth.xlsx (Excel)
        ↓
python scripts/sync_ground_truth_to_rules.py [--dry-run]
        ↓
python scripts/validate_first_aid_rules.py
        ↓
rules.seed.json được cập nhật, sẵn sàng để (sau khi bác sĩ duyệt) nối vào agent
```

- **Không trùng lặp**: script đồng bộ so khớp theo *tiền tố số* của mã (`FA-006`, `GT-042`...),
  bỏ qua mọi rule đã tồn tại trong JSON — chạy lại bao nhiêu lần cũng an toàn, không tạo bản
  sao. Chỉ những dòng có mã **chưa từng xuất hiện** trong `rules.seed.json` mới được thêm.
- Dùng `--dry-run` để xem trước sẽ thêm bao nhiêu rule mà chưa ghi file:
  `python scripts/sync_ground_truth_to_rules.py --dry-run`.
- Sau khi thêm dòng mới vào Excel, luôn chạy `validate_first_aid_rules.py` để chắc chắn không
  có `evidence.source_id` nào trỏ tới nguồn chưa khai báo trong `source_registry.json`.

---

## 4. Ranh giới an toàn (bắt buộc tuân thủ)

- Mọi rule bắt đầu ở trạng thái `needs_clinician_review`; ứng dụng phải từ chối áp dụng bất kỳ
  rule nào có trạng thái khác, trừ khi đã ghi rõ người duyệt (`clinical_approver`), ngày duyệt
  và ngày hết hạn.
- `signals_any`/`signals_any_vi` là **tín hiệu chuẩn hóa**, không phải từ khóa thô người dùng
  gõ. Các rule sinh từ Excel (`GT-xxx`) có slug tín hiệu được cắt tự động từ câu tiếng Việt —
  đây chỉ là **giá trị tạm**, cần một kỹ sư NLP/bác sĩ tinh chỉnh lại thành tín hiệu chuẩn thật
  sự trước khi dùng để so khớp trong sản phẩm.
- `decision` chỉ có hai giá trị: `emergency` (leo thang ngay, gợi ý gọi 115) hoặc
  `non_emergency` (tự chăm sóc/khám thường, có ngưỡng leo thang riêng ghi ở `escalation_vi`).
  Cả hai loại đều cần được bác sĩ duyệt trước khi dùng thật, dù mức độ khẩn cấp khác nhau.
  Không tự động dispatch 115.
- Bộ rule chỉ dùng cho mục đích **giáo dục và hướng dẫn leo thang**, không chứa liều thuốc,
  không đưa chẩn đoán.
- Quy trình cấp cứu ở Việt Nam (gọi 115, giao thức địa phương) cần được rà soát riêng trước
  khi phát hành chính thức — dữ liệu này không mặc định coi quy trình quốc tế tương đương với
  quy trình Việt Nam.

## 5. Giấy phép nguồn

`source_registry.json` chặn tải nội dung trừ khi nguồn cho phép rõ ràng. Sách WHO/ICRC Basic
Emergency Care dùng giấy phép CC BY-NC-SA 3.0 IGO (yêu cầu ghi nguồn, phi thương mại, chia sẻ
tương tự). NHS, Mayo Clinic, CDC, MedlinePlus, American Red Cross, Bộ Y tế Việt Nam hiện chỉ
được lưu dưới dạng **tên tổ chức tham chiếu** (cột Source trong Excel) — không kèm URL bài viết
cụ thể, và chưa được rà soát điều khoản tái sử dụng nội dung đầy đủ.

---

## 6. Các bước để nối rule-base này vào agent + server

> Phần này là **hướng dẫn triển khai** — hiện `rules.seed.json` chưa được `agent.py`/
> `server.py` đọc tới, đây là dữ liệu độc lập. Dưới đây là các bước cụ thể để nối vào, theo
> đúng kiến trúc tool hiện có của "An" (`tools/<tên_tool>/{TOOL.md, tool.py}`, đăng ký trong
> `tools/__init__.py`, khai báo trong `artifacts/tools.yaml`, dạy model dùng qua
> `artifacts/system_prompt.md`).

### Bước 1 — Tạo tool mới `tools/first_aid/`
Theo đúng "Tool Folder Contract" đã có (xem `tools/README.md`):

```text
tools/first_aid/
  TOOL.md     # frontmatter: name, track, kind: local_knowledge, inputs, outputs, side_effect: false
  tool.py     # hàm lookup_first_aid(signal_query: str, ...) -> dict
```

`tool.py` cần:
1. Load `data/first_aid/rules.seed.json` một lần khi import (giống cách `env_loader`/
   `providers` load config).
2. **Lọc bỏ rule chưa được duyệt thật sự nếu muốn an toàn tối đa**: vì hiện tất cả 150 rule
   đều `needs_clinician_review` (chưa duyệt), bước triển khai đầu tiên nên coi kết quả trả về
   là **gợi ý tham khảo kèm cảnh báo rõ ràng**, không phải hướng dẫn xác định — hoặc chặn hẳn
   cho tới khi có ít nhất một rule có `review.clinical_approver != null`.
3. So khớp `signal_query` (câu mô tả triệu chứng từ model) với `signals_any_vi` bằng so khớp
   từ khóa đơn giản trước (vd overlap từ, không cần NLP phức tạp ở bản đầu).
4. Trả về `decision`, `education_actions_vi`, `never_do_vi`, `escalation_vi`, và luôn kèm một
   cờ `needs_clinician_review: true` để tầng gọi phía trên (system prompt) biết mà thêm
   disclaimer.

### Bước 2 — Đăng ký trong `tools/__init__.py`
Thêm import + một dòng trong `TOOL_FUNCTIONS`:
```python
from .first_aid.tool import lookup_first_aid
...
TOOL_FUNCTIONS = {
    "clarify": ask_user,
    "lookup": web_search,
    "fetch": read_url,
    "format": render_digest,
    "first_aid": lookup_first_aid,   # tên này phải khớp tools.yaml bên dưới
}
```

### Bước 3 — Khai báo trong `artifacts/tools.yaml`
Thêm một entry `first_aid` theo đúng format các tool khác (name, description tiếng Việt,
parameters kiểu JSON-schema, vd `signal_query: string`).

### Bước 4 — Dạy model khi nào gọi tool trong `artifacts/system_prompt.md`
Bổ sung một đoạn hướng dẫn: sau khi Red-Flag Engine phía client hoặc model tự nhận diện tình
huống khẩn cấp/cần hướng dẫn xử trí cụ thể, gọi tool `first_aid` để lấy `education_actions_vi`/
`never_do_vi`, rồi **luôn** đính kèm disclaimer "Đây không phải chẩn đoán y khoa, dữ liệu sơ
cứu chưa được bác sĩ duyệt chính thức" trước khi hiển thị cho người dùng — khớp với disclaimer
đã có sẵn ở luồng triage hiện tại (xem `An/README.md`).

### Bước 5 — Khởi động lại backend
```bash
cd An/backend
python -X utf8 server.py
```
Tool mới chỉ được nạp khi `server.py` khởi động lại (nó load `tools/__init__.py` và
`artifacts/tools.yaml` một lần lúc bootstrap — xem đầu file `server.py`).

### Bước 6 — Kiểm thử
- Gọi thử qua endpoint `POST /triage` với một câu mô tả triệu chứng khớp một rule đã có, kiểm
  tra tool `first_aid` có được model gọi và phản hồi có kèm disclaimer hay không.
- Chạy `python run_eval.py` (nếu có case eval cho tool mới) để đảm bảo không phá vỡ các case
  hiện tại của `clarify`/`lookup`/`fetch`/`format`.
- Trước khi coi là "production", đảm bảo mọi rule dùng thật đã được một bác sĩ/chuyên gia y tế
  cập nhật `review.clinical_approver`, `reviewed_at`, `expires_at` trong `rules.seed.json`.

