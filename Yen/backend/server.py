"""
Yên — HTTP server (Trợ lý Bệnh viện Tim Hà Nội)
================================================
Cầu nối giữa frontend React và logic agent trong chat.py, cộng thêm tài
khoản người dùng + hồ sơ sức khỏe + lịch theo dõi sức khỏe.

- POST /triage              body: { history, message }, header Authorization tùy chọn
                             trả về: { events, profile }
- POST /stt/transcribe       body: audio/wav, header Authorization bắt buộc
                             trả về: { text, language }
- POST /tts                  body: { text }, header Authorization bắt buộc
                             trả về: audio/mpeg (MP3) để trình duyệt tự phát
- GET  /health               kiểm tra server
- POST /auth/register        { email, password, age, gender } -> { token, user, profile }
- POST /auth/login           { email, password } -> { token, user, profile }
- GET  /profile               (auth) -> HealthProfile
- PUT  /profile               (auth) -> cập nhật HealthProfile
- GET  /calendar?month=YYYY-MM  (auth) -> danh sách lịch sức khỏe
- POST /calendar               (auth) -> thêm mục lịch
- DELETE /calendar/{id}        (auth)
- GET  /cycle                  (auth) -> danh sách chu kỳ + dự đoán
- POST /cycle                  (auth) -> thêm ngày bắt đầu kỳ kinh
- DELETE /cycle/{id}           (auth)
- GET  /doctors?query=&campus=&specialty=   (auth) -> danh sách bác sĩ + 2 lịch trống gần nhất
- GET  /doctors/{id}/schedule                (auth) -> toàn bộ lịch trống của 1 bác sĩ

Chạy:
    cd Yen/backend
    python server.py                    # mặc định http://localhost:8787

Rồi ở frontend (Yen/frontend/.env):  VITE_TRIAGE_API_URL=http://localhost:8787/triage
"""
from __future__ import annotations

import io
import json
import logging
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

import db
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from tools._shared import fold_text
from auth import create_token, hash_password, verify_password, verify_token
from email_service import AppointmentEmail, AppointmentEmailService

# Import the core agent loop and helpers from chat.py
from chat import run_model_tool_loop, trim_history, write_transcript, safe_slug, now_iso
from versioning import artifact_version_dict, build_artifact_version
from seed_demo import seed_demo_accounts
from artifacts.skills import load_skills, build_skills_section
from stt import (
    InvalidAudioError,
    NoSpeechRecognizedError,
    SpeechRecognizer,
    SpeechServiceError,
)

# Conversation memory: live turns in RAM; on disconnect, persist with 1h TTL and
# embed each (user, assistant) pair into a FAISS vector store (bge-m3, k=1 retrieval).
from memory import default as get_memory_manager


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
ARTIFACTS_DIR = ROOT / "artifacts"
load_lab_env(ROOT)
db.init_db()
seed_demo_accounts()

PROVIDER_NAME = os.getenv("TRIAGE_PROVIDER", "gemini")
MODEL = os.getenv("TRIAGE_MODEL", None)          # None → provider's default_model
HISTORY_WINDOW = int(os.getenv("TRIAGE_HISTORY_WINDOW", "5"))
MAX_TOOL_ROUNDS = int(os.getenv("TRIAGE_MAX_TOOL_ROUNDS", "4"))
PORT = int(os.getenv("PORT", os.getenv("TRIAGE_PORT", "8787")))
STT_MAX_AUDIO_BYTES = int(os.getenv("STT_MAX_AUDIO_BYTES", str(8 * 1024 * 1024)))
EMAIL_SERVICE = AppointmentEmailService.from_env()
LOGGER = logging.getLogger(__name__)

SYSTEM_PROMPT = (ARTIFACTS_DIR / "system_prompt.md").read_text(encoding="utf-8")
# Skills are task-specific markdown instructions layered on top of the base
# persona so the LLM follows them (e.g. phân khoa triệu chứng). Built once at
# boot; falls back to the base prompt if the skills folder is empty/missing.
SKILLS_DIR = ARTIFACTS_DIR / "skills"
SYSTEM_PROMPT = SYSTEM_PROMPT.rstrip() + "\n\n" + build_skills_section(load_skills(SKILLS_DIR))
TOOL_DECLARATIONS = load_tool_declarations(ARTIFACTS_DIR / "tools.yaml")
# Triage cần "tra_gia" (tra bảng giá), "tra_cuu" (RAG quy trình hành chính/chính
# sách/luật KBCB), và "xem_lich_kham" (tìm bác sĩ theo chuyên khoa + lịch trống).
# lookup/fetch/format là tool nghiên cứu web sót lại từ template gốc -- không
# cần cho tư vấn triệu chứng, và mỗi lần model gọi thêm 1 vòng round-trip nữa
# (chậm hẳn), nên bỏ khỏi danh sách tool đưa cho model.
# "clarify" CŨNG bị bỏ có chủ đích: hệ thống JSON schema (xem "ĐỊNH DẠNG TRẢ VỀ"
# trong system_prompt.md) đã có event "question" để hỏi lại khách, đi kèm luôn
# "profile" (symptoms/facts) trong CÙNG response. Khi model được cấp cả 2 lựa
# chọn, nó hay gọi tool "clarify" thay vì trả JSON -- nhưng nhánh xử lý clarify
# trong chat.py (status "waiting_for_user") chỉ trả text câu hỏi thô, KHÔNG có
# profile, nên symptoms/facts không bao giờ được cập nhật khi model chọn nhánh
# đó (xác nhận qua live test). Bỏ "clarify" buộc model luôn đi qua nhánh JSON
# đầy đủ.
TRIAGE_TOOL_NAMES = {"tra_gia", "tra_cuu", "xem_lich_kham"}
OPENAI_TOOLS = [t for t in to_openai_tools(TOOL_DECLARATIONS) if t["function"]["name"] in TRIAGE_TOOL_NAMES]
PROVIDER = make_provider(PROVIDER_NAME)
SELECTED_MODEL = MODEL or getattr(PROVIDER, "default_model", None)

