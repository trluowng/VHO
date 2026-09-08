"""
Yên — HTTP server (Trợ lý sức khỏe cá nhân)
================================================
Cầu nối giữa frontend React và logic agent trong chat.py, cộng thêm hồ sơ sức
khỏe và lịch theo dõi được tách theo một mã phiên ẩn danh của từng trình duyệt.

- POST /triage              body: { history, message }, header X-Client-ID
                             trả về: { events, profile }
- POST /stt/transcribe       body: audio/wav
                             trả về: { text, language }
- POST /tts                  body: { text }
                             trả về: audio/mpeg (MP3) để trình duyệt tự phát
- GET  /health               kiểm tra server
- GET/PUT /profile, /calendar, /cycle dùng cùng X-Client-ID
- GET  /doctors?query=&campus=&specialty= -> danh sách bác sĩ + 2 lịch trống gần nhất
- GET  /doctors/{id}/schedule             -> toàn bộ lịch trống của 1 bác sĩ

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
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

import db
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from tools._shared import fold_text
from email_service import AppointmentEmail, AppointmentEmailService

# Import the core agent loop and helpers from chat.py
from chat import run_model_tool_loop, trim_history, write_transcript, safe_slug, now_iso
from versioning import artifact_version_dict, build_artifact_version
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

PROVIDER_NAME = os.getenv("TRIAGE_PROVIDER", "gemini")
MODEL = os.getenv("TRIAGE_MODEL", None)          # None → provider's default_model
HISTORY_WINDOW = int(os.getenv("TRIAGE_HISTORY_WINDOW", "5"))
MAX_TOOL_ROUNDS = int(os.getenv("TRIAGE_MAX_TOOL_ROUNDS", "5"))
MIN_TRIAGE_FOLLOWUP_QUESTIONS = max(
    0,
    int(os.getenv("TRIAGE_MIN_FOLLOWUP_QUESTIONS", "2")),
)
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
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        ",".join(
            [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "https://vho-triage-frontend.onrender.com",
                "https://vho-yen-frontend.onrender.com",
            ]
        ),
    ).split(",")
    if origin.strip()
]

GENDERS = {"nam", "nu"}

app = FastAPI(title="Yên Triage Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Anonymous browser session helpers
# ---------------------------------------------------------------------------

CLIENT_ID_RE = re.compile(r"[A-Za-z0-9_-]{16,128}")


def _require_client_user_id(
    x_client_id: str | None = Header(None, alias="X-Client-ID"),
) -> str:
    """Resolve the browser-local identity used to partition persisted data."""
    client_id = (x_client_id or "").strip()
    if not CLIENT_ID_RE.fullmatch(client_id):
        raise HTTPException(status_code=400, detail="client_id_required")
    db.ensure_anonymous_user(client_id, now_iso())
    return client_id


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
    if profile.get("full_name"):
        parts.append(f"Họ tên: {profile['full_name']}")
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
    # Only clinically useful fields are sent back to the LLM. Contact and
    # insurance details remain in SQLite for UI/booking use and are not added
    # to every model request.
    for key, label in (("occupation", "Nghề nghiệp"), ("blood_type", "Nhóm máu")):
        if profile.get(key):
            parts.append(f"{label}: {profile[key]}")

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
            "HỒ SƠ BỆNH NHÂN (đã lưu — KHÔNG hỏi lại các mục này trừ khi "
            "cần làm rõ thêm chi tiết):\n" + "\n".join(f"- {p}" for p in parts)
        ),
    }


PATIENT_RELATIONSHIP_LABELS = {
    "self": "chính người đang trò chuyện",
    "son": "con trai của người đang trò chuyện",
    "daughter": "con gái của người đang trò chuyện",
    "mother": "mẹ của người đang trò chuyện",
    "father": "bố của người đang trò chuyện",
    "spouse": "vợ/chồng của người đang trò chuyện",
    "other": "một người khác",
}


def _patient_context_message(patient_context: dict | None) -> dict | None:
    """Build a high-priority context message for a third-party consultation."""
    if not patient_context or patient_context.get("relationship") in {None, "self"}:
        return None

    relationship = patient_context.get("relationship")
    parts = [f"Quan hệ: {PATIENT_RELATIONSHIP_LABELS.get(relationship, 'một người khác')}"]
    if patient_context.get("age") is not None:
        parts.append(f"Tuổi người bệnh: {patient_context['age']}")
    gender_label = {"nam": "Nam", "nu": "Nữ"}.get(patient_context.get("gender"))
    if gender_label:
        parts.append(f"Giới tính người bệnh: {gender_label}")
    for key, label in (
        ("chronic_conditions", "Bệnh nền người bệnh"),
        ("allergies", "Dị ứng người bệnh"),
        ("medications", "Thuốc người bệnh đang dùng"),
    ):
        values = patient_context.get(key)
        if values:
            parts.append(f"{label}: {', '.join(values)}")

    return {
        "role": "system",
        "content": (
            "ĐỐI TƯỢNG ĐANG ĐƯỢC HỎI BỆNH (ưu tiên tuyệt đối khi đánh giá):\n"
            + "\n".join(f"- {part}" for part in parts)
            + "\nKhông dùng tuổi, giới tính, bệnh nền, dị ứng hoặc thuốc trong hồ sơ của người "
              "đang trò chuyện để đánh giá thay cho người bệnh này."
        ),
    }


def _build_messages(
    history: list[dict],
    message: str,
    user_id: str | None,
    patient_context: dict | None = None,
) -> list[dict]:
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

    # Giữ lịch sử đủ để model biết các câu hỏi đã hỏi và không lặp lại.
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
        {
            "role": "system",
            "content": (
                "NHỊP HỎI BỆNH: Trừ cấp cứu hoặc khi khách yêu cầu dừng hỏi, phải hoàn thành ít "
                f"nhất {MIN_TRIAGE_FOLLOWUP_QUESTIONS} lượt hỏi đáp bổ sung trước phản hồi đầu tiên "
                "có event result. Tin nhắn mô tả ban đầu không được tính là lượt hỏi đáp bổ sung."
            ),
        },
    ]
    patient_msg = _patient_context_message(patient_context)
    if patient_msg:
        messages.append(patient_msg)
    elif user_id:
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


HEALTH_PROFILE_LIST_FIELDS = ("chronic_conditions", "allergies", "medications")
HEALTH_PROFILE_SCALAR_FIELDS = (
    "full_name",
    "phone",
    "email",
    "address",
    "occupation",
    "blood_type",
    "insurance_status",
    "insurance_number",
    "emergency_contact_name",
    "emergency_contact_relationship",
    "emergency_contact_phone",
)


def _sanitize_health_profile_updates(raw_updates: Any) -> dict[str, Any]:
    """Validate profile facts extracted by the model before persisting them.

    The model is instructed to emit only facts explicitly stated by the user,
    but its output is still untrusted. Invalid or unsupported values are ignored
    instead of allowing a chat turn to corrupt the stored health profile.
    """
    if not isinstance(raw_updates, dict):
        return {}

    updates: dict[str, Any] = {}

    age = raw_updates.get("age")
    if isinstance(age, str) and age.strip().isdigit():
        age = int(age.strip())
    if isinstance(age, int) and not isinstance(age, bool) and 0 < age < 120:
        updates["age"] = age

    gender = raw_updates.get("gender")
    if isinstance(gender, str):
        normalized_gender = {
            "nam": "nam",
            "male": "nam",
            "nu": "nu",
            "nữ": "nu",
            "female": "nu",
        }.get(gender.strip().lower())
        if normalized_gender:
            updates["gender"] = normalized_gender

    birth_date = raw_updates.get("birth_date")
    if isinstance(birth_date, str) and birth_date.strip():
        try:
            parsed_birth_date = date.fromisoformat(birth_date.strip())
            today = date.today()
            calculated_age = today.year - parsed_birth_date.year - (
                (today.month, today.day) < (parsed_birth_date.month, parsed_birth_date.day)
            )
            if parsed_birth_date <= today and 0 < calculated_age < 120:
                updates["birth_date"] = parsed_birth_date.isoformat()
                updates["age"] = calculated_age
        except ValueError:
            pass

    for key in HEALTH_PROFILE_LIST_FIELDS:
        value = raw_updates.get(key)
        if not isinstance(value, list):
            continue
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                continue
            text = item.strip()[:200]
            folded = fold_text(text)
            if text and folded not in seen:
                seen.add(folded)
                cleaned.append(text)
        updates[key] = cleaned[:30]

    for key in HEALTH_PROFILE_SCALAR_FIELDS:
        value = raw_updates.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        text = value.strip()[:500]
        if key == "email":
            text = text.lower()
            if "@" not in text:
                continue
        updates[key] = text

    return updates


PATIENT_RELATIONSHIPS = {"self", "son", "daughter", "mother", "father", "spouse", "other"}
_LAST_PATIENT_CONTEXT: dict[str, dict[str, Any]] = {}


def _sanitize_patient_context(
    raw_context: Any,
    current_context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Validate and merge the person-being-assessed context for one chat session."""
    if not isinstance(raw_context, dict):
        return dict(current_context) if current_context else None

    relationship = raw_context.get("relationship")
    if relationship not in PATIENT_RELATIONSHIPS:
        relationship = None

    current_relationship = (current_context or {}).get("relationship")
    if relationship and current_relationship and relationship != current_relationship:
        # A new consultation subject must not inherit demographics or medical
        # history from the previous person in this session.
        context: dict[str, Any] = {}
    else:
        context = dict(current_context or {})
    if relationship:
        context["relationship"] = relationship

    age = raw_context.get("age")
    if isinstance(age, str) and age.strip().isdigit():
        age = int(age.strip())
    if isinstance(age, int) and not isinstance(age, bool) and 0 < age < 120:
        context["age"] = age

    gender = raw_context.get("gender")
    if isinstance(gender, str):
        normalized_gender = {
            "nam": "nam", "male": "nam", "nu": "nu", "nữ": "nu", "female": "nu",
        }.get(gender.strip().lower())
        if normalized_gender:
            context["gender"] = normalized_gender
    if context.get("relationship") == "son":
        context["gender"] = "nam"
    elif context.get("relationship") == "daughter":
        context["gender"] = "nu"

    for key in HEALTH_PROFILE_LIST_FIELDS:
        value = raw_context.get(key)
        if not isinstance(value, list):
            continue
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                continue
            text = item.strip()[:200]
            folded = fold_text(text)
            if text and folded not in seen:
                seen.add(folded)
                cleaned.append(text)
        context[key] = cleaned[:30]

    return context or None


