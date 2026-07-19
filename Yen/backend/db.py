"""SQLite persistence: accounts, health profile, calendar, cycle tracking.

Kept intentionally simple (stdlib sqlite3, no ORM) — this is a prototype
backend, not a production data layer. Swap for Postgres/SQLAlchemy if the
product grows past a single-instance demo.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "app.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS health_profiles (
    user_id TEXT PRIMARY KEY REFERENCES users(id),
    age INTEGER,
    gender TEXT,
    chronic_conditions TEXT NOT NULL DEFAULT '[]',
    allergies TEXT NOT NULL DEFAULT '[]',
    medications TEXT NOT NULL DEFAULT '[]',
    full_name TEXT,
    birth_date TEXT,
    phone TEXT,
    address TEXT,
    occupation TEXT,
    blood_type TEXT,
    insurance_status TEXT,
    insurance_number TEXT,
    emergency_contact_name TEXT,
    emergency_contact_relationship TEXT,
    emergency_contact_phone TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cycle_entries (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    period_start_date TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS calendar_entries (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    entry_date TEXT NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    note TEXT,
    time_start TEXT,
    time_end TEXT,
    doctor TEXT,
    location TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cycle_user ON cycle_entries(user_id, period_start_date);
CREATE INDEX IF NOT EXISTS idx_calendar_user ON calendar_entries(user_id, entry_date);
"""

# Cột thêm sau lần tạo bảng đầu tiên — DB cũ trên máy dev cần ALTER TABLE để có đủ cột.
TABLE_MIGRATIONS = {
    "calendar_entries": [
        "time_start TEXT", "time_end TEXT", "doctor TEXT", "location TEXT",
        "date_end TEXT", "times TEXT", "doctor_id TEXT", "time_slot TEXT",
    ],
    "health_profiles": [
        "full_name TEXT", "birth_date TEXT", "phone TEXT", "address TEXT", "occupation TEXT",
        "blood_type TEXT", "insurance_status TEXT", "insurance_number TEXT",
        "emergency_contact_name TEXT", "emergency_contact_relationship TEXT", "emergency_contact_phone TEXT",
    ],
}


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        for table, column_defs in TABLE_MIGRATIONS.items():
            existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
            for column_def in column_defs:
                column_name = column_def.split()[0]
                if column_name not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")


def new_id() -> str:
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def create_user(email: str, password_hash: str, password_salt: str, created_at: str) -> str:
    user_id = new_id()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, password_salt, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, email, password_hash, password_salt, created_at),
        )
    return user_id


