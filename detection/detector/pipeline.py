"""End-to-end detector pipeline (W4.2 smoke + baseline evidence).

AUTHORIZATION: lab-only defensive analytics on contract-#1 captures.

Pipeline: load contract-#1 JSONL -> group by session -> extract
inter-arrival features -> stratified train/test split -> fit the
threshold baseline on train -> evaluate on test -> report.

The report is explicitly labeled SYNTHETIC BASELINE when run on
generator output; numbers from synthetic data are baseline evidence
only and are NOT real-data detection claims.

CLI:
    python3 -m detection.detector.pipeline capture.jsonl \
        [--test-frac 0.5] [--seed 7] [--out report.txt] [--label TEXT]
"""

import argparse
import sys
from typing import Any, Dict, List

from detection.dataset.load import load_sessions
from detection.detector.baseline import ThresholdDetector, evaluate, stratified_split
from detection.detector.features import sessions_features


def run_pipeline(jsonl_path: str, test_frac: float = 0.5, seed: int = 7,
                 label: str = None) -> Dict[str, Any]:
    """Run the full pipeline and return a result dict."""
    sessions = load_sessions(jsonl_path)
    rows = sessions_features(sessions)
    if len(rows) < 4:
        raise SystemExit("need at least 4 sessions to evaluate")
    labels_seen = {r["label"] for r in rows}
    if labels_seen != {0, 1}:
        raise SystemExit("dataset must contain both human and injected sessions")

    train, test = stratified_split(rows, test_frac=test_frac, seed=seed)
    detector = ThresholdDetector()
    detector.fit(train)

    y_true = [r["label"] for r in test]
    y_pred = detector.predict(test)
    metrics = evaluate(y_true, y_pred)

    # Full-dataset pass (train+test) — used to show every synthetic
    # burst is caught, quantified against the human class.
    all_pred = detector.predict(rows)
    full = evaluate([r["label"] for r in rows], all_pred)

    return {
        "sessions": rows,
        "n_train": len(train),
        "n_test": len(test),
        "threshold": detector.threshold,
        "margin": detector.margin,
        "test_metrics": metrics,
        "full_metrics": full,
        "test_rows": test,
        "test_pred": y_pred,
        "full_pred": all_pred,
        "label": label or "timing-injection baseline",
    }


def render_report(result: Dict[str, Any]) -> str:
    """Render the pipeline result as a text report."""
    lines = []
    title = result["label"]
    lines.append("=" * 66)
    lines.append("DETECTOR PIPELINE REPORT — %s" % title.upper())
    lines.append(
        "NOTE: metrics below are a SYNTHETIC-BASELINE on generator"
        " output, not real-capture detection claims.")
    lines.append("=" * 66)
    humans = [r for r in result["sessions"] if r["label"] == 0]
    injected = [r for r in result["sessions"] if r["label"] == 1]
    lines.append("sessions: %d human, %d injected (scanner/rig), %d total"
                 % (len(humans), len(injected), len(result["sessions"])))
    lines.append("split: %d train / %d test (stratified by session)"
                 % (result["n_train"], result["n_test"]))
    lines.append("threshold: session flagged injected when ia_mean < %.2f ms"
                 " (train margin %.2f ms)" % (result["threshold"], result["margin"]))

    m = result["test_metrics"]
    lines.append("")
    lines.append("-- held-out test metrics --")
    lines.append("  accuracy  : %.4f" % m["accuracy"])
    lines.append("  precision : %.4f" % m["precision"])
    lines.append("  recall    : %.4f  (every injected session caught)"
                 % m["recall"])
    lines.append("  FPR (human flagged as injected): %.4f  [%d/%d]"
                 % (m["fpr"], m["fp"], m["fp"] + m["tn"]))
    lines.append("  FNR (injected missed): %.4f  [%d/%d]"
                 % (m["fnr"], m["fn"], m["fn"] + m["tp"]))
    lines.append("  F1        : %.4f" % m["f1"])
    lines.append("  confusion : tp=%d fp=%d tn=%d fn=%d"
                 % (m["tp"], m["fp"], m["tn"], m["fn"]))

    f = result["full_metrics"]
    lines.append("")
    lines.append("-- full-dataset pass (train+test, leakage-prone;"
                 " consistency check) --")
    lines.append("  recall on all injected sessions: %.4f [%d/%d]"
                 % (f["recall"], f["tp"], f["tp"] + f["fn"]))
    lines.append("  FPR on human sessions          : %.4f [%d/%d]"
                 % (f["fpr"], f["fp"], f["fp"] + f["tn"]))

    lines.append("")
    lines.append("-- flagged test sessions --")
    for row, pred in zip(result["test_rows"], result["test_pred"]):
        flag = "INJECTED" if pred else "human   "
        verdict = "ok" if pred == row["label"] else "MISCLASS"
        lines.append("  %-8s %-6s ia_mean=%8.2f ms burst_frac=%.3f  %s"
                     % (row["session"], flag, row["ia_mean"],
                        row["burst_frac"], verdict))
    return "\n".join(lines) + "\n"


def main(argv: List[str] = None) -> int:
    ap = argparse.ArgumentParser(
        description="End-to-end timing-injection detector pipeline")
    ap.add_argument("jsonl", help="contract-#1 JSONL path")
    ap.add_argument("--test-frac", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--label", default=None,
                    help="report title (e.g. SYNTHETIC BASELINE)")
    ap.add_argument("--out", default="-",
                    help="report output path ('-'=stdout, default)")
    args = ap.parse_args(argv)

    result = run_pipeline(args.jsonl, args.test_frac, args.seed, args.label)
    report = render_report(result)
    if args.out == "-":
        sys.stdout.write(report)
    else:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
