"""Unit tests for W4.2 feature extraction."""

import random

import pytest

from detection.dataset.synth import gen_burst_session, gen_human_session
from detection.detector.features import (
    BURST_THRESHOLD_MS,
    inter_arrivals,
    label_for_source,
    session_features,
)


def _events(times, keycode=65, source="human"):
    return [
        {"ts_ms": t, "event": "keydown", "keycode": keycode,
         "source": source, "device": "d", "session": "s"}
        for t in times
    ]


def test_inter_arrivals_uses_keydown_only_and_sorts():
    events = [
        {"ts_ms": 30, "event": "keydown", "keycode": 1, "source": "human",
         "device": "d", "session": "s"},
        {"ts_ms": 10, "event": "keyup", "keycode": 1, "source": "human",
         "device": "d", "session": "s"},
        {"ts_ms": 20, "event": "keydown", "keycode": 2, "source": "human",
         "device": "d", "session": "s"},
        {"ts_ms": 5, "event": "keydown", "keycode": 3, "source": "human",
         "device": "d", "session": "s"},
    ]
    # keyup ignored; keydowns sorted chronologically: 5, 20, 30
    assert inter_arrivals(events) == [15.0, 10.0]


def test_inter_arrivals_known_statistics():
    feats = session_features("s", _events([100, 200, 350, 500]))
    # inter-arrivals: 100, 150, 150
    assert feats["ia_mean"] == pytest.approx(400.0 / 3.0)
    assert feats["ia_min"] == 100.0
    assert feats["ia_median"] == 150.0
    # population std of (100,150,150): mean 400/3, deviations -100/3, +50/3, +50/3
    var = ((100 - 400.0 / 3.0) ** 2 + 2 * (150 - 400.0 / 3.0) ** 2) / 3.0
    assert feats["ia_std"] == pytest.approx(var ** 0.5)


def test_kurtosis_zero_for_constant_and_tiny_sequences():
    assert session_features("s", _events([0, 10, 10, 10]))["ia_kurtosis"] == 0.0
    assert session_features("s", _events([0, 1, 2]))["ia_kurtosis"] == 0.0


def test_kurtosis_positive_for_heavy_tail():
    # mostly fast with one huge outlier -> positive excess kurtosis
    feats = session_features("s", _events([0, 10, 20, 30, 40, 50, 5000]))
    assert feats["ia_kurtosis"] > 1.0


def test_burst_fraction_and_longest_run():
    # inter-arrivals: 1, 2, 200, 1  -> 3 of 4 below threshold
    feats = session_features("s", _events([0, 1, 3, 203, 204]))
    assert feats["burst_frac"] == 0.75
    assert feats["burst_longest_run"] == 2


def test_burst_regularity_constant_burst_is_one():
    feats = session_features("s", _events([0, 2, 4, 6, 8]))
    assert feats["burst_regularity"] == 1.0


def test_burst_regularity_lower_for_irregular_bursts():
    irregular = session_features("s", _events([0, 1, 12, 13]))
    regular = session_features("s", _events([0, 6, 12, 18]))
    assert regular["burst_regularity"] > irregular["burst_regularity"]


def test_synthetic_human_and_scanner_separate_cleanly():
    rng = random.Random(7)
    human = session_features(
        "h", gen_human_session(rng, "h", 80))
    scanner = session_features(
        "s", gen_burst_session(rng, "s", 80, "scanner", "dev"))
    assert scanner["ia_mean"] < BURST_THRESHOLD_MS < human["ia_mean"]
    assert scanner["burst_frac"] == 1.0
    assert scanner["burst_regularity"] > human["burst_regularity"]
    assert scanner["ia_cv"] < 0.2 < human["ia_cv"]
    assert scanner["n_keys"] == 80
    assert human["n_keys"] == 80  # backspaces count as keys


def test_labels():
    assert label_for_source("human") == 0
    assert label_for_source("scanner") == 1
    assert label_for_source("rig") == 1


def test_label_attached_to_session_features():
    human = session_features("h", _events([0, 100, 250], source="human"))
    rig = session_features("r", _events([0, 5, 10], source="rig"))
    assert human["label"] == 0
    assert rig["label"] == 1


def test_empty_session_features_are_zero():
    feats = session_features("s", [])
    assert feats["label"] == 0  # empty -> no source -> human default
    assert feats["n_keys"] == 0
    for name in ("ia_mean", "ia_std", "ia_min", "burst_frac",
                 "burst_regularity"):
        assert feats[name] == 0.0
