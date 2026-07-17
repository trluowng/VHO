"""Tài khoản demo với hồ sơ bệnh lý đa dạng — để demo/QA tính năng "AI dùng hồ sơ
bệnh nhân để suy luận" mà không phải đăng ký + điền hồ sơ thủ công mỗi lần.

Chạy tự động (idempotent) từ server.py sau db.init_db(). SQLite trên free plan
là tạm thời (mất khi redeploy) nên seed lại tự động mỗi lần khởi động, không
cần script tách riêng để nhớ chạy tay.
"""
from __future__ import annotations

from datetime import date, timedelta

import db
from auth import hash_password
from chat import now_iso

DEMO_PASSWORD = "Demo123456"

DEMO_ACCOUNTS = [
    {
        "email": "demo1@yen.vn",
        "age": 16,
        "gender": "nu",
        "chronic_conditions": [],
        "allergies": [],
        "medications": [],
        "cycle_entry_days_ago": 5,
        "label": "Nữ vị thành niên — demo dậy thì + tab chu kỳ kinh nguyệt",
    },
    {
        "email": "demo2@yen.vn",
        "age": 45,
        "gender": "nam",
        "chronic_conditions": ["đái tháo đường type 2"],
        "allergies": [],
        "medications": ["Metformin"],
        "label": "Nam trung niên có bệnh nền — demo tham chiếu bệnh mạn tính",
    },
    {
        "email": "demo3@yen.vn",
        "age": 30,
        "gender": "nu",
        "chronic_conditions": [],
        "allergies": ["đậu phộng", "hải sản"],
        "medications": [],
        "label": "Nữ có dị ứng — demo cảnh giác phản ứng dị ứng",
    },
    {
        "email": "demo4@yen.vn",
        "age": 70,
        "gender": "nam",
        "chronic_conditions": ["cao huyết áp"],
        "allergies": [],
        "medications": ["Amlodipine"],
        "label": "Nam cao tuổi đang dùng thuốc huyết áp — demo tham chiếu thuốc + tuổi già",
    },
    {
        "email": "demo5@yen.vn",
        "age": 50,
        "gender": "nu",
        "chronic_conditions": [],
        "allergies": [],
        "medications": [],
        "label": "Nữ tuổi tiền mãn kinh — demo suy luận theo độ tuổi",
    },
]


def seed_demo_accounts() -> None:
    for acc in DEMO_ACCOUNTS:
        if db.get_user_by_email(acc["email"]):
            continue

        created_at = now_iso()
        password_hash, salt = hash_password(DEMO_PASSWORD)
        user_id = db.create_user(acc["email"], password_hash, salt, created_at)
        db.create_profile(user_id, acc["age"], acc["gender"], created_at)
        db.update_profile(
            user_id,
            {
                "chronic_conditions": acc["chronic_conditions"],
                "allergies": acc["allergies"],
                "medications": acc["medications"],
            },
            created_at,
        )

        cycle_days_ago = acc.get("cycle_entry_days_ago")
        if cycle_days_ago is not None:
            period_start = (date.today() - timedelta(days=cycle_days_ago)).isoformat()
            db.add_cycle_entry(user_id, period_start, None, created_at)

        print(f"🌱 demo account: {acc['email']} / {DEMO_PASSWORD} — {acc['label']}")
