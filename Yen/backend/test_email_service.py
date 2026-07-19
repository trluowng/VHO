from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from email_service import AppointmentEmail, AppointmentEmailService, EmailSettings


class AppointmentEmailServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = EmailSettings(
            host="smtp.example.com",
            port=587,
            username="sender@example.com",
            password="app-password",
            from_email="sender@example.com",
            from_name="Yên · sức khỏe",
            use_tls=True,
            use_ssl=False,
            timeout_seconds=10,
        )
        self.appointment = AppointmentEmail(
            recipient_email="patient@example.com",
            patient_name="Nguyễn Minh An",
            doctor_name="BS. Trần Minh Đức",
            doctor_degree="BSCKII",
            specialty="Tim mạch",
            visit_date="2026-08-03",
            time_slot="09:00-09:30",
            location="Cơ sở 1 - Khoa Tim mạch - P.203",
            appointment_id="appointment-123",
        )

    def test_build_confirmation_contains_appointment_details(self) -> None:
        message = AppointmentEmailService(self.settings).build_confirmation_message(self.appointment)

        self.assertIn("Trần Minh Đức", message["Subject"])
        self.assertEqual(message["To"], "patient@example.com")
        self.assertIn("03/08/2026", message.get_body(preferencelist=("plain",)).get_content())
        self.assertIn("appointment-123", message.get_body(preferencelist=("html",)).get_content())

    @patch("email_service.smtplib.SMTP")
    def test_send_uses_starttls_login_and_send_message(self, smtp_mock: MagicMock) -> None:
        client = smtp_mock.return_value.__enter__.return_value

        AppointmentEmailService(self.settings).send_confirmation(self.appointment)

        smtp_mock.assert_called_once_with(host="smtp.example.com", port=587, timeout=10)
        client.starttls.assert_called_once()
        client.login.assert_called_once_with("sender@example.com", "app-password")
        client.send_message.assert_called_once()


if __name__ == "__main__":
    unittest.main()