def get_user_by_email(email: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def get_user_by_id(user_id: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


# ---------------------------------------------------------------------------
# Health profile
# ---------------------------------------------------------------------------

PROFILE_TEXT_FIELDS = (
    "full_name", "birth_date", "phone", "address", "occupation", "blood_type",
    "insurance_status", "insurance_number",
    "emergency_contact_name", "emergency_contact_relationship", "emergency_contact_phone",
)


def create_profile(user_id: str, age: int | None, gender: str | None, updated_at: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO health_profiles (user_id, age, gender, updated_at) VALUES (?, ?, ?, ?)",
            (user_id, age, gender, updated_at),
        )


def get_profile(user_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM health_profiles WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return None
    profile = {
        "age": row["age"],
        "gender": row["gender"],
        "chronic_conditions": json.loads(row["chronic_conditions"]),
        "allergies": json.loads(row["allergies"]),
        "medications": json.loads(row["medications"]),
        "updated_at": row["updated_at"],
    }
    for key in PROFILE_TEXT_FIELDS:
        profile[key] = row[key]
    return profile


def update_profile(user_id: str, updates: dict, updated_at: str) -> None:
    fields, values = [], []
    for key in ("age", "gender"):
        if key in updates:
            fields.append(f"{key} = ?")
            values.append(updates[key])
    for key in ("chronic_conditions", "allergies", "medications"):
        if key in updates:
            fields.append(f"{key} = ?")
            values.append(json.dumps(updates[key], ensure_ascii=False))
    for key in PROFILE_TEXT_FIELDS:
        if key in updates:
            fields.append(f"{key} = ?")
            values.append(updates[key])
    if not fields:
        return
    fields.append("updated_at = ?")
    values.append(updated_at)
    values.append(user_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE health_profiles SET {', '.join(fields)} WHERE user_id = ?", values)


# ---------------------------------------------------------------------------
# Cycle tracking
# ---------------------------------------------------------------------------

def add_cycle_entry(user_id: str, period_start_date: str, note: str | None, created_at: str) -> str:
    entry_id = new_id()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO cycle_entries (id, user_id, period_start_date, note, created_at) VALUES (?, ?, ?, ?, ?)",
            (entry_id, user_id, period_start_date, note, created_at),
        )
    return entry_id


def list_cycle_entries(user_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM cycle_entries WHERE user_id = ? ORDER BY period_start_date DESC",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_cycle_entry(user_id: str, entry_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM cycle_entries WHERE id = ? AND user_id = ?", (entry_id, user_id))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Health calendar
# ---------------------------------------------------------------------------

def add_calendar_entry(
    user_id: str,
    entry_date: str,
    entry_type: str,
    title: str,
    note: str | None,
    created_at: str,
    *,
    time_start: str | None = None,
    time_end: str | None = None,
    doctor: str | None = None,
    location: str | None = None,
    date_end: str | None = None,
    times: list[str] | None = None,
    doctor_id: str | None = None,
    time_slot: str | None = None,
) -> str:
    entry_id = new_id()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO calendar_entries "
            "(id, user_id, entry_date, type, title, note, time_start, time_end, doctor, location, "
            "date_end, times, doctor_id, time_slot, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                entry_id, user_id, entry_date, entry_type, title, note, time_start, time_end, doctor, location,
                date_end, json.dumps(times, ensure_ascii=False) if times else None, doctor_id, time_slot, created_at,
            ),
        )
    return entry_id


def find_booking(doctor_id: str, entry_date: str, time_slot: str) -> sqlite3.Row | None:
    """Đợt đặt trùng (bất kỳ user nào) trên đúng bác sĩ/ngày/khung giờ -- dùng để
    chặn double-booking và loại slot đã có người đặt khỏi danh sách lịch trống."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM calendar_entries WHERE doctor_id = ? AND entry_date = ? AND time_slot = ?",
            (doctor_id, entry_date, time_slot),
        ).fetchone()


def list_booked_slots(doctor_id: str) -> set[tuple[str, str]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT entry_date, time_slot FROM calendar_entries WHERE doctor_id = ? AND time_slot IS NOT NULL",
            (doctor_id,),
        ).fetchall()
    return {(row["entry_date"], row["time_slot"]) for row in rows}


def _parse_entry_row(row: sqlite3.Row) -> dict:
    entry = dict(row)
    entry["times"] = json.loads(entry["times"]) if entry.get("times") else []
    return entry


def list_calendar_entries(user_id: str, month: str | None = None) -> list[dict]:
    with get_conn() as conn:
        if month:
            # Một nhắc thuốc nhiều ngày (entry_date..date_end) có thể bắt đầu ở
            # tháng trước nhưng vẫn còn hiệu lực trong tháng đang xem -- so khớp
            # theo khoảng ngày chồng lấn với tháng, không chỉ entry_date LIKE.
            month_start = f"{month}-01"
            month_end = f"{month}-31"
            rows = conn.execute(
                "SELECT * FROM calendar_entries WHERE user_id = ? AND entry_date <= ? "
                "AND COALESCE(date_end, entry_date) >= ? ORDER BY entry_date",
                (user_id, month_end, month_start),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM calendar_entries WHERE user_id = ? ORDER BY entry_date", (user_id,)
            ).fetchall()
    return [_parse_entry_row(row) for row in rows]


def delete_calendar_entry(user_id: str, entry_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM calendar_entries WHERE id = ? AND user_id = ?", (entry_id, user_id))
        return cur.rowcount > 0
