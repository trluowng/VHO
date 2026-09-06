# Yên · Trợ lý y tế cá nhân

> Trợ lý phân loại triệu chứng — mô tả bằng ngôn ngữ tự nhiên, Yên xác nhận lại điều đã
> hiểu, hỏi thêm khi cần, rồi đưa ra **mức độ khẩn cấp + bước tiếp theo** kèm độ chắc
> chắn và lý do. Hồ sơ sức khỏe (tuổi, giới tính, bệnh nền, dị ứng) được lưu theo trình
> duyệt để Yên nhớ mà không hỏi lại mỗi lần; hồ sơ nữ có thêm
> tab theo dõi chu kỳ kinh nguyệt). Ô chat hỗ trợ **nhập tiếng Việt bằng micro** qua module
> `backend/stt`. Lấy cảm hứng & cải tiến từ Ada Health (track Healthcare).

Prototype cho Day 06 — built với React + Vite + Framer Motion (frontend), FastAPI + SQLite (backend).

---

## Sử dụng không cần đăng nhập

Người dùng mở ứng dụng và dùng ngay. Frontend tự tạo một `X-Client-ID` ngẫu nhiên, lưu trong
`localStorage` và gửi kèm các API cần dữ liệu cá nhân. Backend dùng mã này để tách hồ sơ, lịch
và chu kỳ giữa các trình duyệt; không thu thập mật khẩu và không có màn hình đăng ký/đăng nhập.

---

## Chạy thử

> **Backend phải chạy** để tải/lưu hồ sơ, lịch và chu kỳ. AI trả lời vẫn tự fallback về
> rule-based engine nếu thiếu API key. Dùng `npm run dev:all` để chạy cả frontend và backend.

```bash
# 1) Backend — cài deps + điền key
cd Yen/backend
pip install -r requirements.txt
cp .env.example .env                # điền GROQ_API_KEY (xem phần AI thật bên dưới)

# 2) Frontend — cài deps
cd ../frontend
npm install

# 3) Chạy cả 2 cùng lúc
npm run dev:all      # chạy `python -X utf8 server.py` (:8787) + `vite` (:5173) cùng lúc
```

Mở `http://localhost:5173` → màn hình landing → **Trò chuyện với Yên**. Không cần đăng nhập;
có thể cập nhật ngày sinh, giới tính và thông tin liên hệ trong tab **Hồ sơ**.

Trong ô chat, bấm nút **micro**, cho phép trình duyệt truy cập micro, nói tối đa 30 giây rồi
bấm lại để dừng. Trên Chrome/Edge, transcript tạm xuất hiện trực tiếp trong lúc đang nói;
khi dừng, backend `stt` xử lý WAV và thay bằng transcript cuối để người dùng kiểm tra trước
khi gửi. Trình duyệt không hỗ trợ nhận dạng trực tiếp vẫn dùng chế độ backend sau khi dừng.
Micro chỉ hoạt động trên `localhost` hoặc website HTTPS.

Build production: `npm run build` → `npm run preview` (chỉ build frontend; backend chạy
bằng `python server.py` như bình thường).

---

## 3 luồng demo (bấm thẳng các ví dụ ở màn hình chào)

| Đường đi | Nhập thử | Yên phản hồi |
|---|---|---|
| 🟡 **Happy** | `Tôi bị sốt 38.5 độ và đau họng 2 ngày nay` → bấm **Có** | Xác nhận triệu chứng → 1 câu hỏi → kết quả **Gặp bác sĩ trong 24h** (88% chắc chắn) + lý do + việc nên làm |
| 🟢 **Low-confidence** | `Tôi thấy mệt và hơi chóng mặt` → trả lời các câu hỏi | Nhận ra mô tả mơ hồ → giữ **Độ chắc chắn: Thấp**, liệt kê **thông tin còn thiếu**, khuyến nghị theo dõi tại nhà |
| 🔴 **Red flag** | `Tôi đau ngực và khó thở` | **Bypass toàn bộ flow** < 1s → màn hình đỏ **Gọi 115 ngay** + hướng dẫn trong lúc chờ |
| ↩️ **Correction** | (sau khi có kết quả) `thực ra tôi có bệnh nền tiểu đường` | Cập nhật hồ sơ, đánh giá lại và giải thích vì sao kết quả đổi |

