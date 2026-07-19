# AI Log — Yên (Bệnh viện Tim Hà Nội)

Nhật ký sử dụng công cụ AI trong quá trình phát triển, theo yêu cầu của ban tổ chức:

> Với công cụ AI trực tuyến, hãy chia sẻ link phiên chat. Với công cụ desktop, hãy kèm các file
> phiên như `~/.claude/projects/<project>`, `~/.codex/sessions/`, hoặc thư mục tương đương, cùng
> ảnh chụp màn hình.

## Công cụ AI sử dụng

- **Claude Code** (Anthropic) — model **Claude Sonnet 5** (`claude-sonnet-5`). Công cụ chính,
  dùng bởi `trluowng` xuyên suốt quá trình phát triển.
- **Codex** (OpenAI, `codex_vscode`) — phát hiện có phiên làm việc thật trên chính máy này, cùng
  thư mục dự án (`cwd: D:\AI\VHO`), khớp thời điểm với các commit STT/Groq provider/mock data.

Cả hai đều là công cụ desktop/CLI (không phải chat web có link chia sẻ), nên bằng chứng phiên làm
việc được đính kèm dưới dạng **file log phiên** theo đúng hướng dẫn, thay vì link.

## ⚠️ File phiên làm việc — KHÔNG commit vào git công khai

Đã thử copy 2 file phiên vào repo và bị **GitHub push protection chặn**: file phiên Claude Code
chứa **API key Groq thật** (được dán trực tiếp vào chat trong lúc làm việc) và GitHub còn phát
hiện thêm **1 GCP API key gắn với service account**. File log ghi lại nguyên văn hội thoại nên bất
cứ secret nào từng được dán vào chat đều nằm trong đó — không thể loại bỏ an toàn bằng tay với
file dài hàng chục MB. Do đó **các file phiên KHÔNG được đưa vào repo** này.

**Việc cần làm ngay** (ưu tiên cao, độc lập với AI log):
- **Xoay vòng (rotate) lại Groq API key đã dùng trong phiên này** — key đã bị dán vào chat và ghi
  vào file log cục bộ, phải coi như đã lộ.
- Kiểm tra GCP API key mà GitHub phát hiện — xác định key này ở đâu ra, xoay vòng nếu còn hiệu lực.

**Đường dẫn file phiên (giữ trên máy, KHÔNG đăng công khai)**:

| Công cụ | Đường dẫn trên máy | Kích thước |
|---|---|---|
| Claude Code | `~/.claude/projects/d--AI-VHO/91bb68d9-8ab7-4dfa-848b-e44b13829464.jsonl` (Windows: `C:\Users\tranl\.claude\projects\d--AI-VHO\...jsonl`) | ~80MB |
| Codex (phiên chính) | `~/.codex/sessions/2026/07/17/rollout-2026-07-17T21-39-31-019f7084-9942-75e1-94b2-fdffa713934c.jsonl` | ~23MB |
| Codex (subagent "guardian" nội bộ) | `~/.codex/sessions/2026/07/17/rollout-2026-07-17T22-02-18-019f7099-7547-7302-8e8a-e68de2cef27a.jsonl` | ~330KB |

- File Claude Code là **một phiên làm việc liên tục duy nhất**, tạo lúc 2026-07-15 và còn cập
  nhật tới 2026-07-19 — chứa toàn bộ prompt của người dùng, phản hồi, và mọi hành động Claude Code
  đã thực hiện (đọc/sửa file, chạy lệnh, gọi API test...) trong suốt quá trình phát triển các tính
  năng mô tả bên dưới.
- File Codex bắt đầu lúc 2026-07-17, cùng thư mục dự án này — khả năng cao là phiên của thành viên
  `laiducanh26112004-debug` (các commit STT, Groq provider, mock data bác sĩ/lịch cùng khung thời
  gian) nhưng chưa xác nhận trực tiếp với thành viên đó.
- **Nộp bài**: nếu ban tổ chức có kênh nộp riêng tư (không phải GitHub công khai — vd upload trực
  tiếp lên form/drive nội bộ), xoá secret khỏi file trước rồi mới đính kèm ở đó, không đăng lên
  git. Không có công cụ đáng tin cậy để tự động rà soát hết secret trong file log dài hàng chục MB.
- **Còn thiếu**: ảnh chụp màn hình (terminal lúc chạy + trình duyệt lúc test tính năng) — không
  công cụ nào tự chụp được, cần bổ sung thủ công trước khi nộp.

## Phạm vi công việc do Claude Code hỗ trợ

Log dưới đây liệt kê các commit trong khoảng thời gian phiên làm việc trên bao phủ (2026-07-15 →
2026-07-19), là phần việc Claude Code trực tiếp tham gia thực hiện cùng người dùng (`trluowng`).
Commit hash để đối chiếu với `git log`.

