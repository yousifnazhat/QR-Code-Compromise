#!/usr/bin/env bash
# sim_boot.sh — P6 iOS rig: boot a simulator (W6.8).
#
# AUTHORIZATION — LAB ONLY (docs/governance/policy.md §1/§7). Simulator and
# owned devices only.
#
# Usage:   ./sim_boot.sh [<udid-or-name>]
#          Default: first 'iPhone' device from `simctl list devices available`.
# Exit codes: 0 simulator booting/booted; 2 Xcode missing / no device found.

set -euo pipefail

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

TARGET="${1:-}"

if [ -z "$TARGET" ]; then
  TARGET="$(xcrun simctl list devices available | awk '/iPhone/ {print $NF; exit}' | tr -d '()')"
fi
if [ -z "$TARGET" ]; then
  echo "ERROR: no available iPhone simulator found (create one in Xcode > Devices & Simulators, or pass a UDID)." >&2
  exit 2
fi

echo "== P6 iOS rig: booting simulator: $TARGET"
xcrun simctl bootstatus "$TARGET" -b
echo "== booted. Open URL with: ./open_url.sh <url> --dev $TARGET"
