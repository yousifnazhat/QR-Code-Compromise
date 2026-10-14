#!/usr/bin/env bash
# sim_list.sh — P6 iOS rig: list available simulators (W6.8).
#
# AUTHORIZATION — LAB ONLY (docs/governance/policy.md §1/§7). Simulator and
# owned devices only.
#
# Usage: ./sim_list.sh
# Exit codes: 0 list printed; 2 Xcode/simctl unavailable (physical slot:
# install Xcode — see message for exact steps).

set -euo pipefail

if ! xcrun simctl help >/dev/null 2>&1; then
  cat >&2 <<'EOF'
ERROR: xcrun simctl is not available — this Mac has no Xcode (only
Command Line Tools). simctl ships with Xcode, not with the CLT.

PHYSICAL SLOT (human, one-time):
  1. Install Xcode from the Mac App Store (or developer.apple.com/xcode).
  2. sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer
  3. xcodebuild -runFirstLaunch   # installs the iOS Simulator platform
  4. Re-run this script.
EOF
  exit 2
fi

echo "== P6 iOS rig: available simulator devices =="
xcrun simctl list devices available
echo
echo "Boot one with: xcrun simctl boot <udid-or-name>  (see sim_boot.sh)"