def _persist_extracted_health_profile(
    user_id: str | None,
    parsed: dict,
    *,
    allow_update: bool = True,
) -> dict | None:
    """Persist explicit profile facts returned by the LLM and return the merged profile."""
    if not user_id:
        return None
    if allow_update:
        updates = _sanitize_health_profile_updates(parsed.get("health_profile_updates"))
        if updates:
            db.update_profile(user_id, updates, now_iso())
    return db.get_profile(user_id)


def _apply_extracted_context(
    user_id: str | None,
    session_id: str,
    parsed: dict,
    authoritative_context: dict[str, Any] | None = None,
) -> tuple[dict | None, dict | None]:
    """Keep third-party patient facts session-scoped and owner facts persistent."""
    raw_patient_context = parsed.get("patient_context")
    if authoritative_context:
        # The context resolved before the main triage call is authoritative for
        # this turn.  The answer model may add missing medical facts, but it may
        # not turn an explicitly mentioned child/relative back into the account
        # owner (which would also make owner-profile writes unsafe).
        raw_patient_context = (
            dict(raw_patient_context) if isinstance(raw_patient_context, dict) else {}
        )
        authoritative_relationship = authoritative_context.get("relationship")
        model_relationship = raw_patient_context.get("relationship")
        if model_relationship != authoritative_relationship:
            # If the main model changed who the patient is, discard all of its
            # patient facts rather than mixing owner and relative demographics.
            raw_patient_context = dict(authoritative_context)
        else:
            # Same subject: accept newly extracted facts (e.g. a corrected age
            # or medication on a follow-up), while keeping relationship locked.
            raw_patient_context["relationship"] = authoritative_relationship
    patient_context = _sanitize_patient_context(
        raw_patient_context,
        _LAST_PATIENT_CONTEXT.get(session_id),
    )
    if patient_context:
        _LAST_PATIENT_CONTEXT[session_id] = patient_context

    # Only facts explicitly classified as belonging to the speaker/account
    # owner may update the durable browser profile. Child/parent/spouse facts
    # remain in patient_context and cannot overwrite the owner's profile.
    is_self = patient_context and patient_context.get("relationship") == "self"
    health_profile = _persist_extracted_health_profile(
        user_id,
        parsed,
        allow_update=bool(is_self),
    )
    return health_profile, patient_context


