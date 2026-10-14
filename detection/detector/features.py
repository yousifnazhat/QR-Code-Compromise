"""Feature extraction for keystroke-injection detection (W4.2).

AUTHORIZATION: lab-only defensive analytics over contract-#1 captures.

Every feature vector describes one *session* (the ``session`` label of
contract #1) — the unit a detector would actually raise on. Features
are computed from keydown inter-arrival times:

=========================  ==================================================
feature                    definition
=========================  ==================================================
ia_mean                    mean inter-arrival (ms)
ia_std                     population std of inter-arrivals
ia_min                     minimum inter-arrival
ia_median                  median inter-arrival
ia_kurtosis                Fisher kurtosis of inter-arrivals
ia_cv                      coefficient of variation (std/mean)
burst_frac                 fraction of inter-arrivals < BURST_THRESHOLD_MS
burst_regularity           1 - min(1, std/mean) over burst inter-arrivals
burst_longest_run          longest consecutive run of burst inter-arrivals
n_keys                     keydown count in the session
=========================  ==================================================

Burst regularity is the QUACK-style "machine rhythm" signal: scanner
wedges emit near-identical inter-arrivals, so their burst
sub-distribution has near-zero relative variance (regularity -> 1),
while even fast human typing keeps a visible spread.
"""

import statistics
from typing import Any, Dict, Iterable, List

__all__ = [
    "BURST_THRESHOLD_MS",
    "INJECTED_SOURCES",
    "inter_arrivals",
    "session_features",
    "sessions_features",
    "label_for_source",
]

# Below ~15 ms sustained typing is not achievable by human fingers on a
# full-size keyboard; the synthetic generator puts wedge bursts in the
# 1-10 ms band, comfortably below this line.
BURST_THRESHOLD_MS = 15.0

INJECTED_SOURCES = {"scanner", "rig"}

FEATURE_NAMES = (
    "n_keys", "ia_mean", "ia_std", "ia_min", "ia_median",
    "ia_kurtosis", "ia_cv", "burst_frac", "burst_regularity",
    "burst_longest_run",
)


def inter_arrivals(events: Iterable[Dict[str, Any]]) -> List[float]:
    """Keydown inter-arrival times in ms, chronological."""
    downs = sorted((e for e in events if e.get("event") == "keydown"),
                   key=lambda e: e["ts_ms"])
    return [float(b["ts_ms"] - a["ts_ms"]) for a, b in zip(downs, downs[1:])]


def _kurtosis(values: List[float], mean: float, std: float) -> float:
    """Fisher (excess) kurtosis; 0.0 when undefined (n<4 or zero var)."""
    if len(values) < 4 or std == 0.0:
        return 0.0
    m4 = sum((v - mean) ** 4 for v in values) / len(values)
    return m4 / (std ** 4) - 3.0


def _burst_metrics(ias: List[float]) -> List[float]:
    burst = [x for x in ias if x < BURST_THRESHOLD_MS]
    frac = len(burst) / len(ias) if ias else 0.0
    if len(burst) >= 2:
        bmean = statistics.fmean(burst)
        bstd = statistics.pstdev(burst)
        regularity = 1.0 - min(1.0, bstd / bmean) if bmean > 0 else 0.0
    else:
        regularity = 0.0
    longest = run = 0
    for x in ias:
        run = run + 1 if x < BURST_THRESHOLD_MS else 0
        longest = max(longest, run)
    return [frac, regularity, float(longest)]


def label_for_source(source: str) -> int:
    """1 = injected (scanner/rig), 0 = human."""
    return 1 if source in INJECTED_SOURCES else 0


def session_features(session_id: str,
                     events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Feature vector + labels for one capture session."""
    ias = inter_arrivals(events)
    source = events[0]["source"] if events else ""
    n_keys = sum(1 for e in events if e.get("event") == "keydown")
    feats: Dict[str, Any] = {
        "session": session_id,
        "source": source,
        "label": label_for_source(source),
        "n_keys": float(n_keys),
    }
    if not ias:
        feats.update({name: 0.0 for name in FEATURE_NAMES[1:]})
        feats["n_keys"] = float(n_keys)
        return feats
    mean = statistics.fmean(ias)
    std = statistics.pstdev(ias)
    ordered = sorted(ias)
    median = (ordered[len(ordered) // 2] if len(ordered) % 2 else
              (ordered[len(ordered) // 2 - 1] + ordered[len(ordered) // 2]) / 2)
    feats.update({
        "ia_mean": mean,
        "ia_std": std,
        "ia_min": ordered[0],
        "ia_median": median,
        "ia_kurtosis": _kurtosis(ias, mean, std),
        "ia_cv": std / mean if mean else 0.0,
    })
    feats["burst_frac"], feats["burst_regularity"], feats["burst_longest_run"] = \
        _burst_metrics(ias)
    return feats


def sessions_features(sessions: Dict[str, List[Dict[str, Any]]]
                      ) -> List[Dict[str, Any]]:
    """Feature vectors for every session, sorted by session id."""
    return [session_features(sid, events)
            for sid, events in sorted(sessions.items())]
