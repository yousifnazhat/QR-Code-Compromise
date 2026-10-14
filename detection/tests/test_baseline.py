"""Unit tests for the threshold baseline detector and eval harness."""

import pytest

from detection.detector.baseline import (
    ThresholdDetector,
    evaluate,
    stratified_split,
)


def _row(session, ia_mean, label):
    return {"session": session, "label": label, "ia_mean": ia_mean}


def test_fit_separates_clean_classes():
    rows = ([_row("h%02d" % i, 100.0 + i, 0) for i in range(10)] +
            [_row("s%02d" % i, 5.0 + 0.1 * i, 1) for i in range(10)])
    det = ThresholdDetector().fit(rows)
    assert det.threshold is not None
    # threshold must sit strictly between the classes (5.9 vs 100.0)
    assert 5.9 < det.threshold < 100.0
    assert det.margin > 0
    assert det.predict(rows) == [r["label"] for r in rows]


def test_predict_direction_low_mean_is_injected():
    rows = ([_row("h0", 120.0, 0), _row("h1", 90.0, 0)] +
            [_row("s0", 3.0, 1), _row("s1", 8.0, 1)])
    det = ThresholdDetector().fit(rows)
    assert det.predict_one({"ia_mean": 2.0}) == 1
    assert det.predict_one({"ia_mean": 500.0}) == 0


def test_fit_picks_best_threshold_when_classes_overlap():
    # injected 10, 50 | human 30, 70 -> best accuracy = 0.75
    rows = ([_row("h0", 30.0, 0), _row("h1", 70.0, 0)] +
            [_row("s0", 10.0, 1), _row("s1", 50.0, 1)])
    det = ThresholdDetector().fit(rows)
    preds = det.predict(rows)
    correct = sum(p == r["label"] for p, r in zip(preds, rows))
    assert correct >= 3  # at least as good as any rule


def test_fit_requires_both_classes():
    with pytest.raises(ValueError):
        ThresholdDetector().fit([_row("h0", 1.0, 0)])
    with pytest.raises(ValueError):
        ThresholdDetector().fit([])


def test_predict_before_fit_raises():
    with pytest.raises(RuntimeError):
        ThresholdDetector().predict_one({"ia_mean": 5.0})


def test_evaluate_known_confusion():
    # y_true: [1,1,0,0,0], y_pred: [1,0,1,0,0]
    metrics = evaluate([1, 1, 0, 0, 0], [1, 0, 1, 0, 0])
    assert metrics["tp"] == 1
    assert metrics["fn"] == 1
    assert metrics["fp"] == 1
    assert metrics["tn"] == 2
    assert metrics["precision"] == pytest.approx(0.5)
    assert metrics["recall"] == pytest.approx(0.5)
    assert metrics["fpr"] == pytest.approx(1 / 3)
    assert metrics["fnr"] == pytest.approx(0.5)
    assert metrics["accuracy"] == pytest.approx(0.6)


def test_evaluate_perfect():
    metrics = evaluate([0, 1, 0, 1], [0, 1, 0, 1])
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["fpr"] == 0.0
    assert metrics["fnr"] == 0.0
    assert metrics["f1"] == 1.0


def test_evaluate_empty_pred_corner_cases():
    # all-negative predictions: recall 0 but defined, no divide-by-zero
    metrics = evaluate([1, 1], [0, 0])
    assert metrics["precision"] == 0.0
    assert metrics["fpr"] == 0.0  # no negatives present


def test_evaluate_length_mismatch():
    with pytest.raises(ValueError):
        evaluate([1, 0], [1])


def test_stratified_split_balances_classes():
    rows = ([_row("h%02d" % i, 100.0, 0) for i in range(10)] +
            [_row("s%02d" % i, 5.0, 1) for i in range(10)])
    train, test = stratified_split(rows, test_frac=0.5, seed=3)
    assert len(train) == len(test) == 10
    assert {r["label"] for r in train} == {0, 1}
    assert {r["label"] for r in test} == {0, 1}
    assert sum(r["label"] for r in train) == 5
    assert sum(r["label"] for r in test) == 5
    # train and test are disjoint
    train_ids = {r["session"] for r in train}
    assert not train_ids & {r["session"] for r in test}


def test_stratified_split_deterministic():
    rows = ([_row("h%02d" % i, 100.0, 0) for i in range(8)] +
            [_row("s%02d" % i, 5.0, 1) for i in range(8)])
    a1, b1 = stratified_split(rows, 0.5, seed=11)
    a2, b2 = stratified_split(rows, 0.5, seed=11)
    assert [r["session"] for r in a1] == [r["session"] for r in a2]
    assert [r["session"] for r in b1] == [r["session"] for r in b2]


def test_end_to_end_synthetic_pipeline(tmp_path):
    # generator -> JSONL -> load -> features -> fit/eval (W4.2 smoke)
    import json

    from detection.dataset.load import load_sessions
    from detection.dataset.synth import generate_dataset
    from detection.detector.features import sessions_features

    events = generate_dataset(seed=9, human_sessions=8,
                              scanner_sessions=8, min_keys=30,
                              max_keys=40)
    path = tmp_path / "synth.jsonl"
    path.write_text(
        "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    rows = sessions_features(load_sessions(str(path)))
    train, test = stratified_split(rows, 0.5, seed=2)
    det = ThresholdDetector().fit(train)
    preds = det.predict(test)
    metrics = evaluate([r["label"] for r in test], preds)
    # clean synthetic separation must give perfect held-out metrics
    assert metrics["recall"] == 1.0
    assert metrics["fpr"] == 0.0
    assert metrics["accuracy"] == 1.0
