import unittest
from unittest.mock import patch

import server


class PatientContextTests(unittest.TestCase):
    def tearDown(self):
        server._LAST_PATIENT_CONTEXT.clear()

    def test_extracts_child_relationship_age_and_gender(self):
        self.assertEqual(
            server._explicit_patient_hint("Con trai tôi 14 tuổi bị đau bụng"),
            {"relationship": "son", "age": 14, "gender": "nam"},
        )

    def test_child_context_survives_short_follow_up(self):
        current = {"relationship": "son", "age": 14, "gender": "nam"}
        self.assertEqual(server._sanitize_patient_context({}, current), current)

    @patch.object(server.db, "update_profile")
    @patch.object(server.db, "get_profile")
    def test_child_facts_never_overwrite_account_owner(self, get_profile, update_profile):
        owner = {"age": 40, "gender": "nu", "chronic_conditions": ["đau nửa đầu"]}
        get_profile.return_value = owner
        parsed = {
            "patient_context": {
                "relationship": "son",
                "age": 14,
                "gender": "nam",
                "chronic_conditions": [],
            },
            # Simulate a bad model response trying to write child facts as owner facts.
            "health_profile_updates": {"age": 14, "gender": "nam"},
        }

        health_profile, patient_context = server._apply_extracted_context(
            "owner-id-12345678", "child-session", parsed
        )

        update_profile.assert_not_called()
        self.assertEqual(health_profile, owner)
        self.assertEqual(patient_context["relationship"], "son")
        self.assertEqual(patient_context["age"], 14)
        self.assertEqual(patient_context["gender"], "nam")

    @patch.object(server.db, "update_profile")
    @patch.object(server.db, "get_profile")
    def test_main_answer_cannot_change_resolved_child_to_self(self, get_profile, update_profile):
        get_profile.return_value = {"age": 40, "gender": "nu"}
        server._LAST_PATIENT_CONTEXT["child-session"] = {
            "relationship": "son", "age": 14, "gender": "nam"
        }
        parsed = {
            "patient_context": {"relationship": "self", "age": 40, "gender": "nu"},
            "health_profile_updates": {"age": 14, "gender": "nam"},
        }

        _, patient_context = server._apply_extracted_context(
            "owner-id-12345678",
            "child-session",
            parsed,
            {"relationship": "son", "age": 14, "gender": "nam"},
        )

        update_profile.assert_not_called()
        self.assertEqual(patient_context["relationship"], "son")
        self.assertEqual(patient_context["age"], 14)
        self.assertEqual(patient_context["gender"], "nam")

    def test_explicit_self_message_can_switch_subject(self):
        self.assertEqual(
            server._explicit_patient_hint("Còn tôi bị đau đầu từ sáng"),
            {"relationship": "self"},
        )

    def test_child_age_is_used_in_reason_and_pediatric_booking(self):
        events = [
            {"type": "result", "triage": {"reason": "Đau bụng và tiêu chảy kéo dài hai ngày."}},
            {
                "type": "question",
                "text": "Bạn có muốn tìm bác sĩ Nội tổng quát để đặt lịch không?",
            },
        ]

        result = server._enforce_patient_context_on_events(
            events,
            {"relationship": "son", "age": 14, "gender": "nam"},
        )

        self.assertIn("14 tuổi", result[0]["triage"]["reason"])
        self.assertIn("nhi khoa", result[0]["triage"]["reason"])
        self.assertIn("chuyên khoa Nhi", result[1]["text"])

    @patch.object(server.PROVIDER, "complete")
    @patch.object(server.db, "get_profile")
    def test_explicit_child_uses_only_main_llm_call(self, get_profile, complete):
        owner = {"age": 40, "gender": "nu"}
        get_profile.return_value = owner

        health_profile, patient_context = server._extract_context_before_triage(
            "owner-id-12345678",
            "child-session",
            [],
            "Con trai tôi 14 tuổi bị đau bụng",
        )

        complete.assert_not_called()
        self.assertEqual(health_profile, owner)
        self.assertEqual(patient_context, {"relationship": "son", "age": 14, "gender": "nam"})


if __name__ == "__main__":
    unittest.main()
