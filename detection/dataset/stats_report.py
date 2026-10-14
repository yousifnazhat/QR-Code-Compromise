"""Per-source inter-arrival statistics report for contract-#1 logs.

AUTHORIZATION: lab-only defensive analytics; operates on labelled
capture data produced inside the owned lab.

For each ``source`` (human / scanner / rig) the report gives event
counts, inter-arrival mean/std/min/max, selected percentiles, an ASCII
inter-arrival histogram, and the distribution of per-session mean
inter-arrivals. This is the W4.1 "stats report" evidence artifact.

CLI:
    python3 -m detection.dataset.stats_report capture.jsonl [--out report.txt]
"""

import argparse
import statistics
import sys
from typing import Any, Dict, Iterable, List

from detection.dataset.load import load_sessions

_PERCENTILES = (5, 25, 50, 75, 95, 99)

# Inter-arrival bins (ms) chosen to expose the 1-10 ms burst band.
_BINS = [(0, 2), (2, 5), (5, 10), (10, 15), (15, 25), (25, 50),
         (50, 100), (100, 200), (200, 400), (400, None)]


def inter_arrivals(events: Iterable[Dict[str, Any]]) -> List[float]:
    """Keydown inter-arrival times in ms, chronological."""
    downs = sorted((e for e in events if e["event"] == "keydown"),
                   key=lambda e: e["ts_ms"])
    return [float(b["ts_ms"] - a["ts_ms"]) for a, b in zip(downs, downs[1:])]


def _percentile(sorted_values: List[float], pct: float) -> float:
    """Linear-interpolated percentile on a pre-sorted list."""
    if not sorted_values:
        return float("nan")
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    frac = rank - low
    return sorted_values[low] * (1 - frac) + sorted_values[high] * frac


def _histogram(values: List[float], width: int = 40) -> str:
    lines = []
    counts = []
    for lo, hi in _BINS:
        if hi is None:
            counts.append(sum(1 for v in values if v >= lo))
        else:
            counts.append(sum(1 for v in values if lo <= v < hi))
    top = max(counts) or 1
    for (lo, hi), count in zip(_BINS, counts):
        bar = "#" * int(round(width * count / top))
        lines.append("%9s ms | %-40s %6d (%5.1f%%)" % (
            ("%g-%s" % (lo, hi if hi else "+")), bar, count,
            100.0 * count / len(values) if values else 0.0))
    return "\n".join(lines)


def _stats_block(name: str, ias: List[float]) -> List[str]:
    lines = ["", "=== source: %s ===" % name, "inter-arrival samples: %d" % len(ias)]
    if not ias:
        lines.append("  (no data)")
        return lines
    s = sorted(ias)
    mean = statistics.fmean(ias)
    std = statistics.pstdev(ias)
    lines.append("  mean     : %8.2f ms" % mean)
    lines.append("  std      : %8.2f ms" % std)
    lines.append("  min      : %8.2f ms" % s[0])
    lines.append("  max      : %8.2f ms" % s[-1])
    for pct in _PERCENTILES:
        lines.append("  p%-02d      : %8.2f ms" % (pct, _percentile(s, pct)))
    lines.append("  cv       : %8.3f" % (std / mean if mean else 0.0))
    lines.append("  histogram (ms):")
    lines.append(_histogram(ias))
    return lines


def build_report(sessions: Dict[str, List[Dict[str, Any]]]) -> str:
    """Render the per-source stats report from grouped sessions."""
    by_source: Dict[str, List[float]] = {}
    session_means: Dict[str, List[float]] = {}
    session_counts: Dict[str, int] = {}
    for events in sessions.values():
        source = events[0]["source"]
        by_source.setdefault(source, [])
        session_counts[source] = session_counts.get(source, 0) + 1
        ias = inter_arrivals(events)
        by_source[source].extend(ias)
        if ias:
            session_means.setdefault(source, []).append(statistics.fmean(ias))

    out = ["Keystroke inter-arrival statistics report (contract-#1 JSONL)",
           "sessions: %d total" % len(sessions)]
    for source in sorted(by_source):
        out.append("  %s: %d sessions" % (source, session_counts.get(source, 0)))
    for source in sorted(by_source):
        out.extend(_stats_block(source, by_source[source]))
        means = session_means.get(source, [])
        if len(means) >= 2:
            sm = sorted(means)
            out.append("  per-session mean inter-arrival:")
            out.append("    min %8.2f | median %8.2f | max %8.2f ms"
                       % (sm[0], _percentile(sm, 50), sm[-1]))
    return "\n".join(out) + "\n"


def main(argv: List[str] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Per-source inter-arrival statistics report")
    ap.add_argument("jsonl", help="contract-#1 JSONL path")
    ap.add_argument("--out", default="-",
                    help="output path ('-'=stdout, default)")
    args = ap.parse_args(argv)

    sessions = load_sessions(args.jsonl)
    report = build_report(sessions)
    if args.out == "-":
        sys.stdout.write(report)
    else:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
