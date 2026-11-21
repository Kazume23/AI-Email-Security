import json
import unittest
from unittest.mock import patch

from ai_email_security.comparison import compare
from ai_email_security.eml_reader import read_eml, InputError
from ai_email_security.ollama_client import EngineUnavailable, AnalysisError
from tests.test_demo import VALID


class ComparisonTests(unittest.TestCase):
    @patch(
        "ai_email_security.keras_client.analyze_with_keras",
        return_value=(
            VALID,
            {"model": "fake", "score": 0.5, "thresholds": {"low": 0.2, "high": 0.8}},
        ),
    )
    @patch("ai_email_security.analyzer.analyze_with_model", return_value=VALID)
    def test_one_parse_and_legacy_reports(self, qwen, keras):
        with patch("ai_email_security.comparison.read_eml", wraps=read_eml) as parser:
            report = compare(b"Subject: demo\n\nHello")
        parser.assert_called_once()
        self.assertTrue(report["agreement"])
        self.assertIsNone(report["results"]["qwen"]["score"])
        self.assertEqual(report["results"]["keras"]["report"]["analysis"], VALID)
        json.dumps(report, allow_nan=False)

    @patch(
        "ai_email_security.keras_client.analyze_with_keras",
        return_value=(VALID, {"model": "fake"}),
    )
    def test_independent_failures(self, keras):
        for exc, status in [
            (EngineUnavailable("private"), "unavailable"),
            (AnalysisError("private"), "error"),
            (RuntimeError("private"), "error"),
        ]:
            with patch(
                "ai_email_security.analyzer.analyze_with_model", side_effect=exc
            ):
                report = compare(b"Subject: demo\n\nHello")
            self.assertEqual(report["results"]["keras"]["status"], "success")
            self.assertEqual(report["results"]["qwen"]["status"], status)
            self.assertIsNone(report["agreement"])
            self.assertNotIn("private", json.dumps(report))

    @patch("ai_email_security.analyzer.analyze_with_model")
    def test_invalid_input_runs_no_engine(self, model):
        with self.assertRaises(InputError):
            compare(b"")
        model.assert_not_called()