TRANSCRIPTS_DIR = ROOT / "transcripts"
VERSION = os.getenv("TRIAGE_VERSION", "server")

GENDERS = {"nam", "nu"}

app = FastAPI(title="Yên Triage Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _bearer_user_id(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return verify_token(authorization.removeprefix("Bearer ").strip())


def _require_user_id(authorization: str | None = Header(None)) -> str:
    user_id = _bearer_user_id(authorization)
    if not user_id or not db.get_user_by_id(user_id):
        raise HTTPException(status_code=401, detail="unauthorized")
    return user_id


def _user_public(row) -> dict:
    return {"id": row["id"], "email": row["email"], "created_at": row["created_at"]}


# ---------------------------------------------------------------------------
# Triage helpers (unchanged behaviour from the previous stdlib server)
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict | None:
    """Try to pull a JSON object out of a freeform string."""
    if not text:
        return None
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start: end + 1])
        except Exception:
            return None
    return None


def _profile_context_message(user_id: str) -> dict | None:
    """Build a system message summarizing the patient's saved health profile,
    so the model doesn't ask again for facts it already knows (README mục 1.1)."""
    profile = db.get_profile(user_id)
    if not profile:
        return None

    parts = []
    if profile.get("age") is not None:
        parts.append(f"Tuổi: {profile['age']}")
    gender_label = {"nam": "Nam", "nu": "Nữ"}.get(profile.get("gender") or "")
    if gender_label:
        parts.append(f"Giới tính: {gender_label}")
    if profile.get("chronic_conditions"):
        parts.append("Bệnh nền: " + ", ".join(profile["chronic_conditions"]))
    if profile.get("allergies"):
        parts.append("Dị ứng: " + ", ".join(profile["allergies"]))
    if profile.get("medications"):
        parts.append("Thuốc đang dùng: " + ", ".join(profile["medications"]))

    if profile.get("gender") == "nu":
        entries = db.list_cycle_entries(user_id)
        if entries:
            try:
                last_start = date.fromisoformat(entries[0]["period_start_date"])
                cycle_day = (date.today() - last_start).days + 1
                if 0 < cycle_day <= 60:
                    parts.append(f"Chu kỳ kinh nguyệt: đang ở ngày {cycle_day} (tính từ lần kinh gần nhất)")
            except ValueError:
                pass

    if not parts:
        return None

    return {
        "role": "system",
        "content": (
            "HỒ SƠ BỆNH NHÂN (đã biết từ tài khoản — KHÔNG hỏi lại các mục này trừ khi "
            "cần làm rõ thêm chi tiết):\n" + "\n".join(f"- {p}" for p in parts)
        ),
    }


def _build_messages(history: list[dict], message: str, user_id: str | None) -> list[dict]:
    flat: list[dict[str, str]] = []
    for turn in history or []:
        role = turn.get("role")
        text = (turn.get("text") or "").strip()
        if not text:
            continue
        flat.append({
            "role": "assistant" if role == "ai" else "user",
            "content": text,
        })

    # Không đặt trần cứng cho số câu hỏi (đã bỏ theo yêu cầu) — việc dừng hỏi/kết luận
    # hoàn toàn dựa vào độ tin cậy và "còn câu hỏi mới hữu ích hay không", theo hướng dẫn
    # trong system_prompt.md; luật không-lặp-câu-hỏi cũng nằm ở đó để chặn hỏi lan man.
    trimmed = trim_history(flat, HISTORY_WINDOW)

    today = date.today()
    tomorrow = date.fromordinal(today.toordinal() + 1)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": (
                "NGÀY HỆ THỐNG: hôm nay là "
                f"{today.isoformat()}; ngày mai là {tomorrow.isoformat()}. "
                "Khi khách nói ngày tương đối như 'mai', 'sáng mai', hãy quy đổi sang YYYY-MM-DD "
                "trước khi gọi tool xem_lich_kham."
            ),
        },
    ]
    if user_id:
        profile_msg = _profile_context_message(user_id)
        if profile_msg:
            messages.append(profile_msg)
    messages.extend(trimmed)
    messages.append({"role": "user", "content": (message or "").strip()})
    return messages


def _normalize_profile(profile: dict) -> dict:
    """Ensure minimum profile keys so the frontend never crashes."""
    profile.setdefault("stage", "questioning")
    profile.setdefault("symptoms", [])
    profile.setdefault("confidence", 0)
    profile.setdefault("confTier", "none")
    profile.setdefault("missing", [])
    profile.setdefault("facts", {})
    return profile


