"""Threshold baseline detector + evaluation harness (W4.2).

AUTHORIZATION: lab-only defensive research; baseline for comparing
timing-anomaly detection approaches on contract-#1 data.

The baseline is deliberately simple and interpretable:

- one feature: ``ia_mean`` (mean keydown inter-arrival in ms) per
  session;
- one threshold, chosen on the TRAIN split by scanning the midpoints
  between consecutive distinct feature values and keeping the candidate
  with the best accuracy (ties -> the candidate with the largest
  separation margin);
- prediction: injected iff ``ia_mean < threshold`` (scanner bursts are
  1-10 ms vs ~100 ms human typing).

The evaluation harness computes precision / recall / FPR / FNR /
accuracy / F1 with a stratified train/test split by session.
"""

import random
from typing import Any, Dict, List, Sequence, Tuple

__all__ = [
    "ThresholdDetector",
    "evaluate",
    "stratified_split",
]


class ThresholdDetector:
    """Single-feature threshold classifier on ia_mean."""

    feature = "ia_mean"

    def __init__(self):
        self.threshold = None  # type: float
        self.margin = None      # type: float

    def fit(self, rows: List[Dict[str, Any]]) -> "ThresholdDetector":
        """Choose the accuracy-maximizing threshold on labelled rows."""
        values = [(r[self.feature], r["label"]) for r in rows
                  if r[self.feature] is not None]
        if not values:
            raise ValueError("no feature values to fit on")
        if len({label for _, label in values}) < 2:
            raise ValueError("training data must contain both classes")
        values.sort()
        # Candidate thresholds: midpoints between adjacent distinct values.
        candidates = []
        for (v1, _), (v2, _) in zip(values, values[1:]):
            if v2 > v1:
                candidates.append((v1 + v2) / 2.0)
        if not candidates:
            self.threshold = values[0][0]
            self.margin = 0.0
            return self

        best = None  # (accuracy, margin, threshold)
        for t in candidates:
            correct = sum(
                1 for v, label in values
                if (1 if v < t else 0) == label)
            accuracy = correct / len(values)
            # Separation margin: distance from t to the nearest value.
            margin = min(abs(v - t) for v, _ in values)
            key = (accuracy, margin)
            if best is None or key > best[:2]:
                best = (accuracy, margin, t)
        self.threshold, self.margin = best[2], best[1]
        return self

    def predict_one(self, features: Dict[str, Any]) -> int:
        if self.threshold is None:
            raise RuntimeError("detector not fitted")
        return 1 if features[self.feature] < self.threshold else 0

    def predict(self, rows: List[Dict[str, Any]]) -> List[int]:
        return [self.predict_one(r) for r in rows]


def evaluate(y_true: Sequence[int], y_pred: Sequence[int]) -> Dict[str, float]:
    """Precision/recall/FPR/FNR and friends. Positive class = injected."""
    if len(y_true) != len(y_pred):
        raise ValueError("label/prediction length mismatch")
    tp = fp = tn = fn = 0
    for truth, pred in zip(y_true, y_pred):
        if truth == 1 and pred == 1:
            tp += 1
        elif truth == 0 and pred == 1:
            fp += 1
        elif truth == 0:
            tn += 1
        else:
            fn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": precision,
        "recall": recall,
        "fpr": fp / (fp + tn) if fp + tn else 0.0,
        "fnr": fn / (fn + tp) if fn + tp else 0.0,
        "accuracy": (tp + tn) / len(y_true) if y_true else 0.0,
        "f1": (2 * precision * recall / (precision + recall)
               if precision + recall else 0.0),
    }


def stratified_split(rows: List[Dict[str, Any]], test_frac: float = 0.5,
                     seed: int = 0) -> Tuple[List[Dict[str, Any]],
                                             List[Dict[str, Any]]]:
    """Stratified session split keeping class balance in both halves."""
    rng = random.Random(seed)
    train, test = [], []
    for label in (0, 1):
        bucket = [r for r in rows if r["label"] == label]
        rng.shuffle(bucket)
        n_test = int(round(len(bucket) * test_frac))
        test.extend(bucket[:n_test])
        train.extend(bucket[n_test:])
    train.sort(key=lambda r: r["session"])
    test.sort(key=lambda r: r["session"])
    return train, test
