# Yên · Trợ lý y tế cá nhân

> Trợ lý phân loại triệu chứng — mô tả bằng ngôn ngữ tự nhiên, Yên xác nhận lại điều đã
> hiểu, hỏi thêm khi cần, rồi đưa ra **mức độ khẩn cấp + bước tiếp theo** kèm độ chắc
> chắn và lý do. Có tài khoản + hồ sơ sức khỏe (tuổi, giới tính, bệnh nền, dị ứng) để Yên
> nhớ mà không hỏi lại mỗi lần, cộng thêm lịch theo dõi sức khỏe (tài khoản nữ có thêm
> tab theo dõi chu kỳ kinh nguyệt). Ô chat hỗ trợ **nhập tiếng Việt bằng micro** qua module
> `backend/stt`. Lấy cảm hứng & cải tiến từ Ada Health (track Healthcare).

Prototype cho Day 06 — built với React + Vite + Framer Motion (frontend), FastAPI + SQLite (backend).

---

## Chạy thử

> ⚠️ Từ khi có tài khoản, **backend bắt buộc phải chạy** — đăng ký/đăng nhập gọi thẳng
> backend (SQLite), không có đường rơi về rule-based cho phần auth. AI trả lời (Groq/Qwen3)
> vẫn tự fallback rule-based engine nếu thiếu `GROQ_API_KEY`, nhưng riêng đăng nhập thì
> không. Luôn dùng `npm run dev:all` (chạy cả 2), đừng chỉ `npm run dev`.

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

Mở `http://localhost:5173` → màn hình landing → **Tạo tài khoản miễn phí** (chọn tuổi +
giới tính) → vào thẳng khu chat, hồ sơ được lưu để không phải khai lại lần sau.

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
├── App.jsx                      # router: Landing / Login / Signup / (App: Chat, Lịch)
├── context/AuthContext.jsx      # token + user + profile, persist localStorage
├── lib/
│   ├── api.js                   # client gọi backend (auth, profile, calendar, cycle)
│   ├── audioRecorder.js         # ghi micro trình duyệt thành PCM WAV
│   ├── liveSpeechRecognition.js # transcript tạm theo thời gian thực (Chrome/Edge)
│   └── triageEngine.js          # fallback rule-based + callRealModel() gọi backend LLM
├── pages/
│   ├── LandingPage.jsx          # trang giới thiệu (public)
│   ├── LoginPage.jsx / SignupPage.jsx   # đăng nhập / đăng ký (chọn tuổi + giới tính)
│   ├── ChatPage.jsx             # khu chat (== App.jsx cũ, giờ là 1 page trong router)
│   └── CalendarPage.jsx         # lịch sức khỏe + sub-tab chu kỳ kinh nguyệt (nếu nữ)
├── components/
│   ├── RequireAuth.jsx          # bảo vệ /app/*, redirect /dang-nhap nếu chưa đăng nhập
│   ├── TabNav.jsx                # tab Trò chuyện/Lịch + đăng xuất, dùng chung 2 page
│   ├── HealthCalendar.jsx        # lưới lịch tháng + form thêm mục
│   ├── CycleTracker.jsx          # tóm tắt dự đoán + lịch sử chu kỳ kinh nguyệt
│   ├── ProfileRail.jsx / TriageResult.jsx / Emergency.jsx / ... (như cũ)
└── index.css                     # design system (CSS variables, atmosphere, animations)