# Last known-good profile per session, for when the model breaks the mandatory JSON
# contract mid-conversation (seen live on Groq/Qwen deep in multi-round tool-calling —
# it occasionally answers in plain prose instead of the JSON schema). Without this, the
# fallback below used to wipe profile.symptoms/facts back to empty and guess a stage,
# silently discarding everything gathered in earlier turns.
_LAST_PROFILE: dict[str, dict] = {}
_LAST_BOOKING_OPTIONS: dict[str, list[dict]] = {}


def _booking_options_from_tool_events(tool_events: list[dict[str, Any]]) -> list[dict]:
    options: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for event in tool_events or []:
        if event.get("tool") != "xem_lich_kham":
            continue
        result = event.get("result") or {}
        if not isinstance(result, dict):
            continue
        for item in result.get("items") or []:
            doctor_id = item.get("ma_bac_si")
            if not doctor_id:
                continue
            for slot in item.get("lich_trong") or []:
                visit_date = slot.get("ngay")
                time_slot = slot.get("khung_gio")
                if not visit_date or not time_slot:
                    continue
                key = (doctor_id, visit_date, time_slot)
                if key in seen:
                    continue
                seen.add(key)
                options.append({
                    "doctor_id": doctor_id,
                    "doctor_name": item.get("bac_si"),
                    "specialty": item.get("chuyen_khoa"),
                    "visit_date": visit_date,
                    "time_slot": time_slot,
                    "campus": slot.get("co_so"),
                    "location": slot.get("khoa_phong"),
                })
    return options[:6]


def _looks_like_booking_confirmation(text: str) -> bool:
    folded = fold_text(text or "")
    if not folded:
        return False
    positive = ("chot", "xac nhan", "dat", "book", "ok", "dong y", "lay", "chon")
    exploratory = ("tim", "xem", "goi y", "liet ke", "co gi")
    return any(word in folded for word in positive) and not any(word in folded for word in exploratory)


def _pick_booking_option(text: str, options: list[dict]) -> dict | None:
    if not options:
        return None
    folded = fold_text(text or "")
    ordinal_map = {
        "dau tien": 0, "thu nhat": 0, "so 1": 0, "1": 0,
        "thu hai": 1, "so 2": 1, "2": 1,
        "thu ba": 2, "so 3": 2, "3": 2,
    }
    for marker, index in ordinal_map.items():
        if marker in folded and index < len(options):
            return options[index]
    for option in options:
        doctor_name = (option.get("doctor_name") or "").split("(")[0].strip()
        if doctor_name and fold_text(doctor_name) in folded:
            return option
    return options[0]


def _booking_error_message(detail: str | None) -> str:
    labels = {
        "slot_already_booked": "Khung giờ này vừa có người đặt trước bạn. Mình chưa chốt lịch được, bạn chọn khung giờ khác trong thẻ lịch nhé.",
        "slot_not_found": "Khung giờ này không còn tồn tại trong lịch trống. Mình chưa chốt lịch được, bạn chọn lại giúp mình nhé.",
        "doctor_not_found": "Mình không còn tìm thấy bác sĩ này trong danh sách hiện tại, nên chưa chốt lịch được.",
    }
    return labels.get(detail or "", "Mình chưa chốt lịch được vì có lỗi khi lưu lịch. Bạn thử chọn lại khung giờ nhé.")


def _agent_result_to_response(result: dict, session_id: str) -> dict:
    booking_options = _booking_options_from_tool_events(result.get("tool_events") or [])
    if booking_options:
        _LAST_BOOKING_OPTIONS[session_id] = booking_options

    assistant_text = result.get("assistant_text", "")

    parsed = _extract_json(assistant_text)
    if parsed and "events" in parsed:
        events = parsed["events"] if isinstance(parsed["events"], list) else []
        if booking_options:
            events.append({"type": "booking_options", "options": booking_options})
        profile = _normalize_profile(
            parsed.get("profile") if isinstance(parsed.get("profile"), dict) else {}
        )
        _LAST_PROFILE[session_id] = profile
        return {"events": events, "profile": profile}

    # Model didn't return valid JSON this round -- carry forward the last profile we
    # actually parsed for this session (nothing about the tracked symptoms/stage changed,
    # the model just failed to restate it), rather than resetting to a bare default and
    # mislabeling stage as "done" when the patient may still be mid-questioning.
    events: list[dict] = [{"type": "message", "text": assistant_text, "confirm": False}]
    profile = _LAST_PROFILE.get(session_id)
    profile = dict(profile) if profile else _normalize_profile({"stage": "questioning"})
    if booking_options:
        events.append({"type": "booking_options", "options": booking_options})
    return {"events": events, "profile": profile}


def _session_id(payload: dict, user_id: str | None) -> str:
    """Stable session key: explicit session_id > user_id > anonymous singleton."""
    sid = payload.get("session_id")
    if sid:
        return str(sid)
    if user_id:
        return f"user_{user_id}"
    return "anon"