def _enforce_patient_context_on_events(
    events: list[dict],
    patient_context: dict[str, Any] | None,
) -> list[dict]:
    """Make demographic context visible in, and consequential to, the conclusion.

    The model receives patient_context in its system messages, but a model can
    still omit the age from its displayed rationale or suggest an adult clinic
    for a child. This final guard keeps those two user-visible invariants exact.
    """
    if not patient_context:
        return events

    age = patient_context.get("age")
    if not isinstance(age, int) or isinstance(age, bool):
        return events

    relationship = patient_context.get("relationship")
    gender = patient_context.get("gender")
    if age < 16:
        patient_label = {
            "son": "bé trai",
            "daughter": "bé gái",
        }.get(relationship, {"nam": "bé trai", "nu": "bé gái"}.get(gender, "trẻ"))
        age_note = (
            f"Người bệnh là {patient_label} {age} tuổi, vì vậy hướng khám được ưu tiên "
            "theo độ tuổi nhi khoa."
        )
    else:
        relationship_label = {
            "self": "chính người đang trò chuyện",
            "son": "con trai",
            "daughter": "con gái",
            "mother": "mẹ",
            "father": "bố",
            "spouse": "vợ/chồng",
            "other": "người được hỏi bệnh",
        }.get(relationship, "người được hỏi bệnh")
        gender_label = {"nam": "nam", "nu": "nữ"}.get(gender)
        subject = f"{relationship_label}, {gender_label}" if gender_label else relationship_label
        age_note = f"Đánh giá này đã tính đến người bệnh là {subject}, {age} tuổi."

    for event in events:
        if not isinstance(event, dict):
            continue
        if event.get("type") == "result" and isinstance(event.get("triage"), dict):
            triage_result = event["triage"]
            reason = str(triage_result.get("reason") or "").strip()
            if not re.search(rf"\b{age}\s*tuoi\b", fold_text(reason)):
                if reason and reason[-1] not in ".!?":
                    reason += "."
                triage_result["reason"] = f"{reason} {age_note}".strip()
        elif age < 16 and event.get("type") == "question":
            question = str(event.get("text") or "")
            folded_question = fold_text(question)
            if any(term in folded_question for term in ("tim bac si", "lich trong", "dat lich")):
                event["text"] = (
                    "Bạn có muốn mình tìm bác sĩ và lịch trống chuyên khoa Nhi "
                    "để đặt lịch cho bé không?"
                )
    return events


def _enforce_preliminary_assessment(
    events: list[dict],
    history: list[dict] | None,
    current_message: str,
    patient_context: dict[str, Any] | None,
) -> list[dict]:
    """Guarantee a cautious preliminary assessment before the care recommendation."""
    conversation = " ".join(
        [str(turn.get("text") or "") for turn in (history or [])] + [current_message or ""]
    )
    folded = fold_text(conversation)
    is_wet_dream = any(
        marker in folded
        for marker in ("mong tinh", "xuat tinh khi ngu", "xuat tinh luc ngu")
    )
    age = (patient_context or {}).get("age")

    generic_by_level = {
        "green": (
            "Các thông tin hiện tại phù hợp hơn với một tình trạng nhẹ hoặc biến đổi sinh lý; "
            "chưa đủ cơ sở để khẳng định một bệnh cụ thể."
        ),
        "amber": (
            "Có dấu hiệu cần được khám trực tiếp để làm rõ nguyên nhân; chưa thể xác định bệnh "
            "cụ thể chỉ qua hội thoại."
        ),
        "red": (
            "Các dấu hiệu gợi ý nguy cơ cấp tính cần được xử trí ngay, không nên chờ xác định "
            "bệnh qua hội thoại."
        ),
    }

    for event in events:
        if not isinstance(event, dict) or event.get("type") != "result":
            continue
        triage_result = event.get("triage")
        if not isinstance(triage_result, dict):
            continue
        level = triage_result.get("level")
        if is_wet_dream and isinstance(age, int) and 9 <= age <= 17:
            if level == "green":
                triage_result["preliminaryAssessment"] = (
                    "Khả năng phù hợp nhất là hiện tượng sinh lý của tuổi dậy thì (xuất tinh "
                    "trong lúc ngủ), chưa gợi ý bệnh lý khi không kèm dấu hiệu bất thường."
                )
            else:
                triage_result["preliminaryAssessment"] = (
                    "Đây là biểu hiện xuất tinh trong lúc ngủ, nhưng thông tin đi kèm chưa cho "
                    "phép xem là biến đổi sinh lý đơn thuần và cần được đánh giá trực tiếp."
                )
        elif not str(triage_result.get("preliminaryAssessment") or "").strip():
            triage_result["preliminaryAssessment"] = generic_by_level.get(
                level,
                "Chưa đủ cơ sở để xác định một bệnh cụ thể chỉ qua hội thoại.",
            )
    return events


