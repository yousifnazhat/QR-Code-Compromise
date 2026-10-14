#!/usr/bin/env bash
# load_url.sh — P6 rig: open a URL on the running emulator (U stage of the chain).
#
# AUTHORIZATION — LAB ONLY (docs/governance/policy.md §1/§7): emulator + owned
# devices only.
#
# This is the phone-side "the user opened the scanned URL" step, expressed as
# the canonical Android VIEW intent:
#   adb shell am start -a android.intent.action.VIEW -d "<url>"
#
# Usage:   ./load_url.sh <url> [--pkg com.qrcompromise.p6rig]
# Example: ./load_url.sh http://192.0.2.10:8000/payload.html --pkg com.qrcompromise.p6rig
#          (192.0.2.10 is RFC 5737 example-space; use YOUR lab host when running.)
#
# Exit codes: 0 URL handed to the device; 2 usage / adb missing / no device.

set -euo pipefail

URL=""
PKG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --pkg) PKG="${2:?--pkg needs a value}"; shift 2 ;;
    -*) echo "unknown flag: $1" >&2; exit 2 ;;
    *) if [ -z "$URL" ]; then URL="$1"; shift; else echo "unexpected arg: $1" >&2; exit 2; fi ;;
  esac
done

if [ -z "$URL" ]; then
  echo "usage: $0 <url> [--pkg com.qrcompromise.p6rig]" >&2
  exit 2
fi
if ! command -v adb >/dev/null 2>&1; then
  echo "ERROR: adb not on PATH (physical slot: install the Android SDK platform-tools)." >&2
  exit 2
fi
if ! adb get-state >/dev/null 2>&1; then
  echo "ERROR: no connected device/emulator (start it: emulator -avd p6rig-api22)." >&2
  exit 2
fi

echo "== P6 rig: opening URL on device: $URL"
if [ -n "$PKG" ]; then
  # Route the VIEW intent into the rig target app's BROWSABLE activity
  # (mirrors a scanner app handing the URL to the vulnerable WebView).
  adb shell am start -a android.intent.action.VIEW -d "$URL" -n "$PKG/.MainActivity"
else
  adb shell am start -a android.intent.action.VIEW -d "$URL"
fi
echo "== delivered. Capture telemetry with:"
echo "   adb logcat -s P6RIG"
