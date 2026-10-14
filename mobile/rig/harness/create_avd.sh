#!/usr/bin/env bash
# create_avd.sh — P6 rig: create the deliberately-vulnerable emulator AVD (W6.3).
#
# AUTHORIZATION — LAB ONLY (docs/governance/policy.md §1/§7): emulator + owned
# devices only. This AVD exists to run legacy API-level builds reproducing
# historical, already-patched chain classes for measurement.
#
# Usage:   ./create_avd.sh [api_level] [arch]     (defaults: 22 x86_64)
#
# Why API 22: the emulator runs a targetSdk-16 APK (no install-time block) and
# keeps the full C1 reflection window for legacy-target apps, while being an
# image that current emulator tooling still boots comfortably.
#
# The avdmanager commands (documented, and executed below when the SDK is
# present — otherwise they are printed for the human's SDK-install slot):
#   sdkmanager  "platforms;android-<API>" "system-images;android-<API>;default;<arch>"
#   avdmanager create avd -n p6rig-api<API> -k "system-images;android-<API>;default;<arch>" -d pixel
#
# Exit codes: 0 created/exists; 2 SDK/avdmanager missing (physical slot: install
# the Android SDK first — see mobile/rig/README.md).

set -euo pipefail

API="${1:-22}"
ARCH="${2:-x86_64}"
AVD_NAME="p6rig-api${API}"
IMAGE="system-images;android-${API};default;${ARCH}"
SDKMANAGER="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/Library/Android/sdk}}/cmdline-tools/latest/bin/sdkmanager"
AVDMANAGER="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/Library/Android/sdk}}/cmdline-tools/latest/bin/avdmanager"
SDKMANAGER_ALT="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/Library/Android/sdk}}/tools/bin/sdkmanager"
AVDMANAGER_ALT="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/Library/Android/sdk}}/tools/bin/avdmanager"

if command -v "$SDKMANAGER" >/dev/null 2>&1; then :; elif command -v "$SDKMANAGER_ALT" >/dev/null 2>&1; then
  SDKMANAGER="$SDKMANAGER_ALT"; AVDMANAGER="$AVDMANAGER_ALT"
else
  echo "ERROR: sdkmanager/avdmanager not found under the Android SDK." >&2
  echo "PHYSICAL SLOT: install Android Studio + SDK cmdline-tools, then rerun." >&2
  echo "Commands to run once the SDK is present:" >&2
  echo "  sdkmanager  --licenses" >&2
  echo "  sdkmanager  \"platforms;android-${API}\" \"${IMAGE}\"" >&2
  echo "  avdmanager create avd -n ${AVD_NAME} -k \"${IMAGE}\" -d pixel" >&2
  exit 2
fi

echo "== P6 rig: creating AVD ${AVD_NAME} (${IMAGE}) =="
echo "== (1/3) accepting licenses + installing system image (may take a while)"
yes | "$SDKMANAGER" --licenses >/dev/null
"$SDKMANAGER" "platforms;android-${API}" "${IMAGE}"

echo "== (2/3) creating AVD"
echo no | "$AVDMANAGER" create avd -n "${AVD_NAME}" -k "${IMAGE}" -d pixel

echo "== (3/3) done. Start it with:"
echo "  emulator -avd ${AVD_NAME}"
echo "  (emulator lives in \$ANDROID_HOME/emulator/)"