def _enforce_question_quick_replies(
    events: list[dict],
    history: list[dict] | None,
    current_message: str,
) -> list[dict]:
    """Supply useful choices when the model leaves a puberty follow-up open-ended."""
    conversation = " ".join(
        [str(turn.get("text") or "") for turn in (history or [])] + [current_message or ""]
    )
    if not any(
        marker in fold_text(conversation)
        for marker in ("mong tinh", "xuat tinh khi ngu", "xuat tinh luc ngu")
    ):
        return events

    for event in events:
        if not isinstance(event, dict) or event.get("type") != "question" or event.get("quick"):
            continue
        folded_question = fold_text(str(event.get("text") or ""))
        if any(marker in folded_question for marker in ("chi khi ngu", "ca luc thuc", "tan suat", "giac ngu")):
            event["quick"] = [
                "Chỉ khi ngủ, không ảnh hưởng",
                "Chỉ khi ngủ nhưng cháu lo lắng",
                "Có cả lúc thức",
            ]
        elif any(marker in folded_question for marker in ("dau tinh hoan", "buot tieu", "sung do")):
            event["quick"] = [
                "Không có",
                "Đau hoặc sưng",
                "Buốt tiểu/sốt",
                "Có máu hoặc dịch bất thường",
            ]
    return events


def _count_answered_followup_questions(
    history: list[dict] | None,
    current_message: str = "",
) -> int:
    """Count assistant questions that already received a subsequent user turn."""
    answered = 0
    pending_question = False
    for turn in history or []:
        role = turn.get("role")
        text = str(turn.get("text") or "").strip()
        if not text:
            continue
        if role in {"ai", "assistant"}:
            pending_question = "?" in text
        elif role == "user" and pending_question:
            answered += 1
            pending_question = False
    # The frontend sends the current user answer separately from history.
    if pending_question and (current_message or "").strip():
        answered += 1
    return answered


def _user_requests_assessment_now(message: str) -> bool:
    folded = fold_text(message or "")
    return any(
        marker in folded
        for marker in (
            "khong muon tra loi them",
            "khong can hoi them",
            "bo qua cau hoi",
            "ket luan luon",
            "danh gia luon",
            "cho ket qua luon",
        )
    )


def _next_required_followup(history: list[dict] | None, message: str) -> dict[str, Any]:
    conversation = " ".join(
        [str(turn.get("text") or "") for turn in (history or [])] + [message or ""]
    )
    folded = fold_text(conversation)
    if any(marker in folded for marker in ("mong tinh", "xuat tinh khi ngu", "xuat tinh luc ngu")):
        warning_was_asked = any(
            marker in folded
            for marker in ("ngoai mong tinh", "dau hoac sung vung tinh hoan", "buot tieu")
        )
        if not warning_was_asked:
            return {
                "type": "question",
                "text": (
                    "Ngoài mộng tinh, cháu có đau hoặc sưng vùng tinh hoàn, sốt, buốt tiểu, "
                    "có máu hay dịch bất thường không?"
                ),
                "quick": ["Không có", "Đau hoặc sưng", "Buốt tiểu/sốt", "Có máu hoặc dịch bất thường"],
            }
        pattern_was_asked = any(
            marker in folded
            for marker in ("chi xay ra khi ngu", "ca luc thuc", "tan suat", "mat ngu", "lo lang nhieu")
        )
        if not pattern_was_asked:
            return {
                "type": "question",
                "text": (
                    "Tình trạng chỉ xảy ra khi ngủ hay cả lúc thức, và có làm cháu mất ngủ "
                    "hoặc lo lắng nhiều không?"
                ),
                "quick": ["Chỉ khi ngủ, không ảnh hưởng", "Chỉ khi ngủ nhưng cháu lo lắng", "Có cả lúc thức"],
            }
    candidates = (
        (
            ("do dan", "giam dan", "nang dan", "nang len", "khong doi", "dien tien"),
            "Trong thời gian theo dõi, triệu chứng đang đỡ dần, gần như không đổi hay nặng lên?",
            ["Đỡ dần", "Gần như không đổi", "Nặng lên"],
        ),
        (
            ("anh huong sinh hoat", "an uong", "ngu nghi", "uong duoc nuoc"),
            "Hiện triệu chứng ảnh hưởng đến ăn uống, ngủ nghỉ hoặc sinh hoạt của người bệnh ở mức nào?",
            ["Gần như không ảnh hưởng", "Ảnh hưởng một phần", "Không ăn/uống/ngủ được"],
        ),
        (
            ("dau hieu nguy hiem",),
            (
                "Hiện người bệnh có dấu hiệu nguy hiểm nào như khó thở, ngất hoặc lơ mơ, "
                "đau tăng dữ dội, nôn liên tục hay không uống được nước không?"
            ),
            ["Không có", "Khó thở/ngất/lơ mơ", "Đau tăng dữ dội", "Nôn liên tục/không uống được"],
        ),
    )
    for signals, text, quick in candidates:
        if not any(signal in folded for signal in signals):
            return {"type": "question", "text": text, "quick": quick}
    return {
        "type": "question",
        "text": "Bạn còn nhận thấy thay đổi hoặc dấu hiệu nào khác ở người bệnh mà mình chưa hỏi đến không?",
        "quick": ["Không có thêm", "Có, tôi muốn bổ sung"],
    }


