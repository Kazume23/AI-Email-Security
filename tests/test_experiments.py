import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_email_security.experiments import read_manifest, run_experiment, summarize
from ai_email_security.comparison import compare
from tests.test_demo import VALID


class ExperimentTests(unittest.TestCase):
    def test_metrics_and_denominators(self):
        rows = []
        for label, verdict in [
            (0, "safe"),
            (0, "dangerous"),
            (1, "safe"),
            (1, "suspicious"),
        ]:
            rows.append(
                {
                    "label": label,
                    "agreement": True,
                    "results": {
                        name: {"status": "success", "verdict": verdict, "seconds": 1.0}
                        for name in ("keras", "qwen")
                    },
                }
            )
        metrics = summarize(rows)
        for item in metrics["engines"].values():
            self.assertEqual(item["fpr"], 0.5)
            self.assertEqual(item["recall"], 0.5)
            self.assertEqual(item["f1"], 0.5)
        self.assertEqual(metrics["agreement_rate"], 1)
        self.assertIsNone(summarize([])["engines"]["qwen"]["fpr"])
        rows[0]["results"]["qwen"]["status"] = "unavailable"
        rows[0]["agreement"] = None
        self.assertEqual(summarize(rows)["agreement_denominator"], 3)
        self.assertEqual(summarize(rows)["engines"]["qwen"]["coverage"], 0.75)

    def test_manifest_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "manifest.jsonl"
            for cases in [
                [{"id": "a", "path": "a.eml"}],
                [{"id": "a", "path": "a.eml", "label": 0}] * 2,
            ]:
                path.write_text("\n".join(json.dumps(case) for case in cases))
                with self.assertRaises(ValueError):
                    read_manifest(path)

    def test_private_export_limit_and_separate_runs(self):
        with (
            patch(
                "ai_email_security.analyzer.analyze_with_model",
                return_value={**VALID, "explanation": "PRIVATE-TEXT"},
            ),
            patch(
                "ai_email_security.keras_client.analyze_with_keras",
                return_value=(VALID, {"model": "fake"}),
            ),
        ):
            report = compare(b"Subject: demo\n\nHello")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.eml").write_bytes(b"Subject: PRIVATE-TEXT\n\nPRIVATE-TEXT")
            manifest = root / "manifest.jsonl"
            manifest.write_text(
                "\n".join(
                    json.dumps({"id": str(i), "path": "a.eml", "label": 0})
                    for i in range(12)
                )
            )
            with (
                patch("ai_email_security.experiments.project_path", return_value=root),
                patch(
                    "ai_email_security.experiments.compare", return_value=report
                ) as comparison,
            ):
                first = run_experiment(manifest, "demonstration")
                self.assertEqual(comparison.call_count, 10)
                second = run_experiment(manifest, "independent", 1)
            self.assertNotEqual(first, second)
            for path in first.iterdir():
                self.assertNotIn("PRIVATE-TEXT", path.read_text(encoding="utf-8"))
            self.assertEqual(
                json.loads((first / "summary.json").read_text())["dataset_kind"],
                "demonstration",
            )
            self.assertEqual(len((first / "cases.jsonl").read_text().splitlines()), 10)