def triage(payload: dict, user_id: str | None) -> dict:
    # Nếu client bật giọng nói (use_voice), dùng STT để lấy đầu vào thay vì text.
    use_voice = bool(payload.get("use_voice"))
    message = payload.get("message", "")
    if use_voice and not message:
        try:
            from stt import speak_input
            message = (speak_input() or "").strip()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"voice_input_failed: {exc}") from exc

    session_id = _session_id(payload, user_id)
    try:
        chat_booking = _maybe_book_from_chat_confirmation(message, session_id, user_id)
    except HTTPException as exc:
        return {
            "events": [{"type": "message", "text": _booking_error_message(str(exc.detail)), "confirm": False}],
            "profile": dict(_LAST_PROFILE.get(session_id) or _normalize_profile({"stage": "done"})),
        }
    if chat_booking:
        return chat_booking

    # Lấy lại 1 cặp hội thoại gần nhất từ vector store (bge-m3, k=1, không rerank).
    # Chỉ là gợi nhớ tham khảo (không bắt buộc) -- lỗi ở đây (model embedding quá nặng
    # cho RAM free-tier, tải model lần đầu chậm, v.v.) không được làm hỏng cả lượt
    # triage; bỏ qua gợi nhớ và tiếp tục bình thường thay vì trả lỗi 500.
    memory = get_memory_manager()
    try:
        past = memory.retrieve(session_id, message, k=1)
    except Exception:
        LOGGER.exception("memory.retrieve failed, continuing without recall context")
        past = []
    if past:
        recalled = past[0]
        recall_ctx = (
            "\n\n# HỘI THOẠI LIÊN QUAN ĐÃ LƯU (gợi nhớ từ bộ nhớ, chỉ để tham khảo):\n"
            f"- Khách: {recalled.get('user', '')}\n"
            f"- Yên: {recalled.get('assistant', '')}"
        )
    else:
        recall_ctx = ""
    messages = _build_messages(payload.get("history", []), message, user_id)
    if recall_ctx:
        messages.append({"role": "system", "content": recall_ctx})

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = "_".join([safe_slug(VERSION), safe_slug(PROVIDER_NAME), timestamp])
    transcript_path = TRANSCRIPTS_DIR / f"{transcript_id}.transcript.json"

    transcript = {
        "transcript_id": transcript_id,
        "provider": PROVIDER_NAME,
        "model": SELECTED_MODEL,
        "system_prompt": str(ARTIFACTS_DIR / "system_prompt.md"),
        "tools": str(ARTIFACTS_DIR / "tools.yaml"),
        "history_window": HISTORY_WINDOW,
        "max_tool_rounds": MAX_TOOL_ROUNDS,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }

    turn_record = {
        "turn_index": 1,
        "started_at": now_iso(),
        "user": message,
        "history_length": len(payload.get("history", [])),
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }

    result = run_model_tool_loop(
        provider=PROVIDER,
        messages=messages,
        tools=OPENAI_TOOLS,
        model=SELECTED_MODEL,
        max_tool_rounds=MAX_TOOL_ROUNDS,
    )
    turn_record.update(result)
    turn_record["ended_at"] = now_iso()
    transcript["turns"].append(turn_record)
    write_transcript(transcript_path, transcript)

    # Lưu cặp (user, assistant) vào bộ nhớ hội thoại (chỉ RAM, chưa ghi đĩa). Chạy SAU KHI
    # đã có câu trả lời thật -- lỗi ở đây không được nuốt mất câu trả lời vừa tạo được.
    assistant_text = result.get("assistant_text", "")
    if assistant_text:
        try:
            memory.record_turn(session_id, message, assistant_text)
        except Exception:
            LOGGER.exception("memory.record_turn failed, response still returned to client")

    return _agent_result_to_response(result, session_id)


@app.post("/triage/end")
def triage_end_route(payload: dict = Body(...), authorization: str | None = Header(None)) -> dict:
    """Client gọi khi user rời đi / mất kết nối: lưu conversation (TTL 1h) + embed vào vector store."""
    user_id = _bearer_user_id(authorization)
    session_id = _session_id(payload, user_id)
    try:
        summary = get_memory_manager().end_session(session_id)
        return {"ok": True, "session_id": session_id, **summary}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


# ---------------------------------------------------------------------------
# Routes — health & triage
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {"ok": True, "provider": PROVIDER_NAME, "model": SELECTED_MODEL, "port": PORT}


@app.post("/stt/transcribe")
def transcribe_speech(
    audio: bytes = Body(..., media_type="audio/wav"),
    authorization: str | None = Header(None),
) -> dict:
    """Convert a short browser-recorded WAV clip to Vietnamese text."""
    _require_user_id(authorization)

    if not audio:
        raise HTTPException(status_code=400, detail="empty_audio")
    if len(audio) > STT_MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="audio_too_large")

    try:
        text = SpeechRecognizer().recognize_wav_bytes(audio)
    except InvalidAudioError as exc:
        raise HTTPException(status_code=400, detail="invalid_audio") from exc
    except NoSpeechRecognizedError as exc:
        raise HTTPException(status_code=422, detail="no_speech") from exc
    except SpeechServiceError as exc:
        raise HTTPException(status_code=502, detail="stt_service_unavailable") from exc

    return {"text": text, "language": "vi-VN"}


TTS_MAX_CHARS = 2000