def _question_repeats_known_fact(
    question: str,
    profile: dict,
    history: list[dict] | None,
    current_message: str,
) -> bool:
    """Detect common cases where the model asks for a fact already provided."""
    folded_question = fold_text(question or "")
    conversation = " ".join(
        [str(turn.get("text") or "") for turn in (history or [])] + [current_message or ""]
    )
    folded_conversation = fold_text(conversation)
    facts = profile.get("facts") if isinstance(profile.get("facts"), dict) else {}

    asks_duration = any(
        marker in folded_question
        for marker in ("tu khi nao", "bao lau", "may ngay", "thoi gian")
    )
    if asks_duration and facts.get("duration"):
        return True

    asks_severity_or_nature = any(
        marker in folded_question
        for marker in ("muc do", "cam giac nhu the nao", "dau nhu the nao", "tinh chat")
    )
    nature_is_known = bool(facts.get("severity")) or any(
        marker in folded_conversation
        for marker in ("am i", "dau quan", "quan tung con", "dau nhoi", "du doi", "muc vua", "muc nhe", "muc nang")
    )
    if asks_severity_or_nature and nature_is_known:
        return True

    asks_associated = any(
        marker in folded_question
        for marker in ("kem theo", "trieu chung khac", "co bi them")
    )
    return bool(asks_associated and facts.get("associated") is not None)


def _delay_premature_triage_result(
    events: list[dict],
    profile: dict,
    history: list[dict] | None,
    current_message: str,
    previous_profile: dict | None,
) -> tuple[list[dict], dict]:
    """Require a short clinical follow-up phase before the first conclusion."""
    result_events = [
        event for event in events
        if isinstance(event, dict)
        and event.get("type") == "result"
        and isinstance(event.get("triage"), dict)
    ]
    if not result_events:
        question_events = [
            event for event in events
            if isinstance(event, dict) and event.get("type") == "question"
        ]
        if profile.get("symptoms") and question_events:
            profile = dict(profile)
            profile["stage"] = "questioning"
            answered = _count_answered_followup_questions(history, current_message)
            first_question = str(question_events[0].get("text") or "")
            folded_question = fold_text(first_question)
            is_booking_question = any(
                marker in folded_question
                for marker in ("tim bac si", "lich trong", "dat lich")
            )
            if (
                is_booking_question
                or (
                    answered < MIN_TRIAGE_FOLLOWUP_QUESTIONS
                    and not _user_requests_assessment_now(current_message)
                    and _question_repeats_known_fact(
                        first_question,
                        profile,
                        history,
                        current_message,
                    )
                )
            ):
                events = [
                    event for event in events
                    if isinstance(event, dict) and event.get("type") == "message"
                ]
                events.append(_next_required_followup(history, current_message))
        return events, profile
    if not profile.get("symptoms"):
        return events, profile
    if previous_profile and previous_profile.get("stage") in {"done", "emergency"}:
        return events, profile
    if any(event.get("triage", {}).get("level") == "red" for event in result_events):
        return events, profile
    if any(isinstance(event, dict) and event.get("type") == "emergency" for event in events):
        return events, profile
    if _user_requests_assessment_now(current_message):
        return events, profile

    answered = _count_answered_followup_questions(history, current_message)
    if answered >= MIN_TRIAGE_FOLLOWUP_QUESTIONS:
        return events, profile

    # Preserve acknowledgements, but remove the premature result and its
    # booking question. Replace them with one clinically useful follow-up.
    delayed_events = [
        event for event in events
        if isinstance(event, dict) and event.get("type") == "message"
    ]
    delayed_events.append(_next_required_followup(history, current_message))

    delayed_profile = dict(profile)
    delayed_profile["stage"] = "questioning"
    delayed_profile["confidence"] = min(int(delayed_profile.get("confidence") or 0), 69)
    if delayed_profile.get("confTier") == "high":
        delayed_profile["confTier"] = "mid"
    missing = list(delayed_profile.get("missing") or [])
    pacing_note = (
        "Cần thêm "
        f"{MIN_TRIAGE_FOLLOWUP_QUESTIONS - answered} lượt xác nhận trước khi kết luận"
    )
    if pacing_note not in missing:
        missing.append(pacing_note)
    delayed_profile["missing"] = missing
    return delayed_events, delayed_profile


PROFILE_EXTRACTION_SIGNAL_TERMS = (
    "tuoi", "gioi tinh", "sinh ngay", "ngay sinh", "sinh nam", "toi ten", "ten toi",
    "ho ten", "so dien thoai", "sdt", "email", "dia chi", "nghe nghiep", "lam nghe",
    "nhom mau", "bao hiem", "bhyt", "benh nen", "tien su", "di ung", "thuoc dang",
    "dang dung thuoc", "dang uong", "lien he khan cap", "nguoi lien he", "toi bi",
    "minh bi", "em bi", "con trai", "con gai", "con toi", "me toi", "ma toi",
    "bo toi", "ba toi", "cha toi", "vo toi", "chong toi", "nguoi nha toi",
)