Mọi kết quả luôn kèm disclaimer **"Đây không phải chẩn đoán y khoa"**.

---

## Thiết kế & kiến trúc

- **Aesthetic "Clarity Teal"** — nền giấy xanh ngọc lam nhạt, mực xanh than sâu, thương hiệu
  xanh dương/ngọc lam, tín hiệu triage xanh lá/hổ phách/đất nung. Font **Fraunces** (display
  serif) + **Be Vietnam Pro** (UI, hỗ trợ tiếng Việt đầy đủ) + **Spline Sans Mono** (nhãn).
  Tránh "AI slop".
- **Rail hồ sơ phiên** (trái): vòng tròn độ chắc chắn động, chip triệu chứng AI ghi nhận,
  thông tin còn thiếu, disclaimer — đúng yêu cầu "xác nhận lại điều AI đã hiểu" trong SPEC.
- **Khu chat** (phải): hội thoại, nút trả lời nhanh, kết quả triage in-thread, overlay
  khẩn cấp.

```
frontend/src/
├── App.jsx                      # router: Landing / Chat / Lịch / Đặt lịch / Hồ sơ
├── context/SessionContext.jsx   # mã phiên trình duyệt + hồ sơ, persist localStorage
├── lib/
│   ├── api.js                   # client gọi backend (profile, calendar, cycle)
│   ├── audioRecorder.js         # ghi micro trình duyệt thành PCM WAV
│   ├── liveSpeechRecognition.js # transcript tạm theo thời gian thực (Chrome/Edge)
│   └── triageEngine.js          # fallback rule-based + callRealModel() gọi backend LLM
├── pages/
│   ├── LandingPage.jsx          # trang giới thiệu (public)
│   ├── ChatPage.jsx             # khu chat (== App.jsx cũ, giờ là 1 page trong router)
│   └── CalendarPage.jsx         # lịch sức khỏe + sub-tab chu kỳ kinh nguyệt (nếu nữ)
├── components/
│   ├── TabNav.jsx                # điều hướng Trò chuyện/Lịch/Đặt lịch/Hồ sơ
│   ├── HealthCalendar.jsx        # lưới lịch tháng + form thêm mục
│   ├── CycleTracker.jsx          # tóm tắt dự đoán + lịch sử chu kỳ kinh nguyệt
│   ├── ProfileRail.jsx / TriageResult.jsx / Emergency.jsx / ... (như cũ)
└── index.css                     # design system (CSS variables, atmosphere, animations)

backend/
├── server.py                    # FastAPI: /triage, /profile, /calendar, /cycle
├── db.py                        # SQLite (phiên ẩn danh, hồ sơ, lịch, chu kỳ)
├── stt/                         # SpeechRecognition tiếng Việt, nhận WAV từ trình duyệt
└── artifacts/system_prompt.md   # hướng dẫn LLM dùng hồ sơ bệnh nhân khi có
```

---

## Phiên trình duyệt & hồ sơ sức khỏe

- Tab Hồ sơ cho phép nhập **ngày sinh** (tự tính tuổi), **giới tính** (nam/nữ), bệnh nền,
  dị ứng, thuốc đang dùng và thông tin liên hệ.
- Mỗi lượt chat gửi kèm `X-Client-ID` — backend tự nạp hồ sơ vào context
  cho LLM (xem `_profile_context_message()` trong `server.py`), nên Yên **không hỏi lại**
  tuổi/giới tính/bệnh nền/dị ứng đã biết.
- **Hồ sơ nữ tự động có thêm sub-tab "Chu kỳ kinh nguyệt"** trong mục Lịch — không hỏi
  bật/tắt, chỉ dựa vào `gender === 'nu'`. Ghi ngày bắt đầu kỳ kinh → hệ thống tự tính chu kỳ
  trung bình, đang ở ngày mấy, dự đoán kỳ tiếp theo — và số này cũng được đưa vào context
  chat nếu triệu chứng có thể liên quan (đau bụng dưới, ra máu bất thường...).
