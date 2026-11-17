import math

import numpy as np

from .evaluation import binary_metrics


def wilson(successes, count):
    if count == 0:
        return None
    z = 1.959963984540054
    rate = successes / count
    denominator = 1 + z * z / count
    center = (rate + z * z / (2 * count)) / denominator
    margin = (
        z * math.sqrt(rate * (1 - rate) / count + z * z / (4 * count**2)) / denominator
    )
    return [max(0.0, center - margin), min(1.0, center + margin)]


def warning_metrics(labels, scores, threshold):
    result = binary_metrics(labels, np.asarray(scores) >= threshold)
    negatives = result["false_positive"] + result["true_negative"]
    positives = result["true_positive"] + result["false_negative"]
    result["fpr"] = result["false_positive"] / negatives if negatives else None
    result["fpr_ci95"] = wilson(result["false_positive"], negatives)
    result["recall_ci95"] = wilson(result["true_positive"], positives)
    return result


def constrained_thresholds(labels, scores, recall_floor):
    labels = np.asarray(labels)
    scores = np.asarray(scores, dtype=float)
    if labels.shape != scores.shape or labels.ndim != 1 or set(labels) != {0, 1}:
        raise ValueError(
            "Threshold selection requires both classes and matching scores"
        )
    if not np.isfinite(scores).all() or np.any((scores < 0) | (scores > 1)):
        raise ValueError("Scores must be finite and between zero and one")
    if not 0 <= recall_floor <= 1:
        raise ValueError("Invalid recall floor")
    candidates = np.unique(np.r_[0.0, scores[scores < 1]])
    eligible = []
    for threshold in candidates:
        metrics = warning_metrics(labels, scores, threshold)
        if metrics["recall"] >= recall_floor:
            eligible.append((metrics["fpr"], -metrics["recall"], -threshold, threshold))
    low = float(min(eligible)[-1])
    upper = np.unique(np.r_[np.nextafter(low, 1.0), scores[scores > low], 1.0])
    high = max(
        upper, key=lambda value: (binary_metrics(labels, scores >= value)["f1"], value)
    )
    return {"low": low, "high": float(high)}
