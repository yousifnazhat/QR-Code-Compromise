#!/usr/bin/env bash
# capture_logs.sh — P6 iOS rig: stream the simulator log for P6 markers (W6.8).
#
# AUTHORIZATION — LAB ONLY (docs/governance/policy.md §1/§7).
#
# Usage:   ./capture_logs.sh [--dev <udid-or-name>] [--all]
#          default predicate: eventMessage CONTAINS "P6RIG"
#          --all: no predicate (full stream; very verbose)
#
# Exit codes: 0 stream ended cleanly (Ctrl-C); 2 Xcode missing / no device.

set -euo pipefail

DEV=""
PRED='eventMessage CONTAINS "P6RIG"'
while [ $# -gt 0 ]; do
  case "$1" in
    --dev) DEV="${2:?--dev needs a value}"; shift 2 ;;
    --all) PRED=''; shift ;;
    -*) echo "unknown flag: $1" >&2; exit 2 ;;
    *) echo "unexpected arg: $1" >&2; exit 2 ;;
  esac
done

if ! xcrun simctl help >/dev/null 2>&1; then
  cat >&2 <<'EOF'
ERROR: xcrun simctl is not available — no Xcode on this Mac.

PHYSICAL SLOT (human, one-time):
  1. Install Xcode from the Mac App Store (or developer.apple.com/xcode).
  2. sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer
  3. xcodebuild -runFirstLaunch
  4. Re-run this script.
EOF
  exit 2
fi
if [ -z "$DEV" ]; then
  DEV="booted"
fi

echo "== P6 iOS rig: streaming device log ($DEV); predicate: ${PRED:-none}; Ctrl-C to stop"
if [ -n "$PRED" ]; then
  exec xcrun simctl spawn "$DEV" log stream --predicate "$PRED"
else
  exec xcrun simctl spawn "$DEV" log stream
fi
