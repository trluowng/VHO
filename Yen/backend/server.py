"""
Yên — HTTP server
=================
Cầu nối giữa frontend React và logic agent trong chat.py, cộng thêm tài
khoản người dùng + hồ sơ sức khỏe + lịch theo dõi sức khỏe/chu kỳ kinh nguyệt.

- POST /triage              body: { history, message }, header Authorization tùy chọn
                             trả về: { events, profile }
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

Chạy:
    cd Yen/backend
    python server.py                    # mặc định http://localhost:8787

Rồi ở frontend (Yen/frontend/.env):  VITE_TRIAGE_API_URL=http://localhost:8787/triage
"""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import db
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from auth import create_token, hash_password, verify_password, verify_token

# Import the core agent loop and helpers from chat.py
from chat import run_model_tool_loop, trim_history, write_transcript, safe_slug, now_iso
from versioning import artifact_version_dict, build_artifact_version
from seed_demo import seed_demo_accounts


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

SYSTEM_PROMPT = (ARTIFACTS_DIR / "system_prompt.md").read_text(encoding="utf-8")
TOOL_DECLARATIONS = load_tool_declarations(ARTIFACTS_DIR / "tools.yaml")
# Triage chỉ cần "clarify" (hỏi lại bệnh nhân). lookup/fetch/format là tool nghiên cứu
# web sót lại từ template gốc — không cần cho tư vấn triệu chứng, và mỗi lần model gọi
# thêm 1 vòng round-trip Gemini nữa (chậm hẳn), nên bỏ khỏi danh sách tool đưa cho model.
TRIAGE_TOOL_NAMES = {"clarify"}
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

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
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


def _agent_result_to_response(result: dict) -> dict:
    assistant_text = result.get("assistant_text", "")
    status = result.get("status", "answered")

    parsed = _extract_json(assistant_text)
    if parsed and "events" in parsed:
        events = parsed["events"] if isinstance(parsed["events"], list) else []
        profile = _normalize_profile(
            parsed.get("profile") if isinstance(parsed.get("profile"), dict) else {}
        )
        return {"events": events, "profile": profile}

    stage_map = {
        "waiting_for_user": "questioning",
        "max_tool_rounds": "done",
        "answered": "done",
    }
    stage = stage_map.get(status, "questioning")

    events: list[dict] = [{"type": "message", "text": assistant_text, "confirm": False}]
    profile = _normalize_profile({"stage": stage})
    return {"events": events, "profile": profile}


def triage(payload: dict, user_id: str | None) -> dict:
    messages = _build_messages(payload.get("history", []), payload.get("message", ""), user_id)

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
        "user": payload.get("message", ""),
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

    return _agent_result_to_response(result)


# ---------------------------------------------------------------------------
# Routes — health & triage
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {"ok": True, "provider": PROVIDER_NAME, "model": SELECTED_MODEL, "port": PORT}


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

    db.update_profile(user_id, updates, now_iso())
    return db.get_profile(user_id)


# ---------------------------------------------------------------------------
# Routes — health calendar
# ---------------------------------------------------------------------------

CALENDAR_TYPES = {"kham_benh", "xet_nghiem", "thuoc", "tiem_chung", "khac"}
TIME_RE = re.compile(r"\d{2}:\d{2}")


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

    entry_id = db.add_calendar_entry(
        user_id, entry_date, entry_type, title, payload.get("note"), now_iso(),
        time_start=time_start, time_end=time_end, doctor=doctor, location=location,
    )
    return {"id": entry_id}


@app.delete("/calendar/{entry_id}")
def delete_calendar_entry(entry_id: str, authorization: str | None = Header(None)) -> dict:
    user_id = _require_user_id(authorization)
    if not db.delete_calendar_entry(user_id, entry_id):
        raise HTTPException(status_code=404, detail="not_found")
    return {"ok": True}


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
