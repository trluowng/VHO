"""Tra cứu bác sĩ theo chuyên khoa và lịch khám còn trống.

Tool này chỉ xem lịch, không tự đặt lịch. Khi dùng trong chatbot, model phải
hỏi ngày/giờ mong muốn trước; nếu khách nói ngày giờ nào cũng được thì truyền
``flexible_time=True``.
"""
from __future__ import annotations

import json
from typing import Any

import db
from tools._shared import ROOT, err, fold_text, terms

_DOCTORS_PATH = ROOT / "data" / "doctors.json"
_SCHEDULE_PATH = ROOT / "data" / "schedule_slots.json"

_doctor_index: list[dict[str, Any]] | None = None
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


def _slot_matches_preference(
    slot: dict[str, Any],
    *,
    preferred_date: str,
    preferred_time_slot: str,
    preferred_time_period: str,
) -> bool:
    if preferred_date and slot.get("visit_date") != preferred_date:
        return False
    if preferred_time_slot and slot.get("time_slot") != preferred_time_slot:
        return False
    if preferred_time_period:
        start = (slot.get("time_slot") or "").split("-", 1)[0]
        hour = int(start.split(":", 1)[0]) if ":" in start else -1
        if preferred_time_period == "morning" and not (0 <= hour < 12):
            return False
        if preferred_time_period == "afternoon" and hour < 12:
            return False
    return True


def _unbooked_slots(doctor_id: str, slots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    booked = db.list_booked_slots(doctor_id)
    return [slot for slot in slots if (slot.get("visit_date"), slot.get("time_slot")) not in booked]


def search_schedule(
    query: str = "",
    max_doctors: int = 3,
    max_slots_per_doctor: int = 3,
    preferred_date: str = "",
    preferred_time_slot: str = "",
    preferred_time_period: str = "",
    flexible_time: bool = False,
) -> dict[str, Any]:
    try:
        query = (query or "").strip()
        preferred_date = (preferred_date or "").strip()
        preferred_time_slot = (preferred_time_slot or "").strip()
        preferred_time_period = (preferred_time_period or "").strip()
        if preferred_time_period not in {"", "morning", "afternoon"}:
            preferred_time_period = ""

        if not query:
            return {
                "tool": "xem_lich_kham",
                "query": query,
                "items": [],
                "error": "missing_query",
                "note": "Thiếu chuyên khoa. Gọi lại với query là Tim mạch, Nhi, Da liễu hoặc Nội tổng quát.",
            }
        if not flexible_time and not preferred_date and not preferred_time_slot and not preferred_time_period:
            return {
                "tool": "xem_lich_kham",
                "query": query,
                "items": [],
                "error": "missing_time_preference",
                "note": (
                    "Chưa có ngày hoặc khung giờ khách muốn đặt. Hãy hỏi khách muốn khám ngày nào, "
                    "buổi/khung giờ nào; chỉ gọi lại tool khi đã có preferred_date, preferred_time_period "
                    "hoặc preferred_time_slot; hoặc flexible_time=true nếu khách nói ngày giờ nào cũng được."
                ),
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

        def matching_slots_for_doctor(doctor_id: str) -> list[dict[str, Any]]:
            open_slots = _unbooked_slots(doctor_id, slots_by_doctor.get(doctor_id, []))
            return [
                slot for slot in open_slots
                if _slot_matches_preference(
                    slot,
                    preferred_date=preferred_date,
                    preferred_time_slot=preferred_time_slot,
                    preferred_time_period=preferred_time_period,
                )
            ]

        scored.sort(key=lambda pair: (-pair[0], -len(matching_slots_for_doctor(pair[1]["doctor"]["id_doctor"]))))

        items = []
        for _, entry in scored:
            doc = entry["doctor"]
            doctor_slots = matching_slots_for_doctor(doc["id_doctor"])[:max_slots_per_doctor]
            if not doctor_slots:
                continue
            items.append({
                "ma_bac_si": doc["id_doctor"],
                "bac_si": f"{doc.get('full_name', '')} ({doc.get('degree', '')})",
                "chuyen_khoa": doc.get("specialty"),
                "lich_trong": [
                    {
                        "ngay": slot["visit_date"],
                        "khung_gio": slot["time_slot"],
                        "co_so": slot["campus"],
                        "khoa_phong": f"{slot['department']} - {slot['room']}",
                    }
                    for slot in doctor_slots
                ],
            })
            if len(items) >= max_doctors:
                break

        return {
            "tool": "xem_lich_kham",
            "query": query,
            "preferred_date": preferred_date or None,
            "preferred_time_slot": preferred_time_slot or None,
            "preferred_time_period": preferred_time_period or None,
            "flexible_time": flexible_time,
            "so_bac_si_khop": len(scored),
            "items": items,
            "note": None if items else "Không có lịch trống phù hợp với ngày/giờ khách mong muốn.",
        }
    except Exception as exc:
        return err("xem_lich_kham", exc)