@app.post("/tts")
def synthesize_speech(payload: dict = Body(...), authorization: str | None = Header(None)) -> Response:
    """Sinh giọng đọc tiếng Việt cho 1 đoạn text, trả về audio/mpeg để trình duyệt tự phát.

    Không dùng backend/stt/speaker.py (module đó phát âm thanh bằng pygame.mixer trên
    MÁY CHẠY SERVER -- vô dụng khi server chạy trên cloud vì không ai nghe được, và mỗi
    lần "phát" sẽ chặn cả request thêm vài giây). gTTS.write_to_fp() sinh MP3 thẳng vào
    bộ nhớ rồi trả về qua HTTP, để trình duyệt phát bằng thẻ <audio> phía client.
    """
    _require_user_id(authorization)
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="empty_text")
    if len(text) > TTS_MAX_CHARS:
        raise HTTPException(status_code=413, detail="text_too_long")

    try:
        from gtts import gTTS
        buffer = io.BytesIO()
        gTTS(text=text, lang="vi").write_to_fp(buffer)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"tts_service_unavailable: {exc}") from exc

    return Response(content=buffer.getvalue(), media_type="audio/mpeg")


@app.post("/triage")
def triage_route(payload: dict = Body(...), authorization: str | None = Header(None)) -> dict:
    user_id = _bearer_user_id(authorization)
    try:
        return triage(payload, user_id)
    except Exception as exc:
        # Frontend falls back to the rule-based engine on 500.
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


# ---------------------------------------------------------------------------
# Routes — auth
# ---------------------------------------------------------------------------

@app.post("/auth/register")
def register(payload: dict = Body(...)) -> dict:
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    age = payload.get("age")
    gender = payload.get("gender")

    if "@" not in email:
        raise HTTPException(status_code=400, detail="invalid_email")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="password_too_short")
    if gender not in GENDERS:
        raise HTTPException(status_code=400, detail="invalid_gender")
    if not isinstance(age, int) or not (0 < age < 120):
        raise HTTPException(status_code=400, detail="invalid_age")
    if db.get_user_by_email(email):
        raise HTTPException(status_code=409, detail="email_taken")

    password_hash, salt = hash_password(password)
    now = now_iso()
    user_id = db.create_user(email, password_hash, salt, now)
    db.create_profile(user_id, age, gender, now)

    token = create_token(user_id)
    return {"token": token, "user": {"id": user_id, "email": email, "created_at": now}, "profile": db.get_profile(user_id)}


@app.post("/auth/login")
def login(payload: dict = Body(...)) -> dict:
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    row = db.get_user_by_email(email)
    if not row or not verify_password(password, row["password_hash"], row["password_salt"]):
        raise HTTPException(status_code=401, detail="invalid_credentials")

    token = create_token(row["id"])
    return {"token": token, "user": _user_public(row), "profile": db.get_profile(row["id"])}


# ---------------------------------------------------------------------------
# Routes — health profile
# ---------------------------------------------------------------------------

@app.get("/profile")
def get_profile(authorization: str | None = Header(None)) -> dict:
    user_id = _require_user_id(authorization)
    profile = db.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="profile_not_found")
    return profile


@app.put("/profile")
def put_profile(payload: dict = Body(...), authorization: str | None = Header(None)) -> dict:
    user_id = _require_user_id(authorization)
    updates: dict[str, Any] = {}

    if "gender" in payload:
        if payload["gender"] not in GENDERS:
            raise HTTPException(status_code=400, detail="invalid_gender")
        updates["gender"] = payload["gender"]
    if "age" in payload:
        age = payload["age"]
        if not isinstance(age, int) or not (0 < age < 120):
            raise HTTPException(status_code=400, detail="invalid_age")
        updates["age"] = age
    for key in ("chronic_conditions", "allergies", "medications"):
        if key in payload:
            value = payload[key]
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                raise HTTPException(status_code=400, detail=f"invalid_{key}")
            updates[key] = value
    for key in db.PROFILE_TEXT_FIELDS:
        if key in payload:
            value = payload[key]
            if value is not None and not isinstance(value, str):
                raise HTTPException(status_code=400, detail=f"invalid_{key}")
            updates[key] = (value or "").strip() or None

    db.update_profile(user_id, updates, now_iso())
    return db.get_profile(user_id)


# ---------------------------------------------------------------------------
# Routes — health calendar
# ---------------------------------------------------------------------------

CALENDAR_TYPES = {"kham_benh", "xet_nghiem", "thuoc", "tiem_chung", "khac"}
TIME_RE = re.compile(r"\d{2}:\d{2}")
TIME_SLOT_RE = re.compile(r"\d{2}:\d{2}-\d{2}:\d{2}")


@app.get("/calendar")
def list_calendar(month: str | None = None, authorization: str | None = Header(None)) -> dict:
    user_id = _require_user_id(authorization)
    if month and not re.fullmatch(r"\d{4}-\d{2}", month):
        raise HTTPException(status_code=400, detail="invalid_month")
    return {"entries": db.list_calendar_entries(user_id, month)}


