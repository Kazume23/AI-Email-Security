import unittest

from ai_email_security.experiment_metrics import (
    constrained_thresholds,
    warning_metrics,
    wilson,
)


class ExperimentMetricsTests(unittest.TestCase):
    def test_recall_constraint_preserves_missed_attack_cost(self):
        labels = [0, 0, 1, 1]
        scores = [0.1, 0.7, 0.6, 0.9]
        thresholds = constrained_thresholds(labels, scores, 1.0)
        metrics = warning_metrics(labels, scores, thresholds["low"])
        self.assertEqual(metrics["recall"], 1.0)
        self.assertEqual(metrics["fpr"], 0.5)
        self.assertLess(thresholds["low"], thresholds["high"])

    def test_zero_scores_and_full_recall(self):
        thresholds = constrained_thresholds([0, 1], [0, 0], 1)
        self.assertEqual(thresholds["low"], 0)
        self.assertGreater(thresholds["high"], 0)

    def test_invalid_data_is_not_success(self):
        for labels, scores in [([0, 0], [0.1, 0.2]), ([0, 1], [0.1, float("nan")])]:
            with self.assertRaises(ValueError):
                constrained_thresholds(labels, scores, 0.9)

    def test_uncertainty_with_small_sample(self):
        self.assertIsNone(wilson(0, 0))
        self.assertGreater(wilson(0, 9)[1], 0.29)
        self.assertLess(wilson(0, 100)[1], 0.04)
