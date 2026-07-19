"""
Convert data/mock_hospital_dataset_v3.xlsx into plain JSON so the runtime
lookup tools don't need pandas/openpyxl as a live dependency.

Writes:
  - data/doctors.json        : list of doctor records (id_doctor, full_name,
                                specialty, degree, campus, department, room)
  - data/schedule_slots.json : flattened list of one entry per
                                (visit_date, campus, department, room, time_slot),
                                each with id_doctor + status (available/booked/
                                checked-in/completed/cancelled). Cell format in
                                the source sheet is
                                "appointment_id:...;id_user:...;id_doctor:...;status:..."

Mock/demo data (patient names in the source sheet are placeholders) -- see
data/README.md. Doctor full names are also placeholders in the source sheet
("Mock Doctor" for all 100 rows) -- this script replaces them with generated
Vietnamese names (deterministic seed, so reruns stay stable) since they are
shown directly to users in the "xem_lich_kham" tool results.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "mock_hospital_dataset_v3.xlsx"
DOCTORS_OUT = ROOT / "data" / "doctors.json"
SCHEDULE_OUT = ROOT / "data" / "schedule_slots.json"

TIME_SLOT_COLUMNS = [
    "07:00-08:00", "08:00-09:00", "09:00-10:00", "10:00-11:00", "11:00-12:00",
    "13:00-14:00", "14:00-15:00", "15:00-16:00", "16:00-17:00",
]

# Tên bác sĩ trong sheet gốc đều là placeholder "Mock Doctor" -- sinh tên tiếng
# Việt hợp lý để thay thế, seed cố định để chạy lại script vẫn ra tên giống cũ
# (không đổi tên bác sĩ mỗi lần build lại).
DOCTOR_NAME_SEED = 20260718
SURNAMES = [
    "Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng",
    "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý", "Đinh", "Đào", "Trịnh", "Mai",
]
GIVEN_NAMES = [
    "Văn Minh", "Đình Khoa", "Quốc Anh", "Hữu Phúc", "Đức Thắng", "Xuân Bách",
    "Thành Đạt", "Trọng Nghĩa", "Công Danh", "Anh Tuấn", "Việt Hùng", "Tuấn Kiệt",
    "Bảo Long", "Gia Huy", "Minh Quân", "Thị Lan", "Ngọc Hà", "Thu Trang",
    "Thanh Tâm", "Mai Anh", "Thùy Linh", "Hồng Nhung", "Kim Ngân", "Bích Ngọc",
    "Diệu Linh", "Thảo Vy", "Hải Yến", "Phương Thảo", "Minh Châu", "Thu Hương",
]


def _generate_doctor_names(count: int) -> list[str]:
    rng = random.Random(DOCTOR_NAME_SEED)
    all_combos = [f"{s} {g}" for s in SURNAMES for g in GIVEN_NAMES]
    return rng.sample(all_combos, count)


def _parse_cell(cell: str) -> dict[str, str]:
    fields = {}
    for part in str(cell).split(";"):
        if ":" not in part:
            continue
        key, _, value = part.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def build() -> None:
    xls = pd.ExcelFile(SRC)

    doctors_df = pd.read_excel(xls, "doctors")
    doctors = doctors_df.to_dict(orient="records")
    generated_names = _generate_doctor_names(len(doctors))
    for doctor, name in zip(doctors, generated_names):
        doctor["full_name"] = name
    DOCTORS_OUT.write_text(json.dumps(doctors, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {DOCTORS_OUT} with {len(doctors)} doctors.")

    schedule_df = pd.read_excel(xls, "schedule")
    slots: list[dict] = []
    for _, row in schedule_df.iterrows():
        visit_date = str(row["visit_date"])[:10]
        for time_slot in TIME_SLOT_COLUMNS:
            fields = _parse_cell(row[time_slot])
            slots.append({
                "visit_date": visit_date,
                "campus": row["campus"],
                "department": row["department"],
                "room": row["room"],
                "time_slot": time_slot,
                "id_doctor": fields.get("id_doctor", ""),
                "status": fields.get("status", ""),
                "appointment_id": fields.get("appointment_id", "none"),
            })
    SCHEDULE_OUT.write_text(json.dumps(slots, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {SCHEDULE_OUT} with {len(slots)} slot entries.")


if __name__ == "__main__":
    build()