def _message_may_contain_health_profile(message: str) -> bool:
    folded = fold_text(message or "")
    return (
        any(term in folded for term in PROFILE_EXTRACTION_SIGNAL_TERMS)
        or bool(re.search(r"\b(nam|nu)\b", folded))
    )


def _explicit_patient_hint(message: str) -> dict[str, Any] | None:
    """Extract unambiguous relationship/age hints before any network call.

    This is a safety guard, not the full profile extractor: it prevents an
    explicitly mentioned child's demographics from ever being written into
    the account owner's profile even if the LLM extraction request times out.
    """
    folded = fold_text(message or "")
    relationship = None
    for candidate, markers in (
        ("son", ("con trai toi", "con trai minh", "con trai em")),
        ("daughter", ("con gai toi", "con gai minh", "con gai em")),
        ("mother", ("me toi", "ma toi", "me minh", "ma minh")),
        ("father", ("bo toi", "ba toi", "cha toi", "bo minh", "ba minh")),
        ("spouse", ("vo toi", "chong toi", "vo minh", "chong minh")),
    ):
        if any(marker in folded for marker in markers):
            relationship = candidate
            break
    if not relationship:
        # Allow an explicit switch back to the speaker in a session that was
        # previously about a relative. Third-party markers above take priority,
        # so "con trai tôi bị..." can never be mistaken for self.
        self_markers = (
            "ban than toi", "ban than minh", "toi bi", "toi dang bi",
            "minh bi", "minh dang bi", "em bi", "em dang bi",
            "gio hoi cho toi", "bay gio hoi cho toi",
        )
        if any(marker in folded for marker in self_markers):
            relationship = "self"
        else:
            return None

    hint: dict[str, Any] = {"relationship": relationship}
    age_match = re.search(r"\b(\d{1,3})\s*tuoi\b", folded)
    if age_match:
        age = int(age_match.group(1))
        if 0 < age < 120:
            hint["age"] = age
    if relationship == "son":
        hint["gender"] = "nam"
    elif relationship == "daughter":
        hint["gender"] = "nu"
    return hint


def _extract_context_before_triage(
    user_id: str | None,
    session_id: str,
    history: list[dict],
    message: str,
) -> tuple[dict | None, dict | None]:
    """Use a focused LLM pass to resolve who is being assessed before triage.

    Facts about the speaker can update their durable health profile. Facts
    about a child/parent/spouse remain in a session-scoped patient context.
    """
    current_patient = _LAST_PATIENT_CONTEXT.get(session_id)
    explicit_hint = _explicit_patient_hint(message)
    if explicit_hint:
        current_patient = _sanitize_patient_context(explicit_hint, current_patient)
        if current_patient:
            _LAST_PATIENT_CONTEXT[session_id] = current_patient

    # An explicit/session-known third-party context already gives the main
    # triage model everything it needs. Let that single response enrich the
    # remaining patient fields, avoiding a redundant OpenAI request per turn.
    if current_patient and current_patient.get("relationship") != "self":
        return db.get_profile(user_id) if user_id else None, current_patient

    recent_history = [
        (turn.get("text") or "").strip() for turn in (history or [])[-6:]
        if (turn.get("text") or "").strip()
    ]
    context_text = "\n".join([*recent_history, message])
    should_extract = _message_may_contain_health_profile(message) or (
        not current_patient and _message_may_contain_health_profile(context_text)
    )
    if not user_id or not should_extract:
        return db.get_profile(user_id) if user_id else None, current_patient

    current_profile = db.get_profile(user_id) or {}
    # Existing scalar/contact values are not needed for extraction. Only list
    # fields must be shown so the model can return their complete updated value.
    extraction_context = {
        key: current_profile.get(key) or [] for key in HEALTH_PROFILE_LIST_FIELDS
    }
    extraction_messages = [
        {
            "role": "system",
            "content": (
                "Bạn là bộ phân giải người bệnh và trích xuất hồ sơ, không tư vấn, không suy đoán. "
                "Xác định người đang được hỏi bệnh từ HỘI THOẠI + TIN NHẮN HIỆN TẠI: chính người "
                "đang chat=self; con trai=son; con gái=daughter; mẹ=mother; bố=father; vợ/chồng=spouse; "
                "người khác=other. Ghi tuổi, giới tính, bệnh nền, dị ứng và thuốc CỦA NGƯỜI BỆNH vào "
                "patient_context. Không đưa triệu chứng cấp tính, thời gian hay mức độ đau vào bệnh nền. "
                "Chỉ điền health_profile_updates khi relationship=self và thông tin thuộc chính người "
                "đang chat; nếu hỏi cho người khác thì mọi trường health_profile_updates phải null. "
                "Với các danh sách có cập nhật, trả toàn bộ giá trị đúng sau khi kết hợp context hiện tại. "
                "Để đáp ứng schema: events=[], profile={stage:'intake', symptoms:[], confidence:0, "
                "confTier:'none', missing:[], facts:{duration:null,severity:null,associated:null}}. "
                "Không trả lời tư vấn trong events."
            ),
        },
        {
            "role": "user",
            "content": (
                "DANH SÁCH HỒ SƠ CỦA NGƯỜI ĐANG CHAT (chỉ dùng nếu patient_context.relationship=self):\n"
                f"{json.dumps(extraction_context, ensure_ascii=False, default=str)}\n\n"
                "PATIENT_CONTEXT HIỆN TẠI CỦA PHIÊN:\n"
                f"{json.dumps(current_patient or {}, ensure_ascii=False, default=str)}\n\n"
                "HỘI THOẠI GẦN ĐÂY:\n"
                f"{json.dumps(recent_history, ensure_ascii=False, default=str)}\n\n"
                "TIN NHẮN HIỆN TẠI:\n"
                f"{message}"
            ),
        },
    ]
    try:
        response = PROVIDER.complete(
            extraction_messages,
            [],
            model=SELECTED_MODEL,
            temperature=0.0,
        )
        parsed = _extract_json(response.text or "")
        if parsed:
            if explicit_hint and explicit_hint.get("relationship") != "self":
                # Deterministic relationship evidence wins over model output,
                # and third-party facts can never update the owner's profile.
                model_patient = parsed.get("patient_context")
                if not isinstance(model_patient, dict):
                    model_patient = {}
                model_patient.update(explicit_hint)
                parsed["patient_context"] = model_patient
                parsed["health_profile_updates"] = {}
            return _apply_extracted_context(user_id, session_id, parsed)
    except Exception:
        LOGGER.exception("patient/profile extraction failed, continuing with existing context")
    return db.get_profile(user_id), current_patient