backend/
├── server.py                    # FastAPI: /triage, /auth/*, /profile, /calendar, /cycle
├── db.py                        # SQLite (accounts, hồ sơ, lịch, chu kỳ) — file tại backend/data/app.db
├── auth.py                      # hash mật khẩu (PBKDF2) + JWT session token
├── stt/                         # SpeechRecognition tiếng Việt, nhận WAV từ trình duyệt
└── artifacts/system_prompt.md   # hướng dẫn LLM dùng hồ sơ bệnh nhân khi có
```

---

## Tài khoản & hồ sơ sức khỏe

- Đăng ký cần **ngày sinh** (tự tính tuổi) + **giới tính** (nam/nữ); bệnh nền, dị ứng,
  thuốc đang dùng có thể bổ sung sau qua `PUT /profile`.
- Mỗi lượt chat gửi kèm `Authorization: Bearer <token>` — backend tự nạp hồ sơ vào context
  cho LLM (xem `_profile_context_message()` trong `server.py`), nên Yên **không hỏi lại**
  tuổi/giới tính/bệnh nền/dị ứng đã biết.
- **Tài khoản nữ tự động có thêm sub-tab "Chu kỳ kinh nguyệt"** trong mục Lịch — không hỏi
  bật/tắt, chỉ dựa vào `gender === 'nu'`. Ghi ngày bắt đầu kỳ kinh → hệ thống tự tính chu kỳ
  trung bình, đang ở ngày mấy, dự đoán kỳ tiếp theo — và số này cũng được đưa vào context
  chat nếu triệu chứng có thể liên quan (đau bụng dưới, ra máu bất thường...).
- Mật khẩu hash bằng PBKDF2-SHA256 (200k vòng), không lưu plaintext. Token là JWT 30 ngày.

### Tài khoản demo (đăng nhập thẳng, không cần đăng ký)

Backend tự seed 5 tài khoản demo (idempotent, chạy lại mỗi lần khởi động — xem
`backend/seed_demo.py`) với hồ sơ bệnh lý khác nhau để demo/QA việc AI dùng hồ sơ để suy
luận, không cần đăng ký + điền hồ sơ thủ công. Mật khẩu chung: **`Demo123456`**.

| Email | Hồ sơ | Minh hoạ cho |
|---|---|---|
| `demo1@yen.vn` | Nữ, 16 tuổi, đã có 1 mục chu kỳ kinh nguyệt | Tuổi dậy thì + tab Chu kỳ kinh nguyệt |
| `demo2@yen.vn` | Nam, 45 tuổi, đái tháo đường type 2, dùng Metformin | Tham chiếu bệnh nền mạn tính |
| `demo3@yen.vn` | Nữ, 30 tuổi, dị ứng đậu phộng + hải sản | Cảnh giác phản ứng dị ứng |
| `demo4@yen.vn` | Nam, 70 tuổi, cao huyết áp, dùng Amlodipine | Tham chiếu thuốc đang dùng + tuổi già |
| `demo5@yen.vn` | Nữ, 50 tuổi, không bệnh nền | Suy luận theo độ tuổi (tiền mãn kinh) |

---

## Công cụ & API

| Hạng mục | Dùng gì |
|---|---|
| Frontend | React 18 + Vite 5 + React Router 7 + Framer Motion |
| Backend | FastAPI + Uvicorn + SQLite (stdlib `sqlite3`, không ORM) |
| Auth | PBKDF2 password hash + JWT (PyJWT) |
| Fonts | Fraunces · Be Vietnam Pro · Spline Sans Mono (Google Fonts) |
| AI (mặc định) | Rule-based triage engine mô phỏng — `src/lib/triageEngine.js` |
| AI thật | **Qwen3-32B trên Groq** qua backend `backend/server.py` |

### API chính

| Route | Việc |
|---|---|
| `POST /auth/register`, `POST /auth/login` | Tài khoản → trả `{ token, user, profile }` |
| `GET/PUT /profile` | Đọc/sửa hồ sơ sức khỏe (auth) |
| `GET/POST/DELETE /calendar` | Lịch sức khỏe theo ngày (auth) |
| `GET/POST/DELETE /cycle` | Chu kỳ kinh nguyệt + dự đoán (auth) |
| `POST /stt/transcribe` | WAV từ micro → `{ text, language }` (auth) |
| `POST /triage` | Chat — `Authorization` tùy chọn, có thì nạp hồ sơ vào context |

### Chạy AI THẬT bằng Groq + Qwen3-32B (cho điểm "AI chạy thật trong ≥1 flow")

```bash
cd Yen/backend
cp .env.example .env    # điền GROQ_API_KEY — lấy tại https://console.groq.com/keys
```

- Khi có `GROQ_API_KEY`, toàn bộ hội thoại đi qua **Qwen3-32B trên Groq**; chỉnh sửa triệu chứng
  cũng gửi correction về backend đánh giá lại.
- Backend tắt / thiếu key / trả JSON hỏng → frontend **tự fallback rule-based engine** cho
  riêng phần AI trả lời (đăng nhập/tài khoản thì không có fallback — xem cảnh báo ở trên).
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
