import unittest

import server


def _profile(stage="done"):
    return {
        "stage": stage,
        "symptoms": [{"label": "Đau bụng", "specific": True}],
        "confidence": 82,
        "confTier": "high",
        "missing": [],
        "facts": {"duration": "2 ngày", "severity": "vừa", "associated": True},
    }


def _result_events(level="amber"):
    return [
        {
            "type": "result",
            "triage": {"level": level, "reason": "Đau bụng kéo dài hai ngày."},
        },
        {
            "type": "question",
            "text": "Bạn có muốn mình tìm bác sĩ và lịch trống để đặt lịch không?",
            "quick": ["Có", "Để sau"],
        },
    ]


class TriagePacingTests(unittest.TestCase):
    def test_first_detailed_message_is_not_concluded_immediately(self):
        events, profile = server._delay_premature_triage_result(
            _result_events(), _profile(), [], "Tôi đã mô tả đầy đủ triệu chứng", None
        )

        self.assertNotIn("result", [event["type"] for event in events])
        self.assertEqual(events[-1]["type"], "question")
        self.assertEqual(profile["stage"], "questioning")

    def test_one_answered_question_is_still_not_enough(self):
        history = [
            {"role": "user", "text": "Tôi bị đau bụng hai ngày"},
            {"role": "ai", "text": "Triệu chứng đang đỡ hay nặng lên?"},
        ]
        events, profile = server._delay_premature_triage_result(
            _result_events(), _profile(), history, "Gần như không đổi", _profile("questioning")
        )

        self.assertNotIn("result", [event["type"] for event in events])
        self.assertEqual(profile["stage"], "questioning")

    def test_two_answered_questions_allow_conclusion(self):
        history = [
            {"role": "user", "text": "Tôi bị đau bụng hai ngày"},
            {"role": "ai", "text": "Triệu chứng đang đỡ hay nặng lên?"},
            {"role": "user", "text": "Không đổi"},
            {"role": "ai", "text": "Có ảnh hưởng ăn uống hoặc sinh hoạt không?"},
        ]
        events, profile = server._delay_premature_triage_result(
            _result_events(), _profile(), history, "Ảnh hưởng một phần", _profile("questioning")
        )

        self.assertIn("result", [event["type"] for event in events])
        self.assertEqual(profile["stage"], "done")

    def test_emergency_result_is_never_delayed(self):
        events, _ = server._delay_premature_triage_result(
            _result_events("red"), _profile("emergency"), [], "Tôi khó thở", None
        )
        self.assertIn("result", [event["type"] for event in events])

    def test_user_can_request_immediate_assessment(self):
        events, _ = server._delay_premature_triage_result(
            _result_events(), _profile(), [], "Không cần hỏi thêm, kết luận luôn", None
        )
        self.assertIn("result", [event["type"] for event in events])

    def test_repeated_question_is_replaced_with_new_followup(self):
        events = [
            {"type": "message", "text": "Mình đã ghi nhận."},
            {
                "type": "question",
                "text": "Đau bụng có cảm giác như thế nào?",
                "quick": ["Âm ỉ", "Quặn", "Nhói"],
            },
        ]
        profile = _profile("questioning")

        delayed, _ = server._delay_premature_triage_result(
            events,
            profile,
            [],
            "Tôi đau bụng âm ỉ mức vừa trong 2 ngày",
            None,
        )

        self.assertNotIn("cảm giác như thế nào", delayed[-1]["text"])
        self.assertIn("đỡ dần", delayed[-1]["text"])

    def test_booking_question_before_conclusion_is_replaced(self):
        events = [
            {"type": "message", "text": "Mình đã ghi nhận."},
            {
                "type": "question",
                "text": "Bạn có muốn mình tìm bác sĩ và lịch trống để đặt lịch không?",
                "quick": ["Có", "Để sau"],
            },
        ]
        history = [
            {"role": "user", "text": "Tôi đau bụng hai ngày"},
            {"role": "ai", "text": "Triệu chứng đang đỡ hay nặng lên?"},
        ]

        delayed, _ = server._delay_premature_triage_result(
            events,
            _profile("questioning"),
            history,
            "Gần như không đổi",
            _profile("questioning"),
        )

        self.assertNotIn("đặt lịch", delayed[-1]["text"])
        self.assertIn("ảnh hưởng", delayed[-1]["text"])


if __name__ == "__main__":
    unittest.main()