@app.post("/calendar")
def create_calendar_entry(payload: dict = Body(...), authorization: str | None = Header(None)) -> dict:
    user_id = _require_user_id(authorization)
    entry_date = payload.get("entry_date")
    entry_type = payload.get("type", "khac")
    title = (payload.get("title") or "").strip()
    time_start = (payload.get("time_start") or "").strip() or None
    time_end = (payload.get("time_end") or "").strip() or None
    doctor = (payload.get("doctor") or "").strip() or None
    location = (payload.get("location") or "").strip() or None
    date_end = (payload.get("date_end") or "").strip() or None
    times = [t.strip() for t in (payload.get("times") or []) if t and t.strip()]

    if not entry_date:
        raise HTTPException(status_code=400, detail="entry_date_required")
    try:
        date.fromisoformat(entry_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_entry_date")
    if entry_type not in CALENDAR_TYPES:
        raise HTTPException(status_code=400, detail="invalid_type")
    if not title:
        raise HTTPException(status_code=400, detail="title_required")
    if time_start and not TIME_RE.fullmatch(time_start):
        raise HTTPException(status_code=400, detail="invalid_time_start")
    if time_end and not TIME_RE.fullmatch(time_end):
        raise HTTPException(status_code=400, detail="invalid_time_end")

    if entry_type == "thuoc":
        # Nhắc uống thuốc là 1 đợt lặp lại (từ ngày -> đến ngày, N lần/ngày),
        # khác với các loại còn lại (1 sự kiện đúng 1 ngày, 1 khung giờ).
        if not times:
            raise HTTPException(status_code=400, detail="times_required")
        if any(not TIME_RE.fullmatch(t) for t in times):
            raise HTTPException(status_code=400, detail="invalid_times")
        if date_end:
            try:
                date.fromisoformat(date_end)
            except ValueError:
                raise HTTPException(status_code=400, detail="invalid_date_end")
            if date_end < entry_date:
                raise HTTPException(status_code=400, detail="date_end_before_entry_date")
        else:
            date_end = entry_date
    else:
        date_end = None
        times = None

    entry_id = db.add_calendar_entry(
        user_id, entry_date, entry_type, title, payload.get("note"), now_iso(),
        time_start=time_start, time_end=time_end, doctor=doctor, location=location,
        date_end=date_end, times=times,
    )
    return {"id": entry_id}


@app.delete("/calendar/{entry_id}")
def delete_calendar_entry(entry_id: str, authorization: str | None = Header(None)) -> dict:
    user_id = _require_user_id(authorization)
    if not db.delete_calendar_entry(user_id, entry_id):
        raise HTTPException(status_code=404, detail="not_found")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Routes — doctor directory / booking search (tab "Đặt lịch khám")
#
# Tách riêng khỏi tool xem_lich_kham dùng cho AI (search mờ theo từ khóa) --
# ở đây khách tự gõ tên + chọn lọc cơ sở/khoa chính xác trên giao diện, nên
# cần match rõ ràng (substring theo tên, exact theo cơ sở/khoa) thay vì
# scoring mờ, và trả về TOÀN BỘ danh sách phù hợp (không giới hạn top-N).
# ---------------------------------------------------------------------------

_DOCTORS_PATH = ROOT / "data" / "doctors.json"
_SCHEDULE_SLOTS_PATH = ROOT / "data" / "schedule_slots.json"
_doctors_cache: list[dict] | None = None
_schedule_by_doctor_cache: dict[str, list[dict]] | None = None


def _load_doctors() -> list[dict]:
    global _doctors_cache
    if _doctors_cache is None:
        _doctors_cache = json.loads(_DOCTORS_PATH.read_text(encoding="utf-8"))
    return _doctors_cache


def _load_schedule_by_doctor() -> dict[str, list[dict]]:
    global _schedule_by_doctor_cache
    if _schedule_by_doctor_cache is None:
        slots = json.loads(_SCHEDULE_SLOTS_PATH.read_text(encoding="utf-8"))
        by_doctor: dict[str, list[dict]] = {}
        for slot in slots:
            if slot.get("status") != "available":
                continue
            by_doctor.setdefault(slot["id_doctor"], []).append(slot)
        for doctor_slots in by_doctor.values():
            doctor_slots.sort(key=lambda s: (s["visit_date"], s["time_slot"]))
        _schedule_by_doctor_cache = by_doctor
    return _schedule_by_doctor_cache


def _open_slots(doctor_id: str) -> list[dict]:
    """Lịch trống thật của 1 bác sĩ = có trong data mock (status available) VÀ
    chưa bị ai đặt qua app (calendar_entries.time_slot) -- 1 khung giờ đã đặt
    thì biến mất khỏi danh sách trống cho MỌI người dùng, không chỉ người đã đặt."""
    booked = db.list_booked_slots(doctor_id)
    return [
        s for s in _load_schedule_by_doctor().get(doctor_id, [])
        if (s["visit_date"], s["time_slot"]) not in booked
    ]


def _book_doctor_slot_for_user(user_id: str, doctor_id: str, visit_date: str, time_slot: str) -> dict:
    doctor = next((d for d in _load_doctors() if d["id_doctor"] == doctor_id), None)
    if not doctor:
        raise HTTPException(status_code=404, detail="doctor_not_found")

    visit_date = (visit_date or "").strip()
    time_slot = (time_slot or "").strip()
    try:
        date.fromisoformat(visit_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_visit_date")
    if not TIME_SLOT_RE.fullmatch(time_slot):
        raise HTTPException(status_code=400, detail="invalid_time_slot")

    matching_slot = next(
        (s for s in _load_schedule_by_doctor().get(doctor_id, [])
         if s["visit_date"] == visit_date and s["time_slot"] == time_slot),
        None,
    )
    if not matching_slot:
        raise HTTPException(status_code=404, detail="slot_not_found")
    if db.find_booking(doctor_id, visit_date, time_slot):
        raise HTTPException(status_code=409, detail="slot_already_booked")

    time_start, _, time_end = time_slot.partition("-")
    location = f"{matching_slot['campus']} - {doctor['department']} - {matching_slot['room']}"
    entry_id = db.add_calendar_entry(
        user_id, visit_date, "kham_benh", f"Khám {doctor['specialty']}",
        f"Đặt lịch qua Yên với {doctor['full_name']}.", now_iso(),
        time_start=time_start, time_end=time_end,
        doctor=f"{doctor['full_name']} ({doctor['degree']})",
        location=location,
        doctor_id=doctor_id, time_slot=time_slot,
    )

    email_notification = "disabled"
    user = db.get_user_by_id(user_id)
    if EMAIL_SERVICE.configured and user:
        profile = db.get_profile(user_id) or {}
        try:
            EMAIL_SERVICE.send_confirmation(AppointmentEmail(
                recipient_email=user["email"],
                patient_name=profile.get("full_name") or "Quý khách",
                doctor_name=doctor["full_name"],
                doctor_degree=doctor["degree"],
                specialty=doctor["specialty"],
                visit_date=visit_date,
                time_slot=time_slot,
                location=location,
                appointment_id=entry_id,
            ))
            email_notification = "sent"
        except Exception:
            # Lịch hẹn đã được lưu; sự cố SMTP không được làm người dùng mất lịch.
            email_notification = "failed"
            LOGGER.exception("Could not send appointment email for booking %s", entry_id)

    return {
        "id": entry_id,
        "email_notification": email_notification,
        "doctor": {
            "id_doctor": doctor["id_doctor"],
            "full_name": doctor["full_name"],
            "degree": doctor["degree"],
            "specialty": doctor["specialty"],
            "department": doctor["department"],
        },
        "visit_date": visit_date,
        "time_slot": time_slot,
        "location": location,
    }


def _maybe_book_from_chat_confirmation(message: str, session_id: str, user_id: str | None) -> dict | None:
    if not user_id or not _looks_like_booking_confirmation(message):
        return None
    option = _pick_booking_option(message, _LAST_BOOKING_OPTIONS.get(session_id, []))
    if not option:
        return None

    booking = _book_doctor_slot_for_user(
        user_id,
        option["doctor_id"],
        option["visit_date"],
        option["time_slot"],
    )
    _LAST_BOOKING_OPTIONS.pop(session_id, None)

    doctor = booking["doctor"]
    email_text = {
        "sent": "Email xác nhận đã được gửi tới email tài khoản của bạn.",
        "failed": "Chưa gửi được email xác nhận, nhưng lịch khám đã được lưu.",
        "disabled": "Chưa cấu hình SMTP nên chưa gửi email, nhưng lịch khám đã được lưu.",
    }.get(booking["email_notification"], "")
    text = (
        f"Mình đã chốt lịch khám {doctor['specialty']} với {doctor['full_name']} "
        f"vào {booking['visit_date']} lúc {booking['time_slot']}. "
        "Lịch này đã xuất hiện trong tab Lịch và slot đã được loại khỏi tab Đặt lịch khám. "
        f"{email_text}"
    ).strip()
    profile = _LAST_PROFILE.get(session_id)
    return {
        "events": [
            {"type": "message", "text": text, "confirm": True},
            {"type": "booking_confirmation", "booking": booking},
        ],
        "profile": dict(profile) if profile else _normalize_profile({"stage": "done"}),
    }


@app.get("/doctors")
def list_doctors(
    query: str | None = None,
    campus: str | None = None,
    specialty: str | None = None,
    time_slot: str | None = None,
    authorization: str | None = Header(None),
) -> dict:
    _require_user_id(authorization)
    folded_query = fold_text(query.strip()) if query and query.strip() else None
    if time_slot and not TIME_SLOT_RE.fullmatch(time_slot):
        raise HTTPException(status_code=400, detail="invalid_time_slot")

    results = []
    for doctor in _load_doctors():
        if campus and doctor.get("campus") != campus:
            continue
        if specialty and doctor.get("specialty") != specialty:
            continue
        if folded_query and folded_query not in fold_text(doctor.get("full_name", "")):
            continue
        open_slots = _open_slots(doctor["id_doctor"])
        if time_slot:
            open_slots = [slot for slot in open_slots if slot["time_slot"] == time_slot]
            if not open_slots:
                continue
        results.append({
            **doctor,
            "next_slots": [
                {"visit_date": s["visit_date"], "time_slot": s["time_slot"], "campus": s["campus"], "room": s["room"]}
                for s in open_slots[:2]
            ],
            "available_count": len(open_slots),
        })

    results.sort(key=lambda d: fold_text(d["full_name"]))
    return {"doctors": results}


@app.get("/doctors/{doctor_id}/schedule")
def get_doctor_schedule(doctor_id: str, authorization: str | None = Header(None)) -> dict:
    _require_user_id(authorization)
    doctor = next((d for d in _load_doctors() if d["id_doctor"] == doctor_id), None)
    if not doctor:
        raise HTTPException(status_code=404, detail="doctor_not_found")
    return {
        "doctor": doctor,
        "slots": [
            {"visit_date": s["visit_date"], "time_slot": s["time_slot"], "campus": s["campus"], "room": s["room"]}
            for s in _open_slots(doctor_id)
        ],
    }


@app.post("/doctors/{doctor_id}/book")
def book_doctor_slot(doctor_id: str, payload: dict = Body(...), authorization: str | None = Header(None)) -> dict:
    user_id = _require_user_id(authorization)
    return _book_doctor_slot_for_user(
        user_id,
        doctor_id,
        payload.get("visit_date") or "",
        payload.get("time_slot") or "",
    )


# ---------------------------------------------------------------------------
# Routes — menstrual cycle tracking
# ---------------------------------------------------------------------------

DEFAULT_PERIOD_LENGTH_DAYS = 5   # không theo dõi ngày kết thúc thực tế, dùng ước lượng phổ biến
LUTEAL_PHASE_DAYS = 14           # pha hoàng thể tương đối ổn định giữa các chu kỳ (khác pha nang trứng)
FERTILE_DAYS_BEFORE_OVULATION = 5  # tinh trùng có thể sống vài ngày trong cơ thể
FERTILE_DAYS_AFTER_OVULATION = 1   # trứng chỉ sống ~24h sau rụng


def _add_days(d: date, days: int) -> date:
    return d.fromordinal(d.toordinal() + days)


def _cycle_prediction(entries: list[dict]) -> dict:
    empty = {
        "average_cycle_length_days": None,
        "last_period_start_date": None,
        "current_cycle_day": None,
        "predicted_period_start": None,
        "predicted_period_end": None,
        "ovulation_date": None,
        "fertile_window_start": None,
        "fertile_window_end": None,
        "period_length_days": DEFAULT_PERIOD_LENGTH_DAYS,
    }
    if not entries:
        return empty

    starts = sorted((date.fromisoformat(e["period_start_date"]) for e in entries), reverse=True)
    last_start = starts[0]

    gaps = [(starts[i] - starts[i + 1]).days for i in range(len(starts) - 1)]
    gaps = [g for g in gaps if 15 <= g <= 45]  # lọc bỏ giá trị bất thường
    avg_len = round(sum(gaps) / len(gaps)) if gaps else 28

    current_cycle_day = (date.today() - last_start).days + 1
    predicted_start = _add_days(last_start, avg_len)
    predicted_end = _add_days(predicted_start, DEFAULT_PERIOD_LENGTH_DAYS - 1)

    # Ước lượng ngày rụng trứng lùi từ NGÀY DỰ ĐOÁN của kỳ kế tiếp (pha hoàng thể ổn định
    # hơn pha nang trứng, nên tính lùi từ kỳ tới chính xác hơn tính xuôi từ kỳ vừa rồi).
    ovulation = _add_days(predicted_start, -LUTEAL_PHASE_DAYS)
    fertile_start = _add_days(ovulation, -FERTILE_DAYS_BEFORE_OVULATION)
    fertile_end = _add_days(ovulation, FERTILE_DAYS_AFTER_OVULATION)

    return {
        "average_cycle_length_days": avg_len,
        "last_period_start_date": last_start.isoformat(),
        "current_cycle_day": current_cycle_day,
        "predicted_period_start": predicted_start.isoformat(),
        "predicted_period_end": predicted_end.isoformat(),
        "ovulation_date": ovulation.isoformat(),
        "fertile_window_start": fertile_start.isoformat(),
        "fertile_window_end": fertile_end.isoformat(),
        "period_length_days": DEFAULT_PERIOD_LENGTH_DAYS,
    }


@app.get("/cycle")
def list_cycle(authorization: str | None = Header(None)) -> dict:
    user_id = _require_user_id(authorization)
    entries = db.list_cycle_entries(user_id)
    return {"entries": entries, "prediction": _cycle_prediction(entries)}


@app.post("/cycle")
def create_cycle_entry(payload: dict = Body(...), authorization: str | None = Header(None)) -> dict:
    user_id = _require_user_id(authorization)
    period_start_date = payload.get("period_start_date")
    if not period_start_date:
        raise HTTPException(status_code=400, detail="period_start_date_required")
    try:
        parsed_start = date.fromisoformat(period_start_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_period_start_date")
    if parsed_start > date.today():
        raise HTTPException(status_code=400, detail="period_start_date_in_future")

    entry_id = db.add_cycle_entry(user_id, period_start_date, payload.get("note"), now_iso())
    entries = db.list_cycle_entries(user_id)
    return {"id": entry_id, "entries": entries, "prediction": _cycle_prediction(entries)}


@app.delete("/cycle/{entry_id}")
def delete_cycle_entry(entry_id: str, authorization: str | None = Header(None)) -> dict:
    user_id = _require_user_id(authorization)
    if not db.delete_cycle_entry(user_id, entry_id):
        raise HTTPException(status_code=404, detail="not_found")
    entries = db.list_cycle_entries(user_id)
    return {"ok": True, "entries": entries, "prediction": _cycle_prediction(entries)}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import uvicorn

    print(f"Yên server -> http://localhost:{PORT}")
    print(f"  provider={PROVIDER_NAME}  model={SELECTED_MODEL}")
    print(f"  history_window={HISTORY_WINDOW}  max_tool_rounds={MAX_TOOL_ROUNDS}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