### 2026-07-15 — Đổi hướng sản phẩm, thiết kế lại landing page
- `0c97e46` Đổi tên dự án An → Yên, bỏ lựa chọn giới tính "Khác", đổi bảng màu xanh dương.
- `289ca71`, `cc9d1f4` Thử nghiệm bảng màu (hồng y tế → đỏ tía).
- `c42f5ea` Thêm tab hồ sơ hiển thị thông tin tài khoản + hồ sơ sức khỏe.
- `a4752d0`, `d54f23c`, `7f6bf11`, `b6eb66f`, `69ecf07`, `93241e3` Thiết kế lại toàn bộ landing
  page theo ảnh tham chiếu (Tailwind CSS + Lucide icons, đổi bảng màu cuối cùng sang "Clarity
  Teal", chỉnh minh hoạ hero nhiều vòng).

### 2026-07-15 → 2026-07-16 — Chất lượng & độ trễ AI triage
- `a24cddf`, `80d9ee4`, `96ea719` Thử nghiệm tắt/bật "thinking" của Gemini để cân bằng tốc độ vs
  chất lượng câu trả lời (quyết định cuối: giữ thinking bật theo phản hồi người dùng).
- `3daf04b`, `8e36490`, `ac3fdc0` Sửa lỗi AI hỏi lặp lại câu đã hỏi, giới hạn số câu hỏi/lượt.
- `ae40a6c` Sửa AI hiểu sai sinh lý bình thường theo tuổi/giới tính thành bệnh lý.
- `5d1f31a` Hiện ngày an toàn + khoảng dự đoán kỳ kinh tiếp theo trên lịch chu kỳ.
- `5ffa15d` Sửa lỗi mất đoạn giải thích của AI khi gọi tool `clarify()`.
- `7e7a3ee` Chặn ghi nhận ngày bắt đầu kỳ kinh trong tương lai (gây ra "ngày chu kỳ" âm).
- `60cfa5f` Bắt AI luôn ưu tiên dùng hồ sơ bệnh nhân làm căn cứ suy luận chính, không chỉ tra cứu
  khi cần.

### 2026-07-17 — Tài khoản demo, thiết kế lại hồ sơ, định dạng phản hồi
- `a46e81e` Seed 5 tài khoản demo với hồ sơ bệnh lý đa dạng (tuổi/giới tính/bệnh nền khác nhau)
  để demo AI suy luận theo hồ sơ mà không cần đăng ký thủ công.
- `32d9578` Thiết kế lại tab hồ sơ theo ảnh tham chiếu.
- `71f7cce` Bắt buộc AI trả về đúng 1 object JSON, cấm in chữ ngoài JSON envelope.

### 2026-07-18 — Đổi provider AI, RAG dữ liệu bệnh viện, đặt lịch khám bác sĩ
- `5446672` Nối tính năng nhận dạng giọng nói (speech-to-text) vào ô chat.
- `13bf9c9` Đổi provider AI mặc định sang Groq (Qwen3.6-27b), sửa 2 lỗi phát hiện khi test sống.
- `98424e8` Merge nhánh `develop` (data luật y tế, chính sách bệnh viện, dataset bác sĩ/lịch mock)
  vào `main`.
- `110267a` Tắt "thinking" của Qwen trên Groq để tránh cạn ngân sách token, thêm cơ chế khôi phục
  khi model trả tool-call bị lỗi định dạng.
- `3474372` Thêm 3 tool AI mới: `tra_gia` (tra bảng giá dịch vụ), `tra_cuu` (RAG quy trình/chính
  sách/luật khám chữa bệnh), `xem_lich_kham` (tìm bác sĩ + lịch trống) — dùng kỹ thuật trọng số
  IDF sau khi test sống phát hiện keyword-overlap thường bị từ phổ biến át mất kết quả đúng. Thêm
  API đặt lịch bác sĩ thật (`/doctors`, `/doctors/{id}/book`) và tính năng nhắc uống thuốc nhiều
  ngày/nhiều lần một ngày.
- `6a5578f` Thiết kế lại tab Lịch, thêm khối "Chỉ số sức khỏe" mô phỏng (nhịp tim/huyết áp cập
  nhật liên tục theo hồ sơ từng tài khoản), và toàn bộ luồng đặt lịch khám bác sĩ (tìm theo
  tên/cơ sở/khoa → trang chi tiết bác sĩ → chọn giờ → xác nhận).
- `d68778a` Đổi backend production sang Groq/Qwen sau khi phát hiện key Gemini trên Render bị lỗi
  (test sống qua API thật, không chỉ đọc log).

### 2026-07-18 (tối) — Thiết kế lại tab chu kỳ kinh nguyệt
- `7c45720` Thiết kế lại tab chu kỳ kinh nguyệt: thẻ số liệu, thanh tiến trình chu kỳ theo từng
  ngày, ô lịch tô màu theo giai đoạn (hành kinh/dễ thụ thai/rụng trứng/an toàn) thay vì chấm nhỏ.

## Ghi chú

- Các commit của `laiducanh26112004-debug` (Groq provider ban đầu, STT, mock data bác sĩ/lịch)
  **không nằm trong phiên Claude Code** ở trên nhưng có khả năng trùng với phiên Codex đã tìm thấy
  (cùng máy, cùng thư mục dự án, cùng khung thời gian 07-17 → 07-18) — cần thành viên đó xác nhận.
- Commit của `Luu Nhat Nam` (`c8893c8`, first-aid rule seed) không khớp với phiên AI nào tìm thấy
  trên máy này — nếu có dùng công cụ AI, cần thành viên đó tự bổ sung link/file log riêng.
- Commit đầu tiên (`d8607c0`, 2026-07-09) có trước thời điểm tạo cả 2 phiên trên (Claude Code từ
  2026-07-15, Codex từ 2026-07-17) nên không thuộc phạm vi bằng chứng ở đây.
