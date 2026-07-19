"""SMTP email notifications for confirmed doctor appointments."""

from __future__ import annotations

import html
import os
import smtplib
import ssl
from dataclasses import dataclass
from datetime import date
from email.message import EmailMessage
from email.utils import formataddr


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _clean_header(value: str) -> str:
    return " ".join(value.replace("\r", " ").replace("\n", " ").split())


def _format_visit_date(value: str) -> str:
    parsed = date.fromisoformat(value)
    weekdays = ("Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật")
    return f"{weekdays[parsed.weekday()]}, ngày {parsed:%d/%m/%Y}"


@dataclass(frozen=True)
class EmailSettings:
    host: str
    port: int
    username: str
    password: str
    from_email: str
    from_name: str
    use_tls: bool
    use_ssl: bool
    timeout_seconds: int

    @property
    def configured(self) -> bool:
        has_auth = not self.username or bool(self.password)
        return bool(self.host and self.from_email and has_auth)

    @classmethod
    def from_env(cls) -> "EmailSettings":
        username = os.getenv("SMTP_USERNAME", "").strip()
        return cls(
            host=os.getenv("SMTP_HOST", "").strip(),
            port=_env_int("SMTP_PORT", 587),
            username=username,
            password=os.getenv("SMTP_PASSWORD", ""),
            from_email=os.getenv("SMTP_FROM_EMAIL", "").strip() or username,
            from_name=os.getenv("SMTP_FROM_NAME", "Yên · sức khỏe").strip(),
            use_tls=_env_bool("SMTP_USE_TLS", True),
            use_ssl=_env_bool("SMTP_USE_SSL", False),
            timeout_seconds=_env_int("SMTP_TIMEOUT_SECONDS", 10),
        )


@dataclass(frozen=True)
class AppointmentEmail:
    recipient_email: str
    patient_name: str
    doctor_name: str
    doctor_degree: str
    specialty: str
    visit_date: str
    time_slot: str
    location: str
    appointment_id: str


class AppointmentEmailService:
    def __init__(self, settings: EmailSettings):
        self.settings = settings

    @classmethod
    def from_env(cls) -> "AppointmentEmailService":
        return cls(EmailSettings.from_env())

    @property
    def configured(self) -> bool:
        return self.settings.configured

    def build_confirmation_message(self, appointment: AppointmentEmail) -> EmailMessage:
        recipient = _clean_header(appointment.recipient_email)
        if "@" not in recipient:
            raise ValueError("invalid_recipient_email")

        visit_date = _format_visit_date(appointment.visit_date)
        doctor_name = _clean_header(appointment.doctor_name)
        patient_name = appointment.patient_name.strip() or "Quý khách"

        message = EmailMessage()
        message["Subject"] = f"[Yên] Xác nhận lịch khám với {doctor_name}"
        message["From"] = formataddr((_clean_header(self.settings.from_name), self.settings.from_email))
        message["To"] = recipient

        message.set_content(
            f"""Xin chào {patient_name},

Lịch khám của bạn đã được xác nhận thành công.

Bác sĩ: {appointment.doctor_name} ({appointment.doctor_degree})
Chuyên khoa: {appointment.specialty}
Thời gian: {visit_date}, {appointment.time_slot}
Địa điểm: {appointment.location}
Mã lịch hẹn: {appointment.appointment_id}

Vui lòng đến sớm 15 phút và mang theo giấy tờ tùy thân, thẻ BHYT nếu có.

Trân trọng,
Yên · AI y tế cá nhân
"""
        )

        safe = {
            "patient_name": html.escape(patient_name),
            "doctor_name": html.escape(appointment.doctor_name),
            "doctor_degree": html.escape(appointment.doctor_degree),
            "specialty": html.escape(appointment.specialty),
            "visit_date": html.escape(visit_date),
            "time_slot": html.escape(appointment.time_slot),
            "location": html.escape(appointment.location),
            "appointment_id": html.escape(appointment.appointment_id),
        }
        message.add_alternative(
            f"""<!doctype html>
<html lang="vi">
  <body style="margin:0;background:#eef6f7;font-family:Arial,sans-serif;color:#203a43">
    <div style="max-width:620px;margin:28px auto;padding:0 16px">
      <div style="padding:24px 28px;border-radius:18px 18px 0 0;background:linear-gradient(135deg,#35a7bb,#145a68);color:#fff">
        <div style="font-size:24px;font-weight:700">Yên · sức khỏe</div>
        <div style="margin-top:5px;font-size:13px;opacity:.85">Xác nhận lịch khám thành công</div>
      </div>
      <div style="padding:28px;border:1px solid #d7e8ea;border-top:0;border-radius:0 0 18px 18px;background:#fff">
        <p style="margin:0 0 18px">Xin chào <strong>{safe['patient_name']}</strong>,</p>
        <p style="margin:0 0 20px;color:#52707a">Yên đã ghi nhận lịch khám của bạn với thông tin sau:</p>
        <table role="presentation" style="width:100%;border-collapse:collapse;background:#f3f9fa;border-radius:12px">
          <tr><td style="padding:12px 14px;color:#6b858d">Bác sĩ</td><td style="padding:12px 14px;font-weight:700">{safe['doctor_name']} ({safe['doctor_degree']})</td></tr>
          <tr><td style="padding:12px 14px;color:#6b858d">Chuyên khoa</td><td style="padding:12px 14px">{safe['specialty']}</td></tr>
          <tr><td style="padding:12px 14px;color:#6b858d">Thời gian</td><td style="padding:12px 14px">{safe['visit_date']} · {safe['time_slot']}</td></tr>
          <tr><td style="padding:12px 14px;color:#6b858d">Địa điểm</td><td style="padding:12px 14px">{safe['location']}</td></tr>
          <tr><td style="padding:12px 14px;color:#6b858d">Mã lịch hẹn</td><td style="padding:12px 14px;font-family:monospace">{safe['appointment_id']}</td></tr>
        </table>
        <div style="margin-top:20px;padding:14px;border-radius:10px;background:#fff6e8;color:#8a622d;font-size:13px;line-height:1.5">
          Vui lòng đến sớm 15 phút và mang theo giấy tờ tùy thân, thẻ BHYT nếu có.
        </div>
        <p style="margin:24px 0 0;color:#6b858d;font-size:12px">Đây là email tự động từ Yên · AI y tế cá nhân.</p>
      </div>
    </div>
  </body>
</html>""",
            subtype="html",
        )
        return message

    def send_confirmation(self, appointment: AppointmentEmail) -> None:
        if not self.configured:
            raise RuntimeError("smtp_not_configured")

        message = self.build_confirmation_message(appointment)
        settings = self.settings
        smtp_class = smtplib.SMTP_SSL if settings.use_ssl else smtplib.SMTP
        kwargs = {"host": settings.host, "port": settings.port, "timeout": settings.timeout_seconds}
        if settings.use_ssl:
            kwargs["context"] = ssl.create_default_context()

        with smtp_class(**kwargs) as client:
            if not settings.use_ssl:
                client.ehlo()
                if settings.use_tls:
                    client.starttls(context=ssl.create_default_context())
                    client.ehlo()
            if settings.username:
                client.login(settings.username, settings.password)
            client.send_message(message)
