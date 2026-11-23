import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from urllib.error import URLError, HTTPError
from ai_email_security.eml_reader import read_eml, InputError, MAX_BYTES
from ai_email_security.rules import find_signals
from ai_email_security.ollama_client import validate, analyze_with_model, AnalysisError
from ai_email_security.analyzer import analyze

SAMPLES = Path(__file__).resolve().parents[1] / "samples"
VALID = {
    "verdict": "suspicious",
    "risk": "medium",
    "evidence": ["Żądanie danych."],
    "explanation": "Próba wyłudzenia.",
    "recommendation": "Zweryfikuj nadawcę.",
}


class ReaderTests(unittest.TestCase):
    def test_samples(self):
        for path in SAMPLES.glob("*.eml"):
            self.assertTrue(read_eml(path.read_bytes())["text"])

    def test_html_and_rules(self):
        mail = read_eml((SAMPLES / "credentials.eml").read_bytes())
        self.assertIn("https://login.example.net/verify", mail["links"])
        self.assertNotIn("<p>", mail["text"])
        self.assertTrue(find_signals(mail))

    def test_attachment(self):
        mail = read_eml((SAMPLES / "attachment.eml").read_bytes())
        self.assertEqual(mail["attachments"][0]["name"], "invoice.exe")
        self.assertGreater(mail["attachments"][0]["size_bytes"], 0)
        self.assertTrue(find_signals(mail))
        self.assertNotIn("Harmless", mail["text"])

    def test_missing_headers(self):
        self.assertEqual(read_eml(b"Subject: test\n\nHello")["headers"]["From"], "")

    def test_invalid_inputs(self):
        for raw in (
            b"",
            b"not an email",
            b"x" * (MAX_BYTES + 1),
            b"Subject: x\n\n" + b"a" * 17000,
            b"MIME-Version: 1.0\nContent-Type: multipart/mixed; boundary=x\n\nbroken",
        ):
            with self.assertRaises(InputError):
                read_eml(raw)

    def test_html_script_hidden(self):
        mail = read_eml(
            b"Content-Type: text/html\n\n<script>bad()</script><p>Hello</p>"
        )
        self.assertNotIn("bad()", mail["text"])


class ModelTests(unittest.TestCase):
    def test_validation(self):
        self.assertEqual(validate(VALID.copy()), VALID)
        for changes in (
            {"risk": "high"},
            {"verdict": []},
            {"evidence": "text"},
            {"explanation": ""},
            {"extra": 1},
        ):
            with self.assertRaises(AnalysisError):
                validate(dict(VALID, **changes))

    @patch("ai_email_security.ollama_client.request.build_opener")
    def test_transport_errors(self, build):
        for failure in (
            URLError("offline"),
            TimeoutError(),
            HTTPError("local", 404, "missing", {}, None),
        ):
            build.return_value.open.side_effect = failure
            with self.assertRaises(AnalysisError):
                analyze_with_model({}, [])

    @patch("ai_email_security.ollama_client.request.build_opener")
    def test_response_and_injection_boundary(self, build):
        response = build.return_value.open.return_value.__enter__.return_value
        response.read.return_value = json.dumps(
            {"done": True, "message": {"content": json.dumps(VALID)}}
        ).encode()
        mail = read_eml((SAMPLES / "injection.eml").read_bytes())
        self.assertEqual(analyze_with_model(mail, []), VALID)
        req = build.return_value.open.call_args.args[0]
        payload = json.loads(req.data)
        self.assertNotIn("SYSTEM OVERRIDE", payload["messages"][0]["content"])
        self.assertIn("SYSTEM OVERRIDE", payload["messages"][1]["content"])
        for raw in (b"bad json", b"{}", json.dumps({"done": False}).encode()):
            response.read.return_value = raw
            with self.assertRaises(AnalysisError):
                analyze_with_model(mail, [])

    @patch("ai_email_security.analyzer.analyze_with_model", return_value=VALID)
    def test_report_export(self, model):
        report = analyze((SAMPLES / "safe.eml").read_bytes())
        self.assertEqual(json.loads(json.dumps(report))["analysis"], VALID)
        self.assertNotIn("text", report)


if __name__ == "__main__":
    unittest.main()
