import unittest
from streamlit.testing.v1 import AppTest
from pathlib import Path


class UITests(unittest.TestCase):
    def test_comparison_partial_failure_and_reset(self):
        from unittest.mock import patch
        from ai_email_security.comparison import compare
        from ai_email_security.ollama_client import EngineUnavailable
        from tests.test_demo import VALID

        with (
            patch(
                "ai_email_security.analyzer.analyze_with_model",
                side_effect=EngineUnavailable(),
            ),
            patch(
                "ai_email_security.keras_client.analyze_with_keras",
                return_value=(
                    VALID,
                    {
                        "model": "fake",
                        "score": 0.5,
                        "thresholds": {"low": 0.2, "high": 0.8},
                    },
                ),
            ),
        ):
            report = compare(b"Subject: demo\n\nHello")
        app = AppTest.from_file(
            str(Path(__file__).resolve().parents[1] / "app.py")
        ).run()
        app.selectbox[0].select("compare").run()
        app.session_state["report"] = report
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        self.assertIn("Keras", [item.value for item in app.subheader])
        self.assertTrue(app.get("download_button"))
        app.selectbox[0].select("qwen").run()
        self.assertNotIn("report", app.session_state)

    def test_start_page(self):
        app = AppTest.from_file(
            str(Path(__file__).resolve().parents[1] / "app.py")
        ).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "AI Email Security")
        self.assertTrue(app.button[0].disabled)

    def test_report_display(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
        app.session_state["fingerprint"] = None
        app.session_state["report"] = {
            "analysis": {
                "verdict": "dangerous",
                "risk": "high",
                "explanation": "Test analizy",
                "evidence": ["Test sygnału"],
                "recommendation": "Nie odpowiadaj.",
            },
            "rule_signals": [],
            "limitations": "Test ograniczeń",
        }
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.subheader[0].value, "Niebezpieczny")
        self.assertIn("Test analizy", [x.value for x in app.text])


if __name__ == "__main__":
    unittest.main()