# Last known-good profile per session, for when the model breaks the mandatory JSON
# contract mid-conversation (seen live on Groq/Qwen deep in multi-round tool-calling —
# it occasionally answers in plain prose instead of the JSON schema). Without this, the
# fallback below used to wipe profile.symptoms/facts back to empty and guess a stage,
# silently discarding everything gathered in earlier turns.
_LAST_PROFILE: dict[str, dict] = {}
_LAST_BOOKING_OPTIONS: dict[str, list[dict]] = {}

TOOL_INTENT_TERMS = (
    "gia", "chi phi", "bhyt", "bao hiem", "thu tuc", "giay to", "dich vu",
    "dat lich", "lich trong", "bac si", "chuyen khoa", "tong dai", "gio lam viec",
    "quy trinh", "luat kham", "dia chi benh vien", "kham o dau",
)


def _tools_for_turn(history: list[dict], message: str) -> list[dict[str, Any]]:
    """Expose lookup tools only for turns that actually need hospital data.

    Giving lookup tools to a symptom-only turn made smaller models repeatedly
    call ``tra_cuu`` even though the prompt forbids it. Besides adding latency,
    hitting the tool-round cap also discarded structured profile extraction.
    """
    current = fold_text(message or "")
    if any(term in current for term in TOOL_INTENT_TERMS):
        return OPENAI_TOOLS

    # Short replies such as "Có" or "Sáng mai" inherit booking/service intent
    # from the immediately preceding assistant question.
    if len(current) <= 40 and history:
        previous = fold_text((history[-1].get("text") or ""))
        if any(term in previous for term in TOOL_INTENT_TERMS):
            return OPENAI_TOOLS
    return []


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


def _agent_result_to_response(
    result: dict,
    session_id: str,
    user_id: str | None = None,
    authoritative_patient_context: dict[str, Any] | None = None,
    history: list[dict] | None = None,
    current_message: str = "",
) -> dict:
    booking_options = _booking_options_from_tool_events(result.get("tool_events") or [])
    if booking_options:
        _LAST_BOOKING_OPTIONS[session_id] = booking_options

    assistant_text = result.get("assistant_text", "")

    parsed = _extract_json(assistant_text)
    if parsed and "events" in parsed:
        events = parsed["events"] if isinstance(parsed["events"], list) else []
        if booking_options:
            events.append({"type": "booking_options", "options": booking_options})
        previous_profile = _LAST_PROFILE.get(session_id)
        profile = _normalize_profile(
            parsed.get("profile") if isinstance(parsed.get("profile"), dict) else {}
        )
        health_profile, patient_context = _apply_extracted_context(
            user_id,
            session_id,
            parsed,
            authoritative_patient_context,
        )
        events, profile = _delay_premature_triage_result(
            events,
            profile,
            history,
            current_message,
            previous_profile,
        )
        events = _enforce_patient_context_on_events(events, patient_context)
        events = _enforce_preliminary_assessment(
            events,
            history,
            current_message,
            patient_context,
        )
        events = _enforce_question_quick_replies(events, history, current_message)
        _LAST_PROFILE[session_id] = profile
        return {
            "events": events,
            "profile": profile,
            "health_profile": health_profile,
            "patient_context": patient_context,
        }

    # Model didn't return valid JSON this round -- carry forward the last profile we
    # actually parsed for this session (nothing about the tracked symptoms/stage changed,
    # the model just failed to restate it), rather than resetting to a bare default and
    # mislabeling stage as "done" when the patient may still be mid-questioning.
    events: list[dict] = [{"type": "message", "text": assistant_text, "confirm": False}]
    profile = _LAST_PROFILE.get(session_id)
    profile = dict(profile) if profile else _normalize_profile({"stage": "questioning"})
    if booking_options:
        events.append({"type": "booking_options", "options": booking_options})
    return {
        "events": events,
        "profile": profile,
        "health_profile": db.get_profile(user_id) if user_id else None,
        "patient_context": _LAST_PATIENT_CONTEXT.get(session_id),
    }


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

    # Resolve the actual patient before building the main prompt. A mother can
    # ask for her son without the son's demographics overwriting her profile.
    history = payload.get("history", [])
    _, patient_context = _extract_context_before_triage(
        user_id,
        session_id,
        history,
        message,
    )

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
    messages = _build_messages(history, message, user_id, patient_context)
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
        "history_length": len(history),
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }

    result = run_model_tool_loop(
        provider=PROVIDER,
        messages=messages,
        tools=_tools_for_turn(history, message),
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

    return _agent_result_to_response(
        result,
        session_id,
        user_id,
        patient_context,
        history,
        message,
    )


@app.post("/triage/end")
def triage_end_route(
    payload: dict = Body(...),
    user_id: str = Depends(_require_client_user_id),
) -> dict:
    """Client gọi khi user rời đi / mất kết nối: lưu conversation (TTL 1h) + embed vào vector store."""
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
) -> dict:
    """Convert a short browser-recorded WAV clip to Vietnamese text."""
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
def synthesize_speech(payload: dict = Body(...)) -> Response:
    """Sinh giọng đọc tiếng Việt cho 1 đoạn text, trả về audio/mpeg để trình duyệt tự phát.

    Không dùng backend/stt/speaker.py (module đó phát âm thanh bằng pygame.mixer trên
    MÁY CHẠY SERVER -- vô dụng khi server chạy trên cloud vì không ai nghe được, và mỗi
    lần "phát" sẽ chặn cả request thêm vài giây). gTTS.write_to_fp() sinh MP3 thẳng vào
    bộ nhớ rồi trả về qua HTTP, để trình duyệt phát bằng thẻ <audio> phía client.
    """
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
def triage_route(
    payload: dict = Body(...),
    user_id: str = Depends(_require_client_user_id),
) -> dict:
    try:
        return triage(payload, user_id)
    except Exception as exc:
        # Frontend falls back to the rule-based engine on 500.
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc


