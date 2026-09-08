import unittest

import server
from providers.openai_provider import _TRIAGE_TRIAGE_SCHEMA


class PreliminaryAssessmentTests(unittest.TestCase):
    def test_openai_schema_requires_preliminary_assessment(self):
        self.assertIn("preliminaryAssessment", _TRIAGE_TRIAGE_SCHEMA["properties"])
        self.assertIn("preliminaryAssessment", _TRIAGE_TRIAGE_SCHEMA["required"])

    def test_wet_dream_at_fourteen_is_framed_as_puberty_physiology(self):
        events = [
            {
                "type": "result",
                "triage": {
                    "level": "green",
                    "preliminaryAssessment": "",
                    "reason": "Không có dấu hiệu bất thường.",
                },
            }
        ]

        result = server._enforce_preliminary_assessment(
            events,
            [{"role": "user", "text": "Con trai tôi 14 tuổi đang mộng tinh"}],
            "Cháu không đau, không buốt tiểu và không có máu.",
            {"relationship": "son", "age": 14, "gender": "nam"},
        )

        assessment = result[0]["triage"]["preliminaryAssessment"]
        self.assertIn("sinh lý", assessment)
        self.assertIn("tuổi dậy thì", assessment)
        self.assertIn("chưa gợi ý bệnh lý", assessment)

    def test_concerning_wet_dream_is_not_framed_as_simply_normal(self):
        events = [
            {
                "type": "result",
                "triage": {"level": "amber", "preliminaryAssessment": "", "reason": "Có đau."},
            }
        ]
        result = server._enforce_preliminary_assessment(
            events,
            [],
            "Con trai tôi 14 tuổi mộng tinh kèm đau và buốt tiểu",
            {"relationship": "son", "age": 14, "gender": "nam"},
        )

        assessment = result[0]["triage"]["preliminaryAssessment"]
        self.assertIn("cần được đánh giá trực tiếp", assessment)
        self.assertNotIn("chưa gợi ý bệnh lý", assessment)

    def test_wet_dream_followups_screen_warning_signs_then_pattern(self):
        first = server._next_required_followup([], "Con trai tôi 14 tuổi đang mộng tinh")
        self.assertIn("đau hoặc sưng", first["text"])
        self.assertIn("Không có", first["quick"])

        history = [
            {"role": "user", "text": "Con trai tôi 14 tuổi đang mộng tinh"},
            {"role": "ai", "text": first["text"]},
        ]
        second = server._next_required_followup(history, "Không có")
        self.assertIn("chỉ xảy ra khi ngủ", second["text"])
        self.assertIn("Có cả lúc thức", second["quick"])

    def test_missing_quick_replies_are_added_to_puberty_question(self):
        events = [
            {
                "type": "question",
                "text": "Mộng tinh chỉ xảy ra khi ngủ hay cả lúc thức và ảnh hưởng giấc ngủ thế nào?",
                "quick": [],
            }
        ]
        result = server._enforce_question_quick_replies(
            events,
            [{"role": "user", "text": "Con trai tôi 14 tuổi có mộng tinh"}],
            "Không có đau hay buốt tiểu",
        )

        self.assertEqual(len(result[0]["quick"]), 3)
        self.assertIn("Có cả lúc thức", result[0]["quick"])


if __name__ == "__main__":
    unittest.main()
