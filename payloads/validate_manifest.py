#!/usr/bin/env python3
"""validate_manifest.py — schema-check payloads/manifest.yaml (contract #4).

Checks:
  1. Manifest entries carry exactly the contract #4 fields with valid enums.
  2. ID set/order matches the coordinator-locked list (P4 runbook depends
     on it verbatim).
  3. Every entry has a templates/<id>.txt with a well-formed header
     (TEMPLATE/CLASS/AUTHORIZATION/PURPOSE/PREREQUISITES/CLEANUP + >=1
     ARTIFACT line) and a non-empty command line.
  4. results/killchain.csv exists with the contract header; any data rows
     reference known ids, carry the manifest runner, and use a verdict from
     the bypass|blocked|partial vocabulary.

Exit 0 = valid; exit 1 = violations (printed). Stdlib only, Python 3.9+.
Authorized lab security research only — see payloads/README.md.
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_matrix import (KILLCHAIN_HEADER, KILLCHAIN_PATH, MANIFEST_PATH,
                        ManifestError, VERDICTS, parse_manifest, parse_template,
                        validate_entries)


def check_killchain(path, entries):
    """Validate killchain.csv header + data rows against the manifest."""
    errors = []
    if not os.path.isfile(path):
        return ["results/killchain.csv missing: %s" % path]
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        try:
            header = next(reader)
        except StopIteration:
            return ["results/killchain.csv is empty (expected header row)"]
    if header != KILLCHAIN_HEADER:
        errors.append("killchain header %s != contract %s"
                      % (header, KILLCHAIN_HEADER))
        return errors
    runners = {e["id"]: e["runner"] for e in entries}
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for i, row in enumerate(rows, 2):
        pid = row.get("payload_id", "")
        if pid not in runners:
            errors.append("killchain row %d: unknown payload_id %r" % (i, pid))
            continue
        if row.get("runner") != runners[pid]:
            errors.append("killchain row %d: runner %r != manifest runner %r "
                          "for %s" % (i, row.get("runner"), runners[pid], pid))
        if not (row.get("mitigation") or "").strip():
            errors.append("killchain row %d: empty mitigation" % i)
        if row.get("verdict") not in VERDICTS:
            errors.append("killchain row %d: verdict %r not in %s"
                          % (i, row.get("verdict"), sorted(VERDICTS)))
    return errors


def main(argv=None):
    argv = argv if argv is not None else sys.argv
    manifest = argv[1] if len(argv) > 1 else MANIFEST_PATH
    try:
        entries = parse_manifest(manifest)
    except ManifestError as exc:
        print("FAIL: %s" % exc)
        return 1

    errors = validate_entries(entries)
    print("  %d entr%s checked" % (len(entries),
                                   "y" if len(entries) == 1 else "ies"))
    for entry in entries:
        print("  [entry] %-13s runner=%-10s staging=%-6s layout_safe=%-5s "
              "win_build=%-4s amsi=%s"
              % (entry.get("id"), entry.get("runner"), entry.get("staging"),
                 entry.get("layout_safe"), entry.get("win_build"),
                 entry.get("amsi")))

    kc_errors = check_killchain(KILLCHAIN_PATH, entries)
    with open(KILLCHAIN_PATH, newline="", encoding="utf-8") as fh:
        data_rows = sum(1 for _ in csv.reader(fh)) - 1
    print("  killchain.csv: %d data row(s) checked" % max(data_rows, 0))

    all_errors = errors + kc_errors
    for err in all_errors:
        print("  [FAIL] %s" % err)
    if all_errors:
        print("OVERALL: FAIL (%d violation(s))" % len(all_errors))
        return 1
    print("OVERALL: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
