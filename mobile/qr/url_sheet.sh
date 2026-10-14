#!/usr/bin/env bash
# url_sheet.sh — P6 QR bridge: print a URL QR sheet via the EXISTING qr-ducky
# CLI (contract #2, implemented by P2). No new QR machinery is introduced
# here: the P6 payload is simply a URL string, so `qr-ducky sheet` is used
# verbatim with the URL as the payload file.
#
# AUTHORIZATION — LAB ONLY (docs/governance/policy.md §1/§7): print sheets for
# YOUR lab staging URLs only. The URL you print is where the scanned device
# will go — never point it at anything you do not own or control.
#
# Usage:
#   url_sheet.sh <url> <out.pdf> [extra qr-ducky sheet flags...]
#
# Examples:
#   url_sheet.sh "http://192.0.2.10:8000/payload.html" out/p6-sheet.pdf
#   url_sheet.sh "http://192.0.2.10:8000/payload.html" out/p6-sheet.pdf --png
#   (192.0.2.10 = RFC 5737 example space; use your lab host when running)
#
# Resolution order for the CLI (first hit wins):
#   1. $QRDUCKY_CMD  (e.g. "qr-ducky" if pip-installed)
#   2. `qr-ducky` on PATH
#   3. repo fallback: PYTHONPATH=<repo>/qrducky python3 -m qrducky.cli
#      (needs Python >= 3.11 for tomllib)
#
# Exit codes: 0 sheet written; 2 usage error / CLI not resolvable.

set -euo pipefail

if [ $# -lt 2 ]; then
  echo "usage: $0 <url> <out.pdf> [extra qr-ducky sheet flags...]" >&2
  exit 2
fi

URL="$1"; OUT="$2"; shift 2

# --- resolve the qr-ducky CLI -------------------------------------------------
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

run_ducky() {
  if [ -n "${QRDUCKY_CMD:-}" ]; then
    $QRDUCKY_CMD sheet --payload "$1" --out "$2" "${@:3}"
  elif command -v qr-ducky >/dev/null 2>&1; then
    qr-ducky sheet --payload "$1" --out "$2" "${@:3}"
  else
    for PY in python3 python3.13 python3.12 python3.11; do
      command -v "$PY" >/dev/null 2>&1 || continue
      if "$PY" -c "import tomllib, segno" >/dev/null 2>&1; then
        PYTHONPATH="$REPO_ROOT/qrducky" "$PY" -m qrducky.cli sheet \
          --payload "$1" --out "$2" "${@:3}"
        return
      fi
    done
    echo "ERROR: qr-ducky CLI not resolvable (install it: pip install -e qrducky," >&2
    echo "or set QRDUCKY_CMD, or provide Python >= 3.11)." >&2
    return 2
  fi
}

PAYLOAD_FILE="$(mktemp "${TMPDIR:-/tmp}/p6-url.XXXXXX")"
trap 'rm -f "$PAYLOAD_FILE"' EXIT
printf '%s' "$URL" > "$PAYLOAD_FILE"

echo "== P6: printing URL QR sheet via qr-ducky (payload = the URL string) =="
echo "== url: $URL"
run_ducky "$PAYLOAD_FILE" "$OUT" "$@"
echo "== wrote $OUT"