- Không có mật khẩu/JWT. Xoá dữ liệu website trong trình duyệt sẽ tạo một phiên mới và
  trình duyệt đó không còn liên kết với dữ liệu phiên cũ.

---

## Công cụ & API

| Hạng mục | Dùng gì |
|---|---|
| Frontend | React 18 + Vite 5 + React Router 7 + Framer Motion |
| Backend | FastAPI + Uvicorn + SQLite (stdlib `sqlite3`, không ORM) |
| Tách dữ liệu | `X-Client-ID` ngẫu nhiên, lưu trong `localStorage` |
| Fonts | Fraunces · Be Vietnam Pro · Spline Sans Mono (Google Fonts) |
| AI (mặc định) | Rule-based triage engine mô phỏng — `src/lib/triageEngine.js` |
| AI thật | **Qwen3-32B trên Groq** qua backend `backend/server.py` |

### API chính

| Route | Việc |
|---|---|
| `GET/PUT /profile` | Đọc/sửa hồ sơ sức khỏe theo `X-Client-ID` |
| `GET/POST/DELETE /calendar` | Lịch sức khỏe theo `X-Client-ID` |
| `GET/POST/DELETE /cycle` | Chu kỳ kinh nguyệt + dự đoán theo `X-Client-ID` |
| `POST /doctors/{id}/book` | Đặt lịch, lưu vào lịch và gửi email trong hồ sơ nếu có |
| `POST /stt/transcribe` | WAV từ micro → `{ text, language }` |
| `POST /triage` | Chat + nạp hồ sơ theo `X-Client-ID` vào context |

### Email xác nhận lịch khám

Backend gửi email xác nhận ngay sau khi đặt lịch thành công qua SMTP. Sao chép các biến
`SMTP_*` trong `backend/.env.example` sang `backend/.env`. Với Gmail, cấu hình thường dùng:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-16-character-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=Yên · sức khỏe
SMTP_USE_TLS=true
SMTP_USE_SSL=false
```

Hãy dùng **Google App Password**, không dùng mật khẩu đăng nhập Gmail. Nếu SMTP lỗi, lịch khám
vẫn được lưu và API trả `email_notification: "failed"`; khi chưa cấu hình SMTP, trạng thái là
`"disabled"`.

### Chạy AI THẬT bằng Groq + Qwen3-32B (cho điểm "AI chạy thật trong ≥1 flow")

```bash
cd Yen/backend
cp .env.example .env    # điền GROQ_API_KEY — lấy tại https://console.groq.com/keys
```

- Khi có `GROQ_API_KEY`, toàn bộ hội thoại đi qua **Qwen3-32B trên Groq**; chỉnh sửa triệu chứng
  cũng gửi correction về backend đánh giá lại.
- Backend tắt / thiếu key / trả JSON hỏng → frontend **tự fallback rule-based engine** cho
  phần AI trả lời; các tính năng lưu hồ sơ/lịch vẫn cần backend.
- Đổi provider/model qua `TRIAGE_PROVIDER` và `TRIAGE_MODEL` trong `backend/.env`.
  `.env.example` mặc định dùng `groq` + `qwen/qwen3-32b`; Gemini vẫn được hỗ trợ như
  provider thay thế.
- **Không commit `.env`** (đã gitignore) — chỉ commit `.env.example`. File DB
  `backend/data/app.db` cũng gitignore — mỗi máy có DB local riêng.

---

## Phân công

| Thành viên | Mã HV | Phần phụ trách |
|---|---|---|
| _(điền)_ | | Frontend / UI |
| _(điền)_ | | Triage engine / prompt |
| _(điền)_ | | Test 4 paths |
| _(điền)_ | | Demo script / repo |
| _(điền)_ | | Evidence / SPEC |

> Cập nhật bảng trên với mã học viên + họ tên thật của nhóm trước khi nộp.

## AI Log

Nhật ký sử dụng công cụ AI (bằng chứng phiên làm việc theo yêu cầu ban tổ chức) ở
[AI_LOG.md](AI_LOG.md). Nếu dùng công cụ AI khác ngoài Claude Code, bổ sung link/file phiên riêng
vào file đó trước khi nộp.
