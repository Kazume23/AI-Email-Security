import numpy as np
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support


def binary_metrics(labels, predicted):
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predicted, average="binary", zero_division=0
    )
    tn, fp, fn, tp = confusion_matrix(labels, predicted, labels=[0, 1]).ravel()
    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
        "true_positive": int(tp),
    }


def choose_thresholds(labels, scores, steps):
    candidates = np.linspace(0.001, 0.999, steps)
    predictions = np.asarray(scores)[:, None] >= candidates[None, :]
    positive = np.asarray(labels, dtype=bool)[:, None]
    tp = (predictions & positive).sum(axis=0)
    fp = (predictions & ~positive).sum(axis=0)
    fn = (~predictions & positive).sum(axis=0)
    f2 = 5 * tp / np.maximum(5 * tp + 4 * fn + fp, 1)
    f1 = 2 * tp / np.maximum(2 * tp + fn + fp, 1)
    low_index = int(np.argmax(f2))
    low_index = min(low_index, len(candidates) - 2)
    high_index = low_index + 1 + int(np.argmax(f1[low_index + 1 :]))
    return {"low": float(candidates[low_index]), "high": float(candidates[high_index])}


def evaluate_scores(labels, scores, thresholds):
    scores = np.asarray(scores)
    warning = scores >= thresholds["low"]
    danger = scores >= thresholds["high"]
    return {
        "count": len(scores),
        "warnings": binary_metrics(labels, warning),
        "strong_alerts": binary_metrics(labels, danger),
        "suspicious_fraction": float(np.mean(warning & ~danger)),
        "analysis_errors": 0,
    }


def classify_score(score, thresholds):
    if score < thresholds["low"]:
        return "safe", "low"
    if score < thresholds["high"]:
        return "suspicious", "medium"
    return "dangerous", "high"