# ---------------------------------------------------------------------------
# Routes — health profile
# ---------------------------------------------------------------------------

@app.get("/profile")
def get_profile(user_id: str = Depends(_require_client_user_id)) -> dict:
    profile = db.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="profile_not_found")
    return profile


@app.put("/profile")
def put_profile(
    payload: dict = Body(...),
    user_id: str = Depends(_require_client_user_id),
) -> dict:
    updates: dict[str, Any] = {}

    if "gender" in payload:
        gender = payload.get("gender") or None
        if gender is not None and gender not in GENDERS:
            raise HTTPException(status_code=400, detail="invalid_gender")
        updates["gender"] = gender
    if "age" in payload:
        age = payload["age"]
        if not isinstance(age, int) or not (0 < age < 120):
            raise HTTPException(status_code=400, detail="invalid_age")
        updates["age"] = age
    if "email" in payload:
        email = (payload.get("email") or "").strip().lower()
        if email and "@" not in email:
            raise HTTPException(status_code=400, detail="invalid_email")
        updates["email"] = email or None
    if "birth_date" in payload:
        birth_date = (payload.get("birth_date") or "").strip()
        if birth_date:
            try:
                parsed_birth_date = date.fromisoformat(birth_date)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="invalid_birth_date") from exc
            if parsed_birth_date > date.today():
                raise HTTPException(status_code=400, detail="invalid_birth_date")
            today = date.today()
            updates["age"] = today.year - parsed_birth_date.year - (
                (today.month, today.day) < (parsed_birth_date.month, parsed_birth_date.day)
            )
            if not (0 < updates["age"] < 120):
                raise HTTPException(status_code=400, detail="invalid_birth_date")
            updates["birth_date"] = birth_date
        else:
            updates["birth_date"] = None
            updates["age"] = None
    for key in ("chronic_conditions", "allergies", "medications"):
        if key in payload:
            value = payload[key]
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                raise HTTPException(status_code=400, detail=f"invalid_{key}")
            updates[key] = value
    for key in db.PROFILE_TEXT_FIELDS:
        if key in {"email", "birth_date"}:
            continue
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
def list_calendar(
    month: str | None = None,
    user_id: str = Depends(_require_client_user_id),
) -> dict:
    if month and not re.fullmatch(r"\d{4}-\d{2}", month):
        raise HTTPException(status_code=400, detail="invalid_month")
    return {"entries": db.list_calendar_entries(user_id, month)}


@app.post("/calendar")
def create_calendar_entry(
    payload: dict = Body(...),
    user_id: str = Depends(_require_client_user_id),
) -> dict:
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
def delete_calendar_entry(
    entry_id: str,
    user_id: str = Depends(_require_client_user_id),
) -> dict:
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
    profile = db.get_profile(user_id) or {}
    recipient_email = profile.get("email")
    if EMAIL_SERVICE.configured and recipient_email:
        try:
            EMAIL_SERVICE.send_confirmation(AppointmentEmail(
                recipient_email=recipient_email,
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
        "sent": "Email xác nhận đã được gửi tới địa chỉ trong hồ sơ của bạn.",
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
) -> dict:
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
def get_doctor_schedule(doctor_id: str) -> dict:
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
def book_doctor_slot(
    doctor_id: str,
    payload: dict = Body(...),
    user_id: str = Depends(_require_client_user_id),
) -> dict:
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
def list_cycle(user_id: str = Depends(_require_client_user_id)) -> dict:
    entries = db.list_cycle_entries(user_id)
    return {"entries": entries, "prediction": _cycle_prediction(entries)}


@app.post("/cycle")
def create_cycle_entry(
    payload: dict = Body(...),
    user_id: str = Depends(_require_client_user_id),
) -> dict:
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
def delete_cycle_entry(
    entry_id: str,
    user_id: str = Depends(_require_client_user_id),
) -> dict:
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
