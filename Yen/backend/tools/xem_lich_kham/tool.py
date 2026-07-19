"""Tra cứu bác sĩ theo chuyên khoa và lịch khám còn trống tại Bệnh viện Tim Hà Nội.

Nguồn: data/doctors.json + data/schedule_slots.json — sinh sẵn từ
data/structured/mock_hospital_dataset_v4.xlsx (dữ liệu mock/demo, xem
data/README.md và backend/scripts/build_schedule.py) bằng script
build_schedule.py, để runtime không cần pandas/openpyxl.

Chỉ tra cứu và gợi ý — KHÔNG tự đặt lịch (khách xác nhận đặt lịch qua CTA
trên giao diện, ngoài phạm vi tool này).
"""
from __future__ import annotations

import json
from typing import Any

from tools._shared import ROOT, err, fold_text, terms

_DOCTORS_PATH = ROOT / "data" / "doctors.json"
_SCHEDULE_PATH = ROOT / "data" / "schedule_slots.json"

_doctor_index: list[dict[str, Any]] | None = None  # each: {doctor, term_set, folded}
_slots_by_doctor: dict[str, list[dict[str, Any]]] | None = None


def _load_doctor_index() -> list[dict[str, Any]]:
    global _doctor_index
    if _doctor_index is None:
        doctors = json.loads(_DOCTORS_PATH.read_text(encoding="utf-8"))
        _doctor_index = []
        for doc in doctors:
            searchable = f"{doc.get('specialty', '')} {doc.get('department', '')} {doc.get('degree', '')}"
            _doctor_index.append({
                "doctor": doc,
                "term_set": terms(searchable),
                "folded": fold_text(searchable),
            })
    return _doctor_index


def _load_slots_by_doctor() -> dict[str, list[dict[str, Any]]]:
    global _slots_by_doctor
    if _slots_by_doctor is None:
        slots = json.loads(_SCHEDULE_PATH.read_text(encoding="utf-8"))
        by_doctor: dict[str, list[dict[str, Any]]] = {}
        for slot in slots:
            if slot.get("status") != "available":
                continue
            by_doctor.setdefault(slot["id_doctor"], []).append(slot)
        for doctor_slots in by_doctor.values():
            doctor_slots.sort(key=lambda s: (s["visit_date"], s["time_slot"]))
        _slots_by_doctor = by_doctor
    return _slots_by_doctor


def search_schedule(query: str = "", max_doctors: int = 3, max_slots_per_doctor: int = 3) -> dict[str, Any]:
    try:
        query = (query or "").strip()
        if not query:
            return {
                "tool": "xem_lich_kham", "query": query, "items": [],
                "error": "missing_query",
                "note": "LỖI: tham số 'query' bị để trống. Hãy GỌI LẠI tool xem_lich_kham ngay với query = một trong 4 chuyên khoa: 'Tim mạch', 'Nhi', 'Da liễu', 'Nội tổng quát'.",
            }

        query_terms = terms(query)
        folded_query = fold_text(query)
        slots_by_doctor = _load_slots_by_doctor()

        scored: list[tuple[int, dict[str, Any]]] = []
        for entry in _load_doctor_index():
            score = len(query_terms & entry["term_set"]) * 2
            if folded_query and folded_query in entry["folded"]:
                score += 3
            if score > 0:
                scored.append((score, entry))
        # Ưu tiên điểm khớp cao hơn, rồi tới bác sĩ có nhiều lịch trống hơn.
        scored.sort(key=lambda pair: (-pair[0], -len(slots_by_doctor.get(pair[1]["doctor"]["id_doctor"], []))))

        items = []
        for _, entry in scored[:max_doctors]:
            doc = entry["doctor"]
            doctor_slots = slots_by_doctor.get(doc["id_doctor"], [])[:max_slots_per_doctor]
            items.append({
                "ma_bac_si": doc["id_doctor"],
                "bac_si": f"{doc.get('full_name', '')} ({doc.get('degree', '')})",
                "chuyen_khoa": doc.get("specialty"),
                # Cơ sở/khoa/phòng lấy theo TỪNG lịch trống (không lấy từ hồ sơ tĩnh
                # của bác sĩ) -- dữ liệu mock cho thấy cùng 1 mã bác sĩ có thể xuất
                # hiện ở lịch của cả 2 cơ sở cùng khung giờ, nên hồ sơ tĩnh không
                # đáng tin cho việc xác định địa điểm khám thực tế của 1 lịch trống.
                "lich_trong": [
                    {
                        "ngay": s["visit_date"],
                        "khung_gio": s["time_slot"],
                        "co_so": s["campus"],
                        "khoa_phong": f"{s['department']} - {s['room']}",
                    }
                    for s in doctor_slots
                ],
            })
        return {"tool": "xem_lich_kham", "query": query, "so_bac_si_khop": len(scored), "items": items}
    except Exception as exc:
        return err("xem_lich_kham", exc)
