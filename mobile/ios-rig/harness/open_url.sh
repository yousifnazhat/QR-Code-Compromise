#!/usr/bin/env bash
# open_url.sh — P6 iOS rig: open a URL on the booted simulator (U stage).
#
# AUTHORIZATION — LAB ONLY (docs/governance/policy.md §1/§7). Simulator and
# owned devices only. This is the iOS equivalent of the Android rig's
# load_url.sh: it hands the "scanned" URL to the device.
#
# Usage:   ./open_url.sh <url> [--dev <udid-or-name>]
# Example: ./open_url.sh "http://192.0.2.10:8000/payload.html" --dev "iPhone 16"
#          (192.0.2.10 = RFC 5737 example space; use YOUR lab host when running)
#
# Mapping: http(s) URLs open in Safari; p6rigdemo:// URLs dispatch to the rig
# demo app if installed (the C4/C7 scheme-dispatch measurement).
#
# Exit codes: 0 URL delivered; 2 usage / Xcode missing / no booted device.

set -euo pipefail

URL=""
DEV=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dev) DEV="${2:?--dev needs a value}"; shift 2 ;;
    -*) echo "unknown flag: $1" >&2; exit 2 ;;
    *) if [ -z "$URL" ]; then URL="$1"; shift; else echo "unexpected arg: $1" >&2; exit 2; fi ;;
  esac
done

if [ -z "$URL" ]; then
  echo "usage: $0 <url> [--dev <udid-or-name>]" >&2
  exit 2
fi
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
if ! xcrun simctl list devices | grep -qi "booted"; then
  echo "ERROR: no booted simulator (boot one: ./sim_boot.sh)." >&2
  exit 2
fi

echo "== P6 iOS rig: opening URL on simulator ($DEV): $URL"
xcrun simctl openurl "$DEV" "$URL"
echo "== delivered. Capture telemetry with: ./capture_logs.sh"
