import unittest
from unittest.mock import patch
import numpy as np
from ai_email_security.evaluation import (
    choose_thresholds,
    classify_score,
    evaluate_scores,
)
from ai_email_security.text_features import mail_text, prepare_text
from ai_email_security.analyzer import analyze


class MLTests(unittest.TestCase):
    def test_thresholds_and_metrics(self):
        labels = [0, 0, 1, 1]
        scores = np.array([0.01, 0.1, 0.8, 0.99])
        thresholds = choose_thresholds(labels, scores, 201)
        self.assertLess(thresholds["low"], thresholds["high"])
        report = evaluate_scores(labels, scores, thresholds)
        self.assertEqual(report["warnings"]["false_negative"], 0)
        self.assertEqual(report["warnings"]["false_positive"], 0)
        self.assertEqual(classify_score(thresholds["low"], thresholds)[0], "suspicious")
        self.assertEqual(classify_score(thresholds["high"], thresholds)[0], "dangerous")

    def test_shared_preprocessing(self):
        self.assertEqual(
            mail_text({"headers": {"Subject": "Hello"}, "text": "one\n two"}),
            prepare_text("Hello", "one\n two"),
        )

    @patch("ai_email_security.keras_client.analyze_with_keras")
    def test_engine_dispatch(self, client):
        client.return_value = (
            {"verdict": "safe", "risk": "low"},
            {"model": "test", "score": 0.1},
        )
        report = analyze(b"Subject: test\n\nHello", engine="keras")
        self.assertEqual(report["engine"], "keras")
        self.assertEqual(report["model"], "test")
        with self.assertRaises(ValueError):
            analyze(b"", engine="unknown")


if __name__ == "__main__":
    unittest.main()
